# -*- coding: utf-8 -*-
"""
Created on 2020/4/22 12:05 AM
---------
@summary:
---------
@author: Boris
@email: boris@bzkj.tech
"""

import time
import warnings
from collections import Iterable

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.core.base_parser import BaseParse
from feapder.core.scheduler import Scheduler
from feapder.db.redisdb import RedisDB
from feapder.network.item import Item
from feapder.network.request import Request
from feapder.utils.log import log


class Spider(
    BaseParse, Scheduler
):  # threading 中有name函数， 必须先继承BaseParser 否则其内部的name会被Schedule的基类threading.Thread的name覆盖
    """
    @summary: 为了简化搭建爬虫
    ---------
    """

    def __init__(
        self,
        redis_key=None,
        min_task_count=1,
        check_task_interval=5,
        thread_count=None,
        begin_callback=None,
        end_callback=None,
        delete_tabs=(),
        process_num=None,
        auto_stop_when_spider_done=None,
        auto_start_requests=None,
        send_run_time=False,
        batch_interval=0,
        wait_lock=True
    ):
        """
        @summary: 爬虫
        ---------
        @param redis_key: 爬虫request及item存放redis中的文件夹
        @param min_task_count: redis 中最少任务数, 少于这个数量会从mysql的任务表取任务。默认1秒
        @param check_task_interval: 检查是否还有任务的时间间隔；默认5秒
        @param thread_count: 线程数，默认为配置文件中的线程数
        @param begin_callback: 爬虫开始回调函数
        @param end_callback: 爬虫结束回调函数
        @param delete_tabs: 爬虫启动时删除的表，元组类型。 支持正则
        @param process_num: 进程数
        @param auto_stop_when_spider_done: 爬虫抓取完毕后是否自动结束或等待任务，默认自动结束
        @param auto_start_requests: 爬虫是否自动添加任务
        @param send_run_time: 发送运行时间
        @param batch_interval: 抓取时间间隔 默认为0 天为单位 多次启动时，只有当前时间与第一次抓取结束的时间间隔大于指定的时间间隔时，爬虫才启动
        @param wait_lock: 下发任务时否等待锁，若不等待锁，可能会存在多进程同时在下发一样的任务，因此分布式环境下请将该值设置True
        ---------
        @result:
        """
        super(Spider, self).__init__(
            redis_key=redis_key,
            thread_count=thread_count,
            begin_callback=begin_callback,
            end_callback=end_callback,
            delete_tabs=delete_tabs,
            process_num=process_num,
            auto_stop_when_spider_done=auto_stop_when_spider_done,
            auto_start_requests=auto_start_requests,
            send_run_time=send_run_time,
            batch_interval=batch_interval,
            wait_lock=wait_lock,
        )

        self._min_task_count = min_task_count
        self._check_task_interval = check_task_interval

        self._is_distributed_task = False
        self._is_show_not_task = False

    def start_monitor_task(self, *args, **kws):
        if not self.is_reach_next_spider_time():
            return

        self._auto_start_requests = False
        redisdb = RedisDB()

        if not self._parsers:  # 不是add_parser 模式
            self._parsers.append(self)

        while True:
            try:
                # 检查redis中是否有任务
                tab_requests = setting.TAB_REQUSETS.format(
                    redis_key=self._redis_key
                )
                todo_task_count = redisdb.zget_count(tab_requests)

                if todo_task_count < self._min_task_count:  # 添加任务
                    # make start requests
                    self.distribute_task(*args, **kws)

                else:
                    log.info("redis 中尚有%s条积压任务，暂时不派发新任务" % todo_task_count)

            except Exception as e:
                log.exception(e)

            if self._auto_stop_when_spider_done:
                break

            time.sleep(self._check_task_interval)

    def distribute_task(self, *args, **kws):
        """
        @summary: 分发任务 并将返回的request入库
        ---------
        @param tasks:
        ---------
        @result:
        """
        self._is_distributed_task = False

        for parser in self._parsers:
            requests = parser.start_requests(*args, **kws)
            if requests and not isinstance(requests, Iterable):
                raise Exception("%s.%s返回值必须可迭代" % (parser.name, "start_requests"))

            result_type = 1
            for request in requests or []:
                if isinstance(request, Request):
                    request.parser_name = request.parser_name or parser.name
                    self._request_buffer.put_request(request)

                    self._is_distributed_task = True
                    result_type = 1

                elif isinstance(request, Item):
                    self._item_buffer.put_item(request)
                    result_type = 2

                elif callable(request):  # callbale的request可能是更新数据库操作的函数
                    if result_type == 1:
                        self._request_buffer.put_request(request)
                    else:
                        self._item_buffer.put_item(request)
                else:
                    raise TypeError(
                        "start_requests yield result type error, expect Request、Item、callback func, bug get type: {}".format(
                            type(request)
                        )
                    )

            self._request_buffer.flush()
            self._item_buffer.flush()

        if self._is_distributed_task:  # 有任务时才提示启动爬虫
            # begin
            self.spider_begin()
            self.record_spider_state(
                spider_type=1,
                state=0,
                batch_date=tools.get_current_date(),
                spider_start_time=tools.get_current_date(),
                batch_interval=self._batch_interval,
            )

            # 重置已经提示无任务状态为False
            self._is_show_not_task = False

        elif not self._is_show_not_task:  # 无任务，且没推送过无任务信息
            # 发送无任务消息
            msg = "《%s》start_requests无任务添加" % (self._spider_name)
            log.info(msg)

            # self.send_msg(msg)

            self._is_show_not_task = True

    def run(self):
        if not self.is_reach_next_spider_time():
            return

        if not self._parsers:  # 不是add_parser 模式
            self._parsers.append(self)

        self._start()

        while True:
            if self.all_thread_is_done():
                if not self._is_notify_end:
                    self.spider_end()  # 跑完一轮
                    self.record_spider_state(
                        spider_type=1,
                        state=1,
                        spider_end_time=tools.get_current_date(),
                        batch_interval=self._batch_interval,
                    )

                    self._is_notify_end = True

                if self._auto_stop_when_spider_done:
                    self._stop_all_thread()
                    break

            else:
                self._is_notify_end = False

            self.check_task_status()

            tools.delay_time(1)  # 1秒钟检查一次爬虫状态

    @classmethod
    def to_DebugSpider(cls, *args, **kwargs):
        # DebugSpider 继承 cls
        DebugSpider.__bases__ = (cls,)
        DebugSpider.__name__ = cls.__name__
        return DebugSpider(*args, **kwargs)


