# -*- coding: utf-8 -*-
"""
Created on 2017-01-03 16:06
---------
@summary: parser 控制类
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import inspect
import random
import threading
import time
from collections.abc import Iterable

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.buffer.item_buffer import ItemBuffer
from feapder.buffer.request_buffer import AirSpiderRequestBuffer
from feapder.core.base_parser import BaseParser
from feapder.core.result_dispatcher import ResultDispatcher
from feapder.core.runtime_state import RuntimeState
from feapder.db.memorydb import MemoryDB
from feapder.network.item import Item
from feapder.network.request import Request
from feapder.utils import metrics
from feapder.utils.log import log


class ParserControl(threading.Thread):
    DOWNLOAD_EXCEPTION = "download_exception"
    DOWNLOAD_SUCCESS = "download_success"
    DOWNLOAD_TOTAL = "download_total"
    PAESERS_EXCEPTION = "parser_exception"

    is_show_tip = False

    # 实时统计已做任务数及失败任务数，若失败任务数/已做任务数>0.5 则报警
    _success_task_count = 0
    _failed_task_count = 0
    _total_task_count = 0

    _hook_parsers = set()

    def __init__(self, collector, redis_key, request_buffer, item_buffer):
        super(ParserControl, self).__init__()
        self._state = RuntimeState()
        self._parsers = []
        self._collector = collector
        self._redis_key = redis_key
        self._request_buffer = request_buffer
        self._item_buffer = item_buffer

        self._thread_stop = False

    def run(self):
        self._thread_stop = False
        self._state = RuntimeState()
        while not self._state.is_stop_requested:
            try:
                request = self._collector.get_request()
                if not request:
                    if not self.is_show_tip:
                        log.debug("等待任务...")
                        self.is_show_tip = True
                    continue

                self.is_show_tip = False
                with self._state.busy():
                    self.deal_request(request)

            except Exception as e:
                log.exception(e)

    def is_not_task(self):
        return self.is_show_tip

    def is_idle(self):
        return self.is_not_task() and self._state.is_idle

    def is_stopped(self):
        return self._state.is_stop_requested

    @classmethod
    def get_task_status_count(cls):
        return cls._failed_task_count, cls._success_task_count, cls._total_task_count

    def _make_sync_request_payload(self, request):
        return {"request_obj": request, "request_redis": None}

    def _find_parser(self, request):
        for parser in self._parsers:
            if parser.name == request.parser_name:
                return parser
        return None

    def _prepare_response(self, parser, request):
        used_download_midware_enable = False
        if not request.auto_request:
            return request, None, used_download_midware_enable

        request_temp = None
        response = None

        # 下载中间件
        if request.download_midware:
            if isinstance(request.download_midware, (list, tuple)):
                request_temp = request
                for download_midware in request.download_midware:
                    download_midware = (
                        download_midware
                        if callable(download_midware)
                        else tools.get_method(parser, download_midware)
                    )
                    request_temp = download_midware(request_temp)
            else:
                download_midware = (
                    request.download_midware
                    if callable(request.download_midware)
                    else tools.get_method(parser, request.download_midware)
                )
                request_temp = download_midware(request)
        elif request.download_midware != False:
            request_temp = parser.download_midware(request)

        # 请求
        if request_temp:
            if isinstance(request_temp, (tuple, list)) and len(request_temp) == 2:
                request_temp, response = request_temp

            if not isinstance(request_temp, Request):
                raise Exception(
                    "download_midware need return a request, but received type: {}".format(
                        type(request_temp)
                    )
                )
            used_download_midware_enable = True
            request = request_temp

        return request, response, used_download_midware_enable

    def _download_response(self, request, response):
        if response is None:
            response = (
                request.get_response()
                if not setting.RESPONSE_CACHED_USED
                else request.get_response_from_cached(save_cached=False)
            )

        if response == None:
            raise Exception("连接超时 url: %s" % request.url)

        return response

    def _run_callback(self, parser, request, response):
        if request.callback:  # 如果有parser的回调函数，则用回调处理
            callback_parser = (
                request.callback
                if callable(request.callback)
                else tools.get_method(parser, request.callback)
            )
            return callback_parser(request, response)

        # 否则默认用parser处理
        return parser.parse(request, response)

    def _dispatch_results(self, parser, request, results):
        dispatcher = ResultDispatcher(
            request_buffer=self._request_buffer,
            item_buffer=self._item_buffer,
            deal_request=self.deal_request,
            sync_request_factory=self._make_sync_request_payload,
            allow_callable=True,
        )
        return dispatcher.dispatch(parser, request, results)

    def _finish_request(
        self,
        request_redis,
        del_request_redis_after_item_to_db,
        del_request_redis_after_request_to_db,
    ):
        # 删除正在做的request 跟随item优先
        if not request_redis:
            return

        if del_request_redis_after_item_to_db:
            self._item_buffer.put_item(request_redis)
        elif del_request_redis_after_request_to_db:
            self._request_buffer.put_del_request(request_redis)
        else:
            self._request_buffer.put_del_request(request_redis)

    def _record_success(self, parser, request, response):
        # 记录下载成功的文档
        self.record_download_status(ParserControl.DOWNLOAD_SUCCESS, parser.name)
        # 记录成功任务数
        self.__class__._success_task_count += 1

        # 缓存下载成功的文档
        if setting.RESPONSE_CACHED_ENABLE:
            request.save_cached(
                response=response,
                expire_time=setting.RESPONSE_CACHED_EXPIRE_TIME,
            )

    def _release_response_browser(self, request, response):
        # 释放浏览器
        if response and getattr(response, "browser", None):
            request.render_downloader.put_back(response.browser)

    def _sleep_after_request(self):
        if setting.SPIDER_SLEEP_TIME:
            if (
                isinstance(setting.SPIDER_SLEEP_TIME, (tuple, list))
                and len(setting.SPIDER_SLEEP_TIME) == 2
            ):
                sleep_time = random.randint(
                    int(setting.SPIDER_SLEEP_TIME[0]), int(setting.SPIDER_SLEEP_TIME[1])
                )
                time.sleep(sleep_time)
            else:
                time.sleep(setting.SPIDER_SLEEP_TIME)

    def _original_request_after_middleware(self, request_redis, request):
        return Request.from_dict(eval(request_redis)) if request_redis else request

    def _handle_exception(
        self,
        parser,
        request,
        request_redis,
        response,
        exception,
        used_download_midware_enable,
    ):
        del_request_redis_after_item_to_db = False
        del_request_redis_after_request_to_db = False

        exception_type = str(type(exception)).replace("<class '", "").replace("'>", "")
        if exception_type.startswith("requests"):
            # 记录下载失败的文档
            self.record_download_status(ParserControl.DOWNLOAD_EXCEPTION, parser.name)
            if request.retry_times % setting.PROXY_MAX_FAILED_TIMES == 0:
                request.del_proxy()

        else:
            # 记录解析程序异常
            self.record_download_status(ParserControl.PAESERS_EXCEPTION, parser.name)

        if setting.LOG_LEVEL == "DEBUG":  # 只有debug模式下打印， 超时的异常篇幅太多
            log.exception(exception)

        log.error(
            """
            -------------- %s.%s error -------------
            error          %s
            response       %s
            deal request   %s
            """
            % (
                parser.name,
                (
                    request.callback
                    and callable(request.callback)
                    and getattr(request.callback, "__name__")
                    or request.callback
                )
                or "parse",
                str(exception),
                response,
                tools.dumps_json(request.to_dict, indent=28)
                if setting.LOG_LEVEL == "DEBUG"
                else request,
            )
        )

        request.error_msg = "%s: %s" % (exception_type, exception)
        request.response = str(response)

        if "Invalid URL" in str(exception):
            request.is_abandoned = True

        requests = parser.exception_request(request, response, exception) or [request]
        if not isinstance(requests, Iterable):
            raise Exception("%s.%s返回值必须可迭代" % (parser.name, "exception_request"))

        for exception_request in requests:
            if callable(exception_request):
                self._request_buffer.put_request(exception_request)
                continue

            if not isinstance(exception_request, Request):
                raise Exception("exception_request 需 yield request")

            if (
                exception_request.retry_times + 1 > setting.SPIDER_MAX_RETRY_TIMES
                or exception_request.is_abandoned
            ):
                self.__class__._failed_task_count += 1  # 记录失败任务数

                # 处理failed_request的返回值 request 或 func
                results = parser.failed_request(
                    exception_request, response, exception
                ) or [exception_request]
                if not isinstance(results, Iterable):
                    raise Exception(
                        "%s.%s返回值必须可迭代" % (parser.name, "failed_request")
                    )

                for result in results:
                    if isinstance(result, Request):
                        if setting.SAVE_FAILED_REQUEST:
                            if used_download_midware_enable:
                                # 去掉download_midware 添加的属性
                                original_request = self._original_request_after_middleware(
                                    request_redis, result
                                )
                                original_request.error_msg = exception_request.error_msg
                                original_request.response = exception_request.response

                                self._request_buffer.put_failed_request(
                                    original_request
                                )
                            else:
                                self._request_buffer.put_failed_request(result)

                    elif callable(result):
                        self._request_buffer.put_request(result)

                    elif isinstance(result, Item):
                        self._item_buffer.put_item(result)

                del_request_redis_after_request_to_db = True

            else:
                # 将 requests 重新入库 爬取
                exception_request.retry_times += 1
                exception_request.filter_repeat = False
                log.info(
                    """
                    入库 等待重试
                    url     %s
                    重试次数 %s
                    最大允许重试次数 %s"""
                    % (
                        exception_request.url,
                        exception_request.retry_times,
                        setting.SPIDER_MAX_RETRY_TIMES,
                    )
                )
                if used_download_midware_enable:
                    # 去掉download_midware 添加的属性 使用原来的requests
                    original_request = self._original_request_after_middleware(
                        request_redis, exception_request
                    )
                    if hasattr(exception_request, "error_msg"):
                        original_request.error_msg = exception_request.error_msg
                    if hasattr(exception_request, "response"):
                        original_request.response = exception_request.response
                    original_request.retry_times = exception_request.retry_times
                    original_request.filter_repeat = exception_request.filter_repeat

                    self._request_buffer.put_request(original_request)
                else:
                    self._request_buffer.put_request(exception_request)
                del_request_redis_after_request_to_db = True

        return (
            del_request_redis_after_item_to_db,
            del_request_redis_after_request_to_db,
        )

    def deal_request(self, request):
        response = None
        request_redis = request["request_redis"]
        request = request["request_obj"]

        del_request_redis_after_item_to_db = False
        del_request_redis_after_request_to_db = False
        used_download_midware_enable = False

        parser = self._find_parser(request)
        if not parser:
            self._finish_request(
                request_redis,
                del_request_redis_after_item_to_db,
                del_request_redis_after_request_to_db,
            )
            self._sleep_after_request()
            return

        try:
            self.__class__._total_task_count += 1
            # 记录需下载的文档
            self.record_download_status(ParserControl.DOWNLOAD_TOTAL, parser.name)

            # 解析request
            request, response, used_download_midware_enable = self._prepare_response(
                parser, request
            )
            if request.auto_request:
                response = self._download_response(request, response)

            # 校验
            if request.auto_request and parser.validate(request, response) == False:
                return

            results = self._run_callback(parser, request, response)
            dispatch_result = self._dispatch_results(parser, request, results)
            del_request_redis_after_item_to_db = (
                dispatch_result.del_request_redis_after_item_to_db
            )
            del_request_redis_after_request_to_db = (
                dispatch_result.del_request_redis_after_request_to_db
            )

        except Exception as e:
            (
                del_request_redis_after_item_to_db,
                del_request_redis_after_request_to_db,
            ) = self._handle_exception(
                parser,
                request,
                request_redis,
                response,
                e,
                used_download_midware_enable,
            )

        else:
            self._record_success(parser, request, response)

        finally:
            self._release_response_browser(request, response)
            self._finish_request(
                request_redis,
                del_request_redis_after_item_to_db,
                del_request_redis_after_request_to_db,
            )
            self._sleep_after_request()

    def record_download_status(self, status, spider):
        """
        记录html等文档下载状态
        @return:
        """

        metrics.emit_counter(f"{spider}:{status}", 1, classify="document")

    def stop(self):
        self._thread_stop = True
        self._state.request_stop()
        self._started.clear()

    def add_parser(self, parser: BaseParser):
        # 动态增加parser.exception_request和parser.failed_request的参数, 兼容旧版本
        if parser not in self.__class__._hook_parsers:
            self.__class__._hook_parsers.add(parser)
            if len(inspect.getfullargspec(parser.exception_request).args) == 3:
                _exception_request = parser.exception_request
                parser.exception_request = (
                    lambda request, response, e: _exception_request(request, response)
                )

            if len(inspect.getfullargspec(parser.failed_request).args) == 3:
                _failed_request = parser.failed_request
                parser.failed_request = lambda request, response, e: _failed_request(
                    request, response
                )

        self._parsers.append(parser)


class AirSpiderParserControl(ParserControl):
    is_show_tip = False

    # 实时统计已做任务数及失败任务数，若失败任务数/已做任务数>0.5 则报警
    _success_task_count = 0
    _failed_task_count = 0

    def __init__(
        self,
        *,
        memory_db: MemoryDB,
        request_buffer: AirSpiderRequestBuffer,
        item_buffer: ItemBuffer,
    ):
        super(ParserControl, self).__init__()
        self._state = RuntimeState()
        self._parsers = []
        self._memory_db = memory_db
        self._thread_stop = False
        self._request_buffer = request_buffer
        self._item_buffer = item_buffer

    def run(self):
        self._thread_stop = False
        self._state = RuntimeState()
        while not self._state.is_stop_requested:
            try:
                request = self._memory_db.get()
                if not request:
                    if not self.is_show_tip:
                        log.debug("等待任务...")
                        self.is_show_tip = True
                    continue

                self.is_show_tip = False
                with self._state.busy():
                    self.deal_request(request)

            except Exception as e:
                log.exception(e)

    def deal_request(self, request):
        response = None

        for parser in self._parsers:
            if parser.name == request.parser_name:
                try:
                    self.__class__._total_task_count += 1
                    # 记录需下载的文档
                    self.record_download_status(
                        ParserControl.DOWNLOAD_TOTAL, parser.name
                    )

                    # 解析request
                    if request.auto_request:
                        request_temp = None
                        response = None

                        # 下载中间件
                        if request.download_midware:
                            if isinstance(request.download_midware, (list, tuple)):
                                request_temp = request
                                for download_midware in request.download_midware:
                                    download_midware = (
                                        download_midware
                                        if callable(download_midware)
                                        else tools.get_method(parser, download_midware)
                                    )
                                    request_temp = download_midware(request_temp)
                            else:
                                download_midware = (
                                    request.download_midware
                                    if callable(request.download_midware)
                                    else tools.get_method(
                                        parser, request.download_midware
                                    )
                                )
                                request_temp = download_midware(request)
                        elif request.download_midware != False:
                            request_temp = parser.download_midware(request)

                        # 请求
                        if request_temp:
                            if (
                                isinstance(request_temp, (tuple, list))
                                and len(request_temp) == 2
                            ):
                                request_temp, response = request_temp

                            if not isinstance(request_temp, Request):
                                raise Exception(
                                    "download_midware need return a request, but received type: {}".format(
                                        type(request_temp)
                                    )
                                )
                            request = request_temp

                        if response is None:
                            response = (
                                request.get_response()
                                if not setting.RESPONSE_CACHED_USED
                                else request.get_response_from_cached(save_cached=False)
                            )

                        # 校验
                        if parser.validate(request, response) == False:
                            break

                    else:
                        response = None

                    if request.callback:  # 如果有parser的回调函数，则用回调处理
                        callback_parser = (
                            request.callback
                            if callable(request.callback)
                            else tools.get_method(parser, request.callback)
                        )
                        results = callback_parser(request, response)
                    else:  # 否则默认用parser处理
                        results = parser.parse(request, response)

                    if results and not isinstance(results, Iterable):
                        raise Exception(
                            "%s.%s返回值必须可迭代" % (parser.name, request.callback or "parse")
                        )

                    # 此处判断是request 还是 item
                    for result in results or []:
                        if isinstance(result, Request):
                            # 给request的 parser_name 赋值
                            result.parser_name = result.parser_name or parser.name

                            # 判断是同步的callback还是异步的
                            if result.request_sync:  # 同步
                                self.deal_request(result)
                            else:  # 异步
                                # 将next_request 入库
                                self._request_buffer.put_request(result)

                        elif isinstance(result, Item):
                            self._item_buffer.put_item(result)
                        elif result is not None:
                            function_name = "{}.{}".format(
                                parser.name,
                                (
                                    request.callback
                                    and callable(request.callback)
                                    and getattr(request.callback, "__name__")
                                    or request.callback
                                )
                                or "parse",
                            )
                            raise TypeError(
                                f"{function_name} result expect Request or Item, bug get type: {type(result)}"
                            )

                except Exception as e:
                    exception_type = (
                        str(type(e)).replace("<class '", "").replace("'>", "")
                    )
                    if exception_type.startswith("requests"):
                        # 记录下载失败的文档
                        self.record_download_status(
                            ParserControl.DOWNLOAD_EXCEPTION, parser.name
                        )
                        if request.retry_times % setting.PROXY_MAX_FAILED_TIMES == 0:
                            request.del_proxy()

                    else:
                        # 记录解析程序异常
                        self.record_download_status(
                            ParserControl.PAESERS_EXCEPTION, parser.name
                        )

                    if setting.LOG_LEVEL == "DEBUG":  # 只有debug模式下打印， 超时的异常篇幅太多
                        log.exception(e)

                    log.error(
                        """
                            -------------- %s.%s error -------------
                            error          %s
                            response       %s
                            deal request   %s
                            """
                        % (
                            parser.name,
                            (
                                request.callback
                                and callable(request.callback)
                                and getattr(request.callback, "__name__")
                                or request.callback
                            )
                            or "parse",
                            str(e),
                            response,
                            tools.dumps_json(request.to_dict, indent=28)
                            if setting.LOG_LEVEL == "DEBUG"
                            else request,
                        )
                    )

                    request.error_msg = "%s: %s" % (exception_type, e)
                    request.response = str(response)

                    if "Invalid URL" in str(e):
                        request.is_abandoned = True

                    requests = parser.exception_request(request, response, e) or [
                        request
                    ]
                    if not isinstance(requests, Iterable):
                        raise Exception(
                            "%s.%s返回值必须可迭代" % (parser.name, "exception_request")
                        )
                    for request in requests:
                        if not isinstance(request, Request):
                            raise Exception("exception_request 需 yield request")

                        if (
                            request.retry_times + 1 > setting.SPIDER_MAX_RETRY_TIMES
                            or request.is_abandoned
                        ):
                            self.__class__._failed_task_count += 1  # 记录失败任务数

                            # 处理failed_request的返回值 request 或 func
                            results = parser.failed_request(request, response, e) or [
                                request
                            ]
                            if not isinstance(results, Iterable):
                                raise Exception(
                                    "%s.%s返回值必须可迭代" % (parser.name, "failed_request")
                                )

                            log.info(
                                """
                                任务超过最大重试次数，丢弃
                                url     %s
                                重试次数 %s
                                最大允许重试次数 %s"""
                                % (
                                    request.url,
                                    request.retry_times,
                                    setting.SPIDER_MAX_RETRY_TIMES,
                                )
                            )

                        else:
                            # 将 requests 重新入库 爬取
                            request.retry_times += 1
                            request.filter_repeat = False
                            log.info(
                                """
                                    入库 等待重试
                                    url     %s
                                    重试次数 %s
                                    最大允许重试次数 %s"""
                                % (
                                    request.url,
                                    request.retry_times,
                                    setting.SPIDER_MAX_RETRY_TIMES,
                                )
                            )
                            self._request_buffer.put_request(request)

                else:
                    # 记录下载成功的文档
                    self.record_download_status(
                        ParserControl.DOWNLOAD_SUCCESS, parser.name
                    )
                    # 记录成功任务数
                    self.__class__._success_task_count += 1

                    # 缓存下载成功的文档
                    if setting.RESPONSE_CACHED_ENABLE:
                        request.save_cached(
                            response=response,
                            expire_time=setting.RESPONSE_CACHED_EXPIRE_TIME,
                        )

                finally:
                    # 释放浏览器
                    if response and getattr(response, "browser", None):
                        request.render_downloader.put_back(response.browser)

                break

        if setting.SPIDER_SLEEP_TIME:
            if (
                isinstance(setting.SPIDER_SLEEP_TIME, (tuple, list))
                and len(setting.SPIDER_SLEEP_TIME) == 2
            ):
                sleep_time = random.randint(
                    int(setting.SPIDER_SLEEP_TIME[0]), int(setting.SPIDER_SLEEP_TIME[1])
                )
                time.sleep(sleep_time)
            else:
                time.sleep(setting.SPIDER_SLEEP_TIME)
