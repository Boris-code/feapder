# -*- coding: utf-8 -*-
"""
Created on 2017-01-09 10:38
---------
@summary: 组装parser、 parser_control 和 collector
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import threading
import time
from collections import Iterable

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.buffer.item_buffer import ItemBuffer
from feapder.buffer.request_buffer import RequestBuffer
from feapder.core.base_parser import BaseParser
from feapder.core.collector import Collector
from feapder.core.handle_failed_requests import HandleFailedRequests
from feapder.core.parser_control import PaserControl
from feapder.db.redisdb import RedisDB
from feapder.network.item import Item
from feapder.network.request import Request
from feapder.utils.log import log
from feapder.utils.redis_lock import RedisLock

SPIDER_START_TIME_KEY = "spider_start_time"
SPIDER_END_TIME_KEY = "spider_end_time"
SPIDER_LAST_TASK_COUNT_RECORD_TIME_KEY = "last_task_count_record_time"


class Scheduler(threading.Thread):
    __custom_setting__ = {}

    def __init__(
        self,
        redis_key=None,
        thread_count=None,
        begin_callback=None,
        end_callback=None,
        delete_keys=(),
        auto_stop_when_spider_done=None,
        auto_start_requests=None,
        send_run_time=True,
        batch_interval=0,
        wait_lock=True,
        task_table=None,
    ):
        """
        @summary: 调度器
        ---------
        @param redis_key: 爬虫request及item存放redis中的文件夹
        @param thread_count: 线程数，默认为配置文件中的线程数
        @param begin_callback: 爬虫开始回调函数
        @param end_callback: 爬虫结束回调函数
        @param delete_keys: 爬虫启动时删除的key，类型: 元组/bool/string。 支持正则
        @param auto_stop_when_spider_done: 爬虫抓取完毕后是否自动结束或等待任务，默认自动结束
        @param auto_start_requests: 爬虫是否自动添加任务
        @param send_run_time: 发送运行时间
        @param batch_interval: 抓取时间间隔 默认为0 天为单位 多次启动时，只有当前时间与第一次抓取结束的时间间隔大于指定的时间间隔时，爬虫才启动
        @param wait_lock: 下发任务时否等待锁，若不等待锁，可能会存在多进程同时在下发一样的任务，因此分布式环境下请将该值设置True
        @param task_table: 任务表， 批次爬虫传递
        ---------
        @result:
        """

        super(Scheduler, self).__init__()

        for key, value in self.__class__.__custom_setting__.items():
            setattr(setting, key, value)

        self._redis_key = redis_key or setting.REDIS_KEY
        if not self._redis_key:
            raise Exception(
                """
                redis_key 为redis中存放request与item的目录。不能为空，
                可在setting中配置，如 REDIS_KEY = 'test'
                或spider初始化时传参, 如 TestSpider(redis_key='test')
                """
            )

        self._request_buffer = RequestBuffer(redis_key)
        self._item_buffer = ItemBuffer(redis_key, task_table)

        self._collector = Collector(redis_key)
        self._parsers = []
        self._parser_controls = []
        self._parser_control_obj = PaserControl

        self._auto_stop_when_spider_done = (
            auto_stop_when_spider_done
            if auto_stop_when_spider_done is not None
            else setting.AUTO_STOP_WHEN_SPIDER_DONE
        )
        self._auto_start_requests = (
            auto_start_requests
            if auto_start_requests is not None
            else setting.SPIDER_AUTO_START_REQUESTS
        )
        self._send_run_time = send_run_time
        self._batch_interval = batch_interval

        self._begin_callback = (
            begin_callback
            if begin_callback
            else lambda: log.info("\n********** feapder begin **********")
        )
        self._end_callback = (
            end_callback
            if end_callback
            else lambda: log.info("\n********** feapder end **********")
        )

        self._thread_count = (
            setting.SPIDER_THREAD_COUNT if not thread_count else thread_count
        )

        self._spider_name = redis_key
        self._project_name = redis_key.split(":")[0]

        self._tab_spider_time = setting.TAB_SPIDER_TIME.format(redis_key=redis_key)
        self._tab_spider_status = setting.TAB_SPIDER_STATUS.format(redis_key=redis_key)
        self._tab_requests = setting.TAB_REQUSETS.format(redis_key=redis_key)
        self._tab_failed_requests = setting.TAB_FAILED_REQUSETS.format(
            redis_key=redis_key
        )

        self._is_notify_end = False  # 是否已经通知结束
        self._last_task_count = 0  # 最近一次任务数量
        self._redisdb = RedisDB()

        self._project_total_state_table = "{}_total_state".format(self._project_name)
        self._is_exist_project_total_state_table = False

        # Request 缓存设置
        Request.cached_redis_key = redis_key
        Request.cached_expire_time = setting.RESPONSE_CACHED_EXPIRE_TIME

        delete_keys = delete_keys or setting.DELETE_KEYS
        if delete_keys:
            self.delete_tables(delete_keys)

        self._last_check_task_status_time = 0
        self.wait_lock = wait_lock

    def add_parser(self, parser):
        parser = parser()  # parser 实例化
        if isinstance(parser, BaseParser):
            self._parsers.append(parser)
        else:
            raise ValueError("类型错误，爬虫需继承feapder.BaseParser或feapder.BatchParser")

    def run(self):
        if not self.is_reach_next_spider_time():
            return

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

    def __add_task(self):
        # 启动parser 的 start_requests
        self.spider_begin()  # 不自动结束的爬虫此处只能执行一遍
        self.record_spider_state(
            spider_type=1,
            state=0,
            batch_date=tools.get_current_date(),
            spider_start_time=tools.get_current_date(),
            batch_interval=self._batch_interval,
        )

        # 判断任务池中属否还有任务，若有接着抓取
        todo_task_count = self._collector.get_requests_count()
        if todo_task_count:
            log.info("检查到有待做任务 %s 条，不重下发新任务，将接着上回异常终止处继续抓取" % todo_task_count)
        else:
            for parser in self._parsers:
                results = parser.start_requests()
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
                    else:
                        raise TypeError(
                            "start_requests yield result type error, expect Request、Item、callback func, bug get type: {}".format(
                                type(result)
                            )
                        )

                self._request_buffer.flush()
                self._item_buffer.flush()

    def _start(self):
        # 启动request_buffer
        self._request_buffer.start()
        # 启动item_buffer
        self._item_buffer.start()
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

        # 下发任务 因为时间可能比较长，放到最后面
        if setting.RETRY_FAILED_REQUESTS:
            # 重设失败的任务, 不用加锁，原子性操作
            handle_failed_requests = HandleFailedRequests(self._redis_key)
            handle_failed_requests.reput_failed_requests_to_requests()

        # 下发新任务
        if self._auto_start_requests:  # 自动下发
            if self.wait_lock:
                # 将添加任务处加锁，防止多进程之间添加重复的任务
                with RedisLock(
                    key=self._spider_name,
                    timeout=3600,
                    wait_timeout=60,
                    redis_cli=RedisDB().get_redis_obj(),
                ) as lock:
                    if lock.locked:
                        self.__add_task()
            else:
                self.__add_task()

    def all_thread_is_done(self):
        for i in range(3):  # 降低偶然性, 因为各个环节不是并发的，很有可能当时状态为假，但检测下一条时该状态为真。一次检测很有可能遇到这种偶然性
            # 检测 collector 状态
            if (
                self._collector.is_collector_task()
                or self._collector.get_requests_count() > 0
            ):
                return False

            # 检测 parser_control 状态
            for parser_control in self._parser_controls:
                if not parser_control.is_not_task():
                    return False

            # 检测 item_buffer 状态
            if (
                self._item_buffer.get_items_count() > 0
                or self._item_buffer.is_adding_to_db()
            ):
                return False

            # 检测 request_buffer 状态
            if (
                self._request_buffer.get_requests_count() > 0
                or self._request_buffer.is_adding_to_db()
            ):
                return False

            tools.delay_time(1)

        return True

    @tools.run_safe_model("check_task_status")
    def check_task_status(self):
        """
        检查任务状态 预警
        """
        # 每分钟检查一次
        now_time = time.time()
        if now_time - self._last_check_task_status_time > 60:
            self._last_check_task_status_time = now_time
        else:
            return

        # 检查redis中任务状态，若连续20分钟内任务数量未发生变化（parser可能卡死），则发出报警信息
        task_count = self._redisdb.zget_count(self._tab_requests)

        if task_count:
            if task_count != self._last_task_count:
                self._last_task_count = task_count
                self._redisdb.hset(
                    self._tab_spider_time,
                    SPIDER_LAST_TASK_COUNT_RECORD_TIME_KEY,
                    tools.get_current_timestamp(),
                )  # 多进程会重复发消息， 使用reids记录上次统计时间
            else:
                # 判断时间间隔是否超过20分钟
                lua = """
                    -- local key = KEYS[1]
                    local field = ARGV[1]
                    local current_timestamp = ARGV[2]

                    -- 取值
                    local last_timestamp = redis.call('hget', KEYS[1], field)
                    if last_timestamp and current_timestamp - last_timestamp >= 1200 then
                        return current_timestamp - last_timestamp -- 返回任务停滞时间 秒
                    end

                    if not last_timestamp then
                        redis.call('hset', KEYS[1], field, current_timestamp)
                    end

                    return 0

                """
                redis_obj = self._redisdb.get_redis_obj()
                cmd = redis_obj.register_script(lua)
                overtime = cmd(
                    keys=[self._tab_spider_time],
                    args=[
                        SPIDER_LAST_TASK_COUNT_RECORD_TIME_KEY,
                        tools.get_current_timestamp(),
                    ],
                )

                if overtime:
                    # 发送报警
                    msg = "《{}》爬虫任务停滞 {}，请检查爬虫是否正常".format(
                        self._spider_name, tools.format_seconds(overtime)
                    )
                    log.error(msg)
                    self.send_msg(
                        msg,
                        level="error",
                        message_prefix="《{}》爬虫任务停滞".format(self._spider_name),
                    )

        else:
            self._last_task_count = 0

        # 检查失败任务数量 超过1000 报警，
        failed_count = self._redisdb.zget_count(self._tab_failed_requests)
        if failed_count > setting.WARNING_FAILED_COUNT:
            # 发送报警
            msg = "《%s》爬虫当前失败任务 %s, 请检查爬虫是否正常" % (self._spider_name, failed_count)
            log.error(msg)
            self.send_msg(
                msg,
                level="error",
                message_prefix="《%s》爬虫当前失败任务数预警" % (self._spider_name),
            )

        # parser_control实时统计已做任务数及失败任务数，若失败数大于10且失败任务数/已做任务数>=0.5 则报警
        failed_task_count, success_task_count = PaserControl.get_task_status_count()
        total_count = success_task_count + failed_task_count
        if total_count > 0:
            task_success_rate = success_task_count / total_count
            if task_success_rate < 0.5:
                # 发送报警
                msg = "《%s》爬虫当前任务成功数%s, 失败数%s, 成功率 %.2f, 请检查爬虫是否正常" % (
                    self._spider_name,
                    success_task_count,
                    failed_task_count,
                    task_success_rate,
                )
                log.error(msg)
                # 统计下上次发消息的时间，若时间大于1小时，则报警（此处为多进程，需要考虑别报重复）
                self.send_msg(
                    msg,
                    level="error",
                    message_prefix="《%s》爬虫当前任务成功率" % (self._spider_name),
                )

    def delete_tables(self, delete_tables_list):
        if isinstance(delete_tables_list, bool):
            delete_tables_list = [self._redis_key + "*"]
        elif not isinstance(delete_tables_list, (list, tuple)):
            delete_tables_list = [delete_tables_list]

        redis = RedisDB()
        for delete_tab in delete_tables_list:
            if not delete_tab.startswith(self._redis_key):
                delete_tab = self._redis_key + delete_tab
            tables = redis.getkeys(delete_tab)
            for table in tables:
                if table != self._tab_spider_time:
                    log.info("正在删除key %s" % table)
                    redis.clear(table)

    def _stop_all_thread(self):
        self._request_buffer.stop()
        self._item_buffer.stop()
        # 停止 collector
        self._collector.stop()
        # 停止 parser_controls
        for parser_control in self._parser_controls:
            parser_control.stop()

        self._started.clear()

    def send_msg(self, msg, level="debug", message_prefix=""):
        if setting.WARNING_LEVEL == "ERROR":
            if level != "error":
                return

        if setting.DINGDING_WARNING_PHONE:
            keyword = "feapder报警系统\n"
            tools.dingding_warning(keyword + msg, message_prefix=message_prefix)

        if setting.EMAIL_RECEIVER:
            tools.email_warning(
                msg, message_prefix=message_prefix, title=self._spider_name
            )

        if setting.WECHAT_WARNING_URL:
            keyword = "feapder报警系统\n"
            tools.wechat_warning(keyword + msg, message_prefix=message_prefix)

    def spider_begin(self):
        """
        @summary: start_monitor_task 方式启动，此函数与spider_end不在同一进程内，变量不可共享
        ---------
        ---------
        @result:
        """

        if self._begin_callback:
            self._begin_callback()

        for parser in self._parsers:
            parser.start_callback()

        # 记录开始时间
        if not self._redisdb.hexists(self._tab_spider_time, SPIDER_START_TIME_KEY):
            current_timestamp = tools.get_current_timestamp()
            self._redisdb.hset(
                self._tab_spider_time, SPIDER_START_TIME_KEY, current_timestamp
            )

            # 发送消息
            self.send_msg("《%s》爬虫开始" % self._spider_name)

    def spider_end(self):
        self.record_end_time()

        if self._end_callback:
            self._end_callback()

        for parser in self._parsers:
            parser.close()
            parser.end_callback()

        # 关闭webdirver
        if Request.webdriver_pool:
            Request.webdriver_pool.close()

        # 计算抓取时长
        data = self._redisdb.hget(
            self._tab_spider_time, SPIDER_START_TIME_KEY, is_pop=True
        )
        if data:
            begin_timestamp = int(data)

            spand_time = tools.get_current_timestamp() - begin_timestamp

            msg = "《%s》爬虫结束，耗时 %s" % (
                self._spider_name,
                tools.format_seconds(spand_time),
            )
            log.info(msg)

            if self._send_run_time:
                self.send_msg(msg)

        if not self._auto_stop_when_spider_done:
            log.info("爬虫不自动结束， 等待下一轮任务...")
        else:
            self.delete_tables(self._tab_spider_status)

    def record_end_time(self):
        # 记录结束时间
        if self._batch_interval:
            current_timestamp = tools.get_current_timestamp()
            self._redisdb.hset(
                self._tab_spider_time, SPIDER_END_TIME_KEY, current_timestamp
            )

    def is_reach_next_spider_time(self):
        if not self._batch_interval:
            return True

        last_spider_end_time = self._redisdb.hget(
            self._tab_spider_time, SPIDER_END_TIME_KEY
        )
        if last_spider_end_time:
            last_spider_end_time = int(last_spider_end_time)
            current_timestamp = tools.get_current_timestamp()
            time_interval = current_timestamp - last_spider_end_time

            if time_interval < self._batch_interval * 86400:
                log.info(
                    "上次运行结束时间为 {} 与当前时间间隔 为 {}, 小于规定的抓取时间间隔 {}。爬虫不执行，退出～".format(
                        tools.timestamp_to_date(last_spider_end_time),
                        tools.format_seconds(time_interval),
                        tools.format_seconds(self._batch_interval * 86400),
                    )
                )
                return False

        return True

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