class DebugSpider(Spider):
    """
    Debug爬虫
    """

    __debug_custom_setting__ = dict(
        COLLECTOR_SLEEP_TIME=1,
        COLLECTOR_TASK_COUNT=1,
        # SPIDER
        SPIDER_THREAD_COUNT=1,
        SPIDER_SLEEP_TIME=0,
        SPIDER_TASK_COUNT=1,
        SPIDER_MAX_RETRY_TIMES=10,
        REQUEST_TIME_OUT=600,  # 10秒
        ADD_ITEM_TO_MYSQL=False,
        PROXY_ENABLE=False,
        RETRY_FAILED_REQUESTS=False,
        # 保存失败的request
        SAVE_FAILED_REQUEST=False,
        # 过滤
        ITEM_FILTER_ENABLE=False,
        REQUEST_FILTER_ENABLE=False,
        OSS_UPLOAD_TABLES=(),
        DELETE_TABS=True,
    )

    def __init__(self, request=None, request_dict=None, *args, **kwargs):
        """
        @param request: request 类对象
        @param request_dict: request 字典。 request 与 request_dict 二者选一即可
        @param kwargs:
        """
        warnings.warn(
            "您正处于debug模式下，该模式下不会更新任务状态及数据入库，仅用于调试。正式发布前请更改为正常模式", category=Warning
        )

        if not request and not request_dict:
            raise Exception("request 与 request_dict 不能同时为null")

        kwargs["redis_key"] = kwargs["redis_key"] + "_debug"
        self.__class__.__custom_setting__.update(
            self.__class__.__debug_custom_setting__
        )

        super(DebugSpider, self).__init__(*args, **kwargs)

        self._request = request or Request.from_dict(request_dict)

    def save_cached(self, request, response, table):
        pass

    def delete_tables(self, delete_tables_list):
        if isinstance(delete_tables_list, bool):
            delete_tables_list = [self._redis_key + "*"]
        elif not isinstance(delete_tables_list, (list, tuple)):
            delete_tables_list = [delete_tables_list]

        redis = RedisDB()
        for delete_tab in delete_tables_list:
            if delete_tab == "*":
                delete_tab = self._redis_key + "*"

            tables = redis.getkeys(delete_tab)
            for table in tables:
                log.info("正在删除表 %s" % table)
                redis.clear(table)

    def __start_requests(self):
        yield self._request

    def distribute_task(self):
        """
        @summary: 分发任务 并将返回的request入库
        ---------
        ---------
        @result:
        """
        self._is_distributed_task = False

        for parser in self._parsers:
            requests = parser.__start_requests()
            if requests and not isinstance(requests, Iterable):
                raise Exception("%s.%s返回值必须可迭代" % (parser.name, "start_requests"))

            result_type = 1
            for request in requests or []:
                if isinstance(request, Request):
                    request.parser_name = request.parser_name or parser.name
                    self._request_buffer.put_request(request)

                    self._is_distributed_task = True
                    result_type = 1

                elif isinstance(request, Item):
                    self._item_buffer.put_item(request)
                    result_type = 2

                elif callable(request):  # callbale的request可能是更新数据库操作的函数
                    if result_type == 1:
                        self._request_buffer.put_request(request)
                    else:
                        self._item_buffer.put_item(request)

            self._request_buffer.flush()
            self._item_buffer.flush()

        if self._is_distributed_task:  # 有任务时才提示启动爬虫
            # begin
            self.spider_begin()
            self.record_spider_state(
                spider_type=1,
                state=0,
                batch_date=tools.get_current_date(),
                spider_start_time=tools.get_current_date(),
                batch_interval=self._batch_interval,
            )

            # 重置已经提示无任务状态为False
            self._is_show_not_task = False

        elif not self._is_show_not_task:  # 无任务，且没推送过无任务信息
            # 发送无任务消息
            msg = "《%s》start_requests无任务添加" % (self._spider_name)
            log.info(msg)

            # self.send_msg(msg)

            self._is_show_not_task = True

    def record_spider_state(
        self,
        spider_type,
        state,
        batch_date=None,
        spider_start_time=None,
        spider_end_time=None,
        batch_interval=None,
    ):
        pass

    def _start(self):
        # 启动parser 的 start_requests
        self.spider_begin()  # 不自动结束的爬虫此处只能执行一遍

        for parser in self._parsers:
            results = parser.__start_requests()
            # 添加request到请求队列，由请求队列统一入库
            if results and not isinstance(results, Iterable):
                raise Exception("%s.%s返回值必须可迭代" % (parser.name, "start_requests"))

            result_type = 1
            for result in results or []:
                if isinstance(result, Request):
                    result.parser_name = result.parser_name or parser.name
                    self._request_buffer.put_request(result)
                    result_type = 1

                elif isinstance(result, Item):
                    self._item_buffer.put_item(result)
                    result_type = 2

                elif callable(result):  # callbale的request可能是更新数据库操作的函数
                    if result_type == 1:
                        self._request_buffer.put_request(result)
                    else:
                        self._item_buffer.put_item(result)

            self._request_buffer.flush()
            self._item_buffer.flush()

        # 启动collector
        self._collector.start()

        # 启动parser control
        for i in range(self._thread_count):
            parser_control = self._parser_control_obj(
                self._collector,
                self._redis_key,
                self._request_buffer,
                self._item_buffer,
            )

            for parser in self._parsers:
                parser_control.add_parser(parser)

            parser_control.start()
            self._parser_controls.append(parser_control)

        # 启动request_buffer
        self._request_buffer.start()

        # 启动item_buffer
        self._item_buffer.start()

    def run(self):
        if not self._parsers:  # 不是add_parser 模式
            self._parsers.append(self)

        self._start()

        while True:
            if self.all_thread_is_done():
                self._stop_all_thread()
                break

            tools.delay_time(1)  # 1秒钟检查一次爬虫状态

        self.delete_tables([self._redis_key + "*"])
