# -*- coding: utf-8 -*-
"""
Created on 2020/4/22 12:06 AM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import datetime
import os
import time
import warnings
from collections import Iterable

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.buffer.item_buffer import MAX_ITEM_COUNT
from feapder.core.base_parser import BatchParser
from feapder.core.scheduler import Scheduler
from feapder.db.mysqldb import MysqlDB
from feapder.db.redisdb import RedisDB
from feapder.network.item import Item
from feapder.network.item import UpdateItem
from feapder.network.request import Request
from feapder.utils.log import log
from feapder.utils.perfect_dict import PerfectDict
from feapder.utils.redis_lock import RedisLock

CONSOLE_PIPELINE_PATH = "feapder.pipelines.console_pipeline.ConsolePipeline"
MYSQL_PIPELINE_PATH = "feapder.pipelines.mysql_pipeline.MysqlPipeline"


class BatchSpider(BatchParser, Scheduler):
    def __init__(
        self,
        task_table,
        batch_record_table,
        batch_name,
        batch_interval,
        task_keys,
        task_state="state",
        min_task_count=10000,
        check_task_interval=5,
        task_limit=10000,
        related_redis_key=None,
        related_batch_record=None,
        task_condition="",
        task_order_by="",
        redis_key=None,
        thread_count=None,
        begin_callback=None,
        end_callback=None,
        delete_keys=(),
        keep_alive=None,
        **kwargs,
    ):
        """
        @summary: 批次爬虫
        必要条件
        1、需有任务表
            任务表中必须有id 及 任务状态字段 如 state。如指定parser_name字段，则任务会自动下发到对应的parser下, 否则会下发到所有的parser下。其他字段可根据爬虫需要的参数自行扩充

            参考建表语句如下：
            CREATE TABLE `table_name` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `param` varchar(1000) DEFAULT NULL COMMENT '爬虫需要的抓取数据需要的参数',
              `state` int(11) DEFAULT NULL COMMENT '任务状态',
              `parser_name` varchar(255) DEFAULT NULL COMMENT '任务解析器的脚本类名',
              PRIMARY KEY (`id`),
              UNIQUE KEY `nui` (`param`) USING BTREE
            ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

        2、需有批次记录表 不存在自动创建
        ---------
        @param task_table: mysql中的任务表
        @param batch_record_table: mysql 中的批次记录表
        @param batch_name: 批次采集程序名称
        @param batch_interval: 批次间隔 天为单位。 如想一小时一批次，可写成1/24
        @param task_keys: 需要获取的任务字段 列表 [] 如需指定解析的parser，则需将parser_name字段取出来。
        @param task_state: mysql中任务表的任务状态字段
        @param min_task_count: redis 中最少任务数, 少于这个数量会从mysql的任务表取任务
        @param check_task_interval: 检查是否还有任务的时间间隔；
        @param task_limit: 从数据库中取任务的数量
        @param redis_key: 任务等数据存放在redis中的key前缀
        @param thread_count: 线程数，默认为配置文件中的线程数
        @param begin_callback: 爬虫开始回调函数
        @param end_callback: 爬虫结束回调函数
        @param delete_keys: 爬虫启动时删除的key，类型: 元组/bool/string。 支持正则; 常用于清空任务队列，否则重启时会断点续爬
        @param keep_alive: 爬虫是否常驻，默认否
        @param related_redis_key: 有关联的其他爬虫任务表（redis）注意：要避免环路 如 A -> B & B -> A 。
        @param related_batch_record: 有关联的其他爬虫批次表（mysql）注意：要避免环路 如 A -> B & B -> A 。
            related_redis_key 与 related_batch_record 选其一配置即可；用于相关联的爬虫没结束时，本爬虫也不结束
            若相关连的爬虫为批次爬虫，推荐以related_batch_record配置，
            若相关连的爬虫为普通爬虫，无批次表，可以以related_redis_key配置
        @param task_condition: 任务条件 用于从一个大任务表中挑选出数据自己爬虫的任务，即where后的条件语句
        @param task_order_by: 取任务时的排序条件 如 id desc
        ---------
        @result:
        """
        Scheduler.__init__(
            self,
            redis_key=redis_key,
            thread_count=thread_count,
            begin_callback=begin_callback,
            end_callback=end_callback,
            delete_keys=delete_keys,
            keep_alive=keep_alive,
            auto_start_requests=False,
            batch_interval=batch_interval,
            task_table=task_table,
            **kwargs,
        )

        self._redisdb = RedisDB()
        self._mysqldb = MysqlDB()

        self._task_table = task_table  # mysql中的任务表
        self._batch_record_table = batch_record_table  # mysql 中的批次记录表
        self._batch_name = batch_name  # 批次采集程序名称
        self._task_keys = task_keys  # 需要获取的任务字段

        self._task_state = task_state  # mysql中任务表的state字段名
        self._min_task_count = min_task_count  # redis 中最少任务数
        self._check_task_interval = check_task_interval
        self._task_limit = task_limit  # mysql中一次取的任务数量
        self._related_task_tables = [
            setting.TAB_REQUSETS.format(redis_key=redis_key)
        ]  # 自己的task表也需要检查是否有任务
        if related_redis_key:
            self._related_task_tables.append(
                setting.TAB_REQUSETS.format(redis_key=related_redis_key)
            )

        self._related_batch_record = related_batch_record
        self._task_condition = task_condition
        self._task_condition_prefix_and = task_condition and " and {}".format(
            task_condition
        )
        self._task_condition_prefix_where = task_condition and " where {}".format(
            task_condition
        )
        self._task_order_by = task_order_by and " order by {}".format(task_order_by)

        self._batch_date_cache = None
        if self._batch_interval >= 1:
            self._date_format = "%Y-%m-%d"
        elif self._batch_interval < 1 and self._batch_interval >= 1 / 24:
            self._date_format = "%Y-%m-%d %H"
        else:
            self._date_format = "%Y-%m-%d %H:%M"

        # 报警相关
        self._send_msg_interval = datetime.timedelta(hours=1)  # 每隔1小时发送一次报警
        self._last_send_msg_time = None

        self._spider_last_done_time = None  # 爬虫最近已做任务数量时间
        self._spider_last_done_count = 0  # 爬虫最近已做任务数量
        self._spider_deal_speed_cached = None

        self._is_more_parsers = True  # 多模版类爬虫

    def init_property(self):
        """
        每个批次开始时需要重置的属性
        @return:
        """
        self._last_send_msg_time = None

        self._spider_last_done_time = None
        self._spider_last_done_count = 0  # 爬虫刚开始启动时已做任务数量

    def add_parser(self, parser):
        parser = parser(
            self._task_table,
            self._batch_record_table,
            self._task_state,
            self._date_format,
            self._mysqldb,
        )  # parser 实例化
        self._parsers.append(parser)

    def start_monitor_task(self):
        """
        @summary: 监控任务状态
        ---------
        ---------
        @result:
        """
        if not self._parsers:  # 不是多模版模式， 将自己注入到parsers，自己为模版
            self._is_more_parsers = False
            self._parsers.append(self)

        elif len(self._parsers) <= 1:
            self._is_more_parsers = False

        self.create_batch_record_table()

        # 添加任务
        for parser in self._parsers:
            parser.add_task()

        is_first_check = True
        while True:
            try:
                if self.check_batch(is_first_check):  # 该批次已经做完
                    if self._keep_alive:
                        is_first_check = True
                        log.info("爬虫所有任务已做完，不自动结束，等待新任务...")
                        time.sleep(self._check_task_interval)
                        continue
                    else:
                        break

                is_first_check = False

                # 检查redis中是否有任务 任务小于_min_task_count 则从mysql中取
                tab_requests = setting.TAB_REQUSETS.format(redis_key=self._redis_key)
                todo_task_count = self._redisdb.zget_count(tab_requests)

                tasks = []
                if todo_task_count < self._min_task_count:  # 从mysql中取任务
                    # 更新batch表的任务状态数量
                    self.update_task_done_count()

                    log.info("redis 中剩余任务%s 数量过小 从mysql中取任务追加" % todo_task_count)
                    tasks = self.get_todo_task_from_mysql()
                    if not tasks:  # 状态为0的任务已经做完，需要检查状态为2的任务是否丢失

                        if (
                            todo_task_count == 0
                        ):  # redis 中无待做任务，此时mysql中状态为2的任务为丢失任务。需重新做
                            lose_task_count = self.get_lose_task_count()

                            if not lose_task_count:
                                time.sleep(self._check_task_interval)
                                continue

                            elif (
                                lose_task_count > self._task_limit * 5
                            ):  # 丢失任务太多，直接重置，否则每次等redis任务消耗完再取下一批丢失任务，速度过慢
                                log.info("正在重置丢失任务为待做 共 {} 条".format(lose_task_count))
                                # 重置正在做的任务为待做
                                if self.reset_lose_task_from_mysql():
                                    log.info("重置丢失任务成功")
                                else:
                                    log.info("重置丢失任务失败")

                                continue

                            else:  # 丢失任务少，直接取
                                log.info(
                                    "正在取丢失任务 共 {} 条, 取 {} 条".format(
                                        lose_task_count,
                                        self._task_limit
                                        if self._task_limit <= lose_task_count
                                        else lose_task_count,
                                    )
                                )
                                tasks = self.get_doing_task_from_mysql()

                    else:
                        log.info("mysql 中取到待做任务 %s 条" % len(tasks))

                else:
                    log.info("redis 中尚有%s条积压任务，暂时不派发新任务" % todo_task_count)

                if not tasks:
                    if todo_task_count >= self._min_task_count:
                        # log.info('任务正在进行 redis中剩余任务 %s' % todo_task_count)
                        pass
                    else:
                        log.info("mysql 中无待做任务 redis中剩余任务 %s" % todo_task_count)
                else:
                    # make start requests
                    self.distribute_task(tasks)
                    log.info("添加任务到redis成功")

            except Exception as e:
                log.exception(e)

            time.sleep(self._check_task_interval)

    def create_batch_record_table(self):
        sql = (
            "select table_name from information_schema.tables where table_name like '%s'"
            % self._batch_record_table
        )
        tables_name = self._mysqldb.find(sql)
        if not tables_name:
            sql = """
                CREATE TABLE `{table_name}` (
                      `id` int(11) UNSIGNED NOT NULL AUTO_INCREMENT,
                      `batch_date` {batch_date} DEFAULT NULL COMMENT '批次时间',
                      `total_count` int(11) DEFAULT NULL COMMENT '任务总数',
                      `done_count` int(11) DEFAULT NULL COMMENT '完成数 (1,-1)',
                      `fail_count` int(11) DEFAULT NULL COMMENT '失败任务数 (-1)',
                      `interval` float(11) DEFAULT NULL COMMENT '批次间隔',
                      `interval_unit` varchar(20) DEFAULT NULL COMMENT '批次间隔单位 day, hour',
                      `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '批次开始时间',
                      `update_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '本条记录更新时间',
                      `is_done` int(11) DEFAULT '0' COMMENT '批次是否完成 0 未完成  1 完成',
                      PRIMARY KEY (`id`)
                    ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;
            """.format(
                table_name=self._batch_record_table,
                batch_date="date" if self._date_format == "%Y-%m-%d" else "datetime",
            )

            self._mysqldb.execute(sql)

    def distribute_task(self, tasks):
        """
        @summary: 分发任务
        ---------
        @param tasks:
        ---------
        @result:
        """
        if self._is_more_parsers:  # 为多模版类爬虫，需要下发指定的parser
            for task in tasks:
                for parser in self._parsers:  # 寻找task对应的parser
                    if parser.name in task:
                        task = PerfectDict(
                            _dict=dict(zip(self._task_keys, task)), _values=list(task)
                        )
                        requests = parser.start_requests(task)
                        if requests and not isinstance(requests, Iterable):
                            raise Exception(
                                "%s.%s返回值必须可迭代" % (parser.name, "start_requests")
                            )

                        result_type = 1
                        for request in requests or []:
                            if isinstance(request, Request):
                                request.parser_name = request.parser_name or parser.name
                                self._request_buffer.put_request(request)
                                result_type = 1

                            elif isinstance(request, Item):
                                self._item_buffer.put_item(request)
                                result_type = 2

                                if (
                                    self._item_buffer.get_items_count()
                                    >= MAX_ITEM_COUNT
                                ):
                                    self._item_buffer.flush()

                            elif callable(request):  # callbale的request可能是更新数据库操作的函数
                                if result_type == 1:
                                    self._request_buffer.put_request(request)
                                else:
                                    self._item_buffer.put_item(request)

                                    if (
                                        self._item_buffer.get_items_count()
                                        >= MAX_ITEM_COUNT
                                    ):
                                        self._item_buffer.flush()

                            else:
                                raise TypeError(
                                    "start_requests yield result type error, expect Request、Item、callback func, bug get type: {}".format(
                                        type(requests)
                                    )
                                )

                        break

        else:  # task没对应的parser 则将task下发到所有的parser
            for task in tasks:
                for parser in self._parsers:
                    task = PerfectDict(
                        _dict=dict(zip(self._task_keys, task)), _values=list(task)
                    )
                    requests = parser.start_requests(task)
                    if requests and not isinstance(requests, Iterable):
                        raise Exception(
                            "%s.%s返回值必须可迭代" % (parser.name, "start_requests")
                        )

                    result_type = 1
                    for request in requests or []:
                        if isinstance(request, Request):
                            request.parser_name = request.parser_name or parser.name
                            self._request_buffer.put_request(request)
                            result_type = 1

                        elif isinstance(request, Item):
                            self._item_buffer.put_item(request)
                            result_type = 2

                            if self._item_buffer.get_items_count() >= MAX_ITEM_COUNT:
                                self._item_buffer.flush()

                        elif callable(request):  # callbale的request可能是更新数据库操作的函数
                            if result_type == 1:
                                self._request_buffer.put_request(request)
                            else:
                                self._item_buffer.put_item(request)

                                if (
                                    self._item_buffer.get_items_count()
                                    >= MAX_ITEM_COUNT
                                ):
                                    self._item_buffer.flush()

        self._request_buffer.flush()
        self._item_buffer.flush()

    def __get_task_state_count(self):
        sql = "select {state}, count(1) from {task_table}{task_condition} group by {state}".format(
            state=self._task_state,
            task_table=self._task_table,
            task_condition=self._task_condition_prefix_where,
        )
        task_state_count = self._mysqldb.find(sql)

        task_state = {
            "total_count": sum(count for state, count in task_state_count),
            "done_count": sum(
                count for state, count in task_state_count if state in (1, -1)
            ),
            "failed_count": sum(
                count for state, count in task_state_count if state == -1
            ),
        }

        return task_state

    def update_task_done_count(self):
        """
        @summary: 更新批次表中的任务状态
        ---------
        ---------
        @result:
        """
        task_count = self.__get_task_state_count()

        # log.info('《%s》 批次进度 %s/%s' % (self._batch_name, done_task_count, total_task_count))

        # 更新批次表
        sql = "update {} set done_count = {}, total_count = {}, fail_count = {}, update_time = CURRENT_TIME, is_done=0, `interval` = {}, interval_unit = '{}' where batch_date = '{}'".format(
            self._batch_record_table,
            task_count.get("done_count"),
            task_count.get("total_count"),
            task_count.get("failed_count"),
            self._batch_interval
            if self._batch_interval >= 1
            else self._batch_interval * 24,
            "day" if self._batch_interval >= 1 else "hour",
            self.batch_date,
        )
        self._mysqldb.update(sql)

    def update_is_done(self):
        sql = "update {} set is_done = 1, update_time = CURRENT_TIME where batch_date = '{}' and is_done = 0".format(
            self._batch_record_table, self.batch_date
        )
        self._mysqldb.update(sql)

    def get_todo_task_from_mysql(self):
        """
        @summary: 取待做的任务
        ---------
        ---------
        @result:
        """
        # TODO 分批取数据 每批最大取 1000000个，防止内存占用过大
        # 查询任务
        task_keys = ", ".join([f"`{key}`" for key in self._task_keys])
        sql = "select %s from %s where %s = 0%s%s limit %s" % (
            task_keys,
            self._task_table,
            self._task_state,
            self._task_condition_prefix_and,
            self._task_order_by,
            self._task_limit,
        )
        tasks = self._mysqldb.find(sql)

        if tasks:
            # 更新任务状态
            for i in range(0, len(tasks), 10000):  # 10000 一批量更新
                task_ids = str(
                    tuple([task[0] for task in tasks[i : i + 10000]])
                ).replace(",)", ")")
                sql = "update %s set %s = 2 where id in %s" % (
                    self._task_table,
                    self._task_state,
                    task_ids,
                )
                self._mysqldb.update(sql)

        return tasks

    def get_doing_task_from_mysql(self):
        """
        @summary: 取正在做的任务
        ---------
        ---------
        @result:
        """

        # 查询任务
        task_keys = ", ".join([f"`{key}`" for key in self._task_keys])
        sql = "select %s from %s where %s = 2%s%s limit %s" % (
            task_keys,
            self._task_table,
            self._task_state,
            self._task_condition_prefix_and,
            self._task_order_by,
            self._task_limit,
        )
        tasks = self._mysqldb.find(sql)

        return tasks

    def get_lose_task_count(self):
        sql = 'select date_format(batch_date, "{date_format}"), total_count, done_count from {batch_record_table} order by id desc limit 1'.format(
            date_format=self._date_format.replace(":%M", ":%i"),
            batch_record_table=self._batch_record_table,
        )
        batch_info = self._mysqldb.find(sql)  # (('2018-08-19', 49686, 0),)
        batch_date, total_count, done_count = batch_info[0]
        return total_count - done_count

    def reset_lose_task_from_mysql(self):
        """
        @summary: 重置丢失任务为待做
        ---------
        ---------
        @result:
        """

        sql = "update {table} set {state} = 0 where {state} = 2{task_condition}".format(
            table=self._task_table,
            state=self._task_state,
            task_condition=self._task_condition_prefix_and,
        )
        return self._mysqldb.update(sql)

    def get_deal_speed(self, total_count, done_count, last_batch_date):
        """
        获取处理速度
        @param total_count: 总数量
        @param done_count: 做完数量
        @param last_batch_date: 批次时间 datetime
        @return:
            deal_speed （条/小时）, need_time （秒）, overflow_time（秒） （ overflow_time < 0 时表示提前多少秒完成 )
            或
            None
        """
        if not self._spider_last_done_count:
            now_date = datetime.datetime.now()
            self._spider_last_done_count = done_count
            self._spider_last_done_time = now_date

        if done_count > self._spider_last_done_count:
            now_date = datetime.datetime.now()

            time_interval = (now_date - self._spider_last_done_time).total_seconds()
            deal_speed = (
                done_count - self._spider_last_done_count
            ) / time_interval  # 条/秒
            need_time = (total_count - done_count) / deal_speed  # 单位秒
            overflow_time = (
                (now_date - last_batch_date).total_seconds()
                + need_time
                - datetime.timedelta(days=self._batch_interval).total_seconds()
            )  # 溢出时间 秒
            calculate_speed_time = now_date.strftime("%Y-%m-%d %H:%M:%S")  # 统计速度时间

            deal_speed = int(deal_speed * 3600)  # 条/小时

            # 更新最近已做任务数及时间
            self._spider_last_done_count = done_count
            self._spider_last_done_time = now_date

            self._spider_deal_speed_cached = (
                deal_speed,
                need_time,
                overflow_time,
                calculate_speed_time,
            )

        return self._spider_deal_speed_cached

    def init_task(self):
        """
        @summary: 初始化任务表中的任务， 新一个批次开始时调用。 可能会重写
        ---------
        ---------
        @result:
        """

        sql = "update {task_table} set {state} = 0 where {state} != -1{task_condition}".format(
            task_table=self._task_table,
            state=self._task_state,
            task_condition=self._task_condition_prefix_and,
        )
        return self._mysqldb.update(sql)

    def check_batch(self, is_first_check=False):
        """
        @summary: 检查批次是否完成
        ---------
        @param: is_first_check 是否为首次检查，若首次检查，且检查结果为批次已完成，则不发送批次完成消息。因为之前发送过了
        ---------
        @result: 完成返回True 否则False
        """

        sql = 'select date_format(batch_date, "{date_format}"), total_count, done_count from {batch_record_table} order by id desc limit 1'.format(
            date_format=self._date_format.replace(":%M", ":%i"),
            batch_record_table=self._batch_record_table,
        )
        batch_info = self._mysqldb.find(sql)  # (('2018-08-19', 49686, 0),)

        if batch_info:
            batch_date, total_count, done_count = batch_info[0]

            now_date = datetime.datetime.now()
            last_batch_date = datetime.datetime.strptime(batch_date, self._date_format)
            time_difference = now_date - last_batch_date

            if total_count == done_count and time_difference < datetime.timedelta(
                days=self._batch_interval
            ):  # 若在本批次内，再次检查任务表是否有新增任务
                # # 改成查询任务表 看是否真的没任务了，因为batch_record表里边的数量可能没来得及更新
                task_count = self.__get_task_state_count()

                total_count = task_count.get("total_count")
                done_count = task_count.get("done_count")

            if total_count == done_count:
                # 检查相关联的爬虫是否完成
                releated_spider_is_done = self.related_spider_is_done()
                if releated_spider_is_done == False:
                    msg = "《{}》本批次未完成, 正在等待依赖爬虫 {} 结束. 批次时间 {} 批次进度 {}/{}".format(
                        self._batch_name,
                        self._related_batch_record or self._related_task_tables,
                        batch_date,
                        done_count,
                        total_count,
                    )
                    log.info(msg)
                    # 检查是否超时 超时发出报警
                    if time_difference >= datetime.timedelta(
                        days=self._batch_interval
                    ):  # 已经超时
                        if (
                            not self._last_send_msg_time
                            or now_date - self._last_send_msg_time
                            >= self._send_msg_interval
                        ):
                            self._last_send_msg_time = now_date
                            self.send_msg(
                                msg,
                                level="error",
                                message_prefix="《{}》本批次未完成, 正在等待依赖爬虫 {} 结束".format(
                                    self._batch_name,
                                    self._related_batch_record
                                    or self._related_task_tables,
                                ),
                            )

                    return False

                elif releated_spider_is_done == True:
                    # 更新is_done 状态
                    self.update_is_done()

                else:
                    self.update_is_done()

                msg = "《{}》本批次完成 批次时间 {} 共处理 {} 条任务".format(
                    self._batch_name, batch_date, done_count
                )
                log.info(msg)
                if not is_first_check:
                    self.send_msg(msg)

                # 判断下一批次是否到
                if time_difference >= datetime.timedelta(days=self._batch_interval):
                    msg = "《{}》下一批次开始".format(self._batch_name)
                    log.info(msg)
                    self.send_msg(msg)

                    # 初始化任务表状态
                    if self.init_task() != False:  # 更新失败返回False 其他返回True/None
                        # 初始化属性
                        self.init_property()

                        is_success = (
                            self.record_batch()
                        )  # 有可能插入不成功，但是任务表已经重置了，不过由于当前时间为下一批次的时间，检查批次是否结束时不会检查任务表，所以下次执行时仍然会重置
                        if is_success:
                            # 看是否有等待任务的worker，若有则需要等会再下发任务，防止work批次时间没来得及更新
                            current_timestamp = tools.get_current_timestamp()
                            spider_count = self._redisdb.zget_count(
                                self._tab_spider_status,
                                priority_min=current_timestamp
                                - (setting.COLLECTOR_SLEEP_TIME + 10),
                                priority_max=current_timestamp,
                            )
                            if spider_count:
                                log.info(
                                    f"插入新批次记录成功，检测到有{spider_count}个爬虫进程在等待任务，本批任务1分钟后开始下发, 防止爬虫端缓存的批次时间没来得及更新"
                                )
                                tools.delay_time(60)
                            else:
                                log.info("插入新批次记录成功")

                            return False  # 下一批次开始

                        else:
                            return True  # 下一批次不开始。先不派发任务，因为批次表新批次插入失败了，需要插入成功后再派发任务

                else:
                    log.info("《{}》下次批次时间未到".format(self._batch_name))
                    if not is_first_check:
                        self.send_msg("《{}》下次批次时间未到".format(self._batch_name))
                    return True

            else:
                if time_difference >= datetime.timedelta(
                    days=self._batch_interval
                ):  # 已经超时
                    time_out = time_difference - datetime.timedelta(
                        days=self._batch_interval
                    )
                    time_out_pretty = tools.format_seconds(time_out.total_seconds())

                    msg = "《{}》本批次已超时{} 批次时间 {}, 批次进度 {}/{}".format(
                        self._batch_name,
                        time_out_pretty,
                        batch_date,
                        done_count,
                        total_count,
                    )
                    if self._batch_interval >= 1:
                        msg += ", 期望时间{}天".format(self._batch_interval)
                    else:
                        msg += ", 期望时间{}小时".format(self._batch_interval * 24)

                    result = self.get_deal_speed(
                        total_count=total_count,
                        done_count=done_count,
                        last_batch_date=last_batch_date,
                    )
                    if result:
                        deal_speed, need_time, overflow_time, calculate_speed_time = (
                            result
                        )
                        msg += ", 任务处理速度于{}统计, 约 {}条/小时, 预计还需 {}".format(
                            calculate_speed_time,
                            deal_speed,
                            tools.format_seconds(need_time),
                        )

                        if overflow_time > 0:
                            msg += ", 该批次预计总超时 {}, 请及时处理".format(
                                tools.format_seconds(overflow_time)
                            )

                    log.info(msg)

                    if (
                        not self._last_send_msg_time
                        or now_date - self._last_send_msg_time
                        >= self._send_msg_interval
                    ):
                        self._last_send_msg_time = now_date
                        self.send_msg(
                            msg,
                            level="error",
                            message_prefix="《{}》批次超时".format(self._batch_name),
                        )

                else:  # 未超时
                    remaining_time = (
                        datetime.timedelta(days=self._batch_interval) - time_difference
                    )
                    remaining_time_pretty = tools.format_seconds(
                        remaining_time.total_seconds()
                    )

                    if self._batch_interval >= 1:
                        msg = "《{}》本批次正在进行, 批次时间 {}, 批次进度 {}/{}, 期望时间{}天, 剩余{}".format(
                            self._batch_name,
                            batch_date,
                            done_count,
                            total_count,
                            self._batch_interval,
                            remaining_time_pretty,
                        )
                    else:
                        msg = "《{}》本批次正在进行, 批次时间 {}, 批次进度 {}/{}, 期望时间{}小时, 剩余{}".format(
                            self._batch_name,
                            batch_date,
                            done_count,
                            total_count,
                            self._batch_interval * 24,
                            remaining_time_pretty,
                        )

                    result = self.get_deal_speed(
                        total_count=total_count,
                        done_count=done_count,
                        last_batch_date=last_batch_date,
                    )
                    if result:
                        deal_speed, need_time, overflow_time, calculate_speed_time = (
                            result
                        )
                        msg += ", 任务处理速度于{}统计, 约 {}条/小时, 预计还需 {}".format(
                            calculate_speed_time,
                            deal_speed,
                            tools.format_seconds(need_time),
                        )

                        if overflow_time > 0:
                            msg += ", 该批次可能会超时 {}, 请及时处理".format(
                                tools.format_seconds(overflow_time)
                            )
                            # 发送警报
                            if (
                                not self._last_send_msg_time
                                or now_date - self._last_send_msg_time
                                >= self._send_msg_interval
                            ):
                                self._last_send_msg_time = now_date
                                self.send_msg(
                                    msg,
                                    level="error",
                                    message_prefix="《{}》批次可能超时".format(
                                        self._batch_name
                                    ),
                                )

                        elif overflow_time < 0:
                            msg += ", 该批次预计提前 {} 完成".format(
                                tools.format_seconds(-overflow_time)
                            )

                    log.info(msg)

        else:
            # 插入batch_date
            self.record_batch()

            # 初始化任务表状态 可能有产生任务的代码
            self.init_task()

            return False

    def related_spider_is_done(self):
        """
        相关连的爬虫是否跑完
        @return: True / False / None 表示无相关的爬虫 可由自身的total_count 和 done_count 来判断
        """

        for related_redis_task_table in self._related_task_tables:
            if self._redisdb.exists_key(related_redis_task_table):
                return False

        if self._related_batch_record:
            sql = "select is_done from {} order by id desc limit 1".format(
                self._related_batch_record
            )
            is_done = self._mysqldb.find(sql)
            is_done = is_done[0][0] if is_done else None

            if is_done is None:
                log.warning("相关联的批次表不存在或无批次信息")
                return None

            if not is_done:
                return False

        return True

    def record_batch(self):
        """
        @summary: 记录批次信息（初始化）
        ---------
        ---------
        @result:
        """

        # 查询总任务数
        sql = "select count(1) from %s%s" % (
            self._task_table,
            self._task_condition_prefix_where,
        )
        total_task_count = self._mysqldb.find(sql)[0][0]

        batch_date = tools.get_current_date(self._date_format)

        sql = (
            "insert into %s (batch_date, done_count, total_count, `interval`, interval_unit, create_time) values ('%s', %s, %s, %s, '%s', CURRENT_TIME)"
            % (
                self._batch_record_table,
                batch_date,
                0,
                total_task_count,
                self._batch_interval
                if self._batch_interval >= 1
                else self._batch_interval * 24,
                "day" if self._batch_interval >= 1 else "hour",
            )
        )

        affect_count = self._mysqldb.add(sql)  # None / 0 / 1 (1 为成功)
        if affect_count:
            # 重置批次日期
            self._batch_date_cache = batch_date
            # 重新刷下self.batch_date 中的 os.environ.get('batch_date') 否则日期还停留在上一个批次
            os.environ["batch_date"] = self._batch_date_cache

            # 爬虫开始
            self.spider_begin()
            self.record_spider_state(
                spider_type=2,
                state=0,
                batch_date=batch_date,
                spider_start_time=tools.get_current_date(),
                batch_interval=self._batch_interval,
            )
        else:
            log.error("插入新批次失败")

        return affect_count

    # -------- 批次结束逻辑 ------------

    def task_is_done(self):
        """
        @summary: 检查任务状态 是否做完 同时更新批次时间 (不能挂 挂了批次时间就不更新了)
        ---------
        ---------
        @result: True / False （做完 / 未做完）
        """

        is_done = False

        # 查看批次记录表任务状态
        sql = 'select date_format(batch_date, "{date_format}"), total_count, done_count, is_done from {batch_record_table} order by id desc limit 1'.format(
            date_format=self._date_format.replace(":%M", ":%i"),
            batch_record_table=self._batch_record_table,
        )

        batch_info = self._mysqldb.find(sql)
        if batch_info is None:
            raise Exception("查询批次信息失败")

        if batch_info:
            self._batch_date_cache, total_count, done_count, is_done = batch_info[
                0
            ]  # 更新self._batch_date_cache, 防止新批次已经开始了，但self._batch_date_cache还是原来的批次时间

            log.info(
                "《%s》 批次时间%s 批次进度 %s/%s 完成状态 %d"
                % (
                    self._batch_name,
                    self._batch_date_cache,
                    done_count,
                    total_count,
                    is_done,
                )
            )
            os.environ["batch_date"] = self._batch_date_cache  # 更新BatchParser里边的批次时间

        if is_done:  # 检查任务表中是否有没做的任务 若有则is_done 为 False
            # 比较耗时 加锁防止多进程同时查询
            with RedisLock(key=self._spider_name) as lock:
                if lock.locked:
                    log.info("批次表标记已完成，正在检查任务表是否有未完成的任务")

                    sql = "select 1 from %s where (%s = 0 or %s=2)%s limit 1" % (
                        self._task_table,
                        self._task_state,
                        self._task_state,
                        self._task_condition_prefix_and,
                    )
                    tasks = self._mysqldb.find(sql)  # [(1,)]  / []
                    if tasks:
                        log.info("检测到任务表中有未完成任务，等待任务下发")
                        is_done = False

                        # 更新batch_record 表的is_done 状态，减少查询任务表的次数
                        sql = 'update {batch_record_table} set is_done = 0 where batch_date = "{batch_date}"'.format(
                            batch_record_table=self._batch_record_table,
                            batch_date=self._batch_date_cache,
                        )
                        self._mysqldb.update(sql)

                    else:
                        log.info("任务表中任务均已完成，爬虫结束")
                else:
                    log.info("批次表标记已完成，其他爬虫进程正在检查任务表是否有未完成的任务，本进程跳过检查，继续等待")

                    is_done = False

        return is_done

    def run(self):
        """
        @summary: 重写run方法 检查mysql中的任务是否做完， 做完停止
        ---------
        ---------
        @result:
        """
        try:
            self.create_batch_record_table()

            if not self._parsers:  # 不是add_parser 模式
                self._parsers.append(self)

            self._start()

            while True:
                if (
                    self.task_is_done() and self.all_thread_is_done()
                ):  # redis全部的任务已经做完 并且mysql中的任务已经做完（检查各个线程all_thread_is_done，防止任务没做完，就更新任务状态，导致程序结束的情况）
                    if not self._is_notify_end:
                        self.spider_end()
                        self.record_spider_state(
                            spider_type=2,
                            state=1,
                            batch_date=self._batch_date_cache,
                            spider_end_time=tools.get_current_date(),
                            batch_interval=self._batch_interval,
                        )

                        self._is_notify_end = True

                    if not self._keep_alive:
                        self._stop_all_thread()
                        break
                else:
                    self._is_notify_end = False

                self.check_task_status()
                tools.delay_time(10)  # 10秒钟检查一次爬虫状态

        except Exception as e:
            msg = "《%s》主线程异常 爬虫结束 exception: %s" % (self._batch_name, e)
            log.error(msg)
            self.send_msg(
                msg, level="error", message_prefix="《%s》爬虫异常结束".format(self._batch_name)
            )

            os._exit(137)  # 使退出码为35072 方便爬虫管理器重启

    @classmethod
    def to_DebugBatchSpider(cls, *args, **kwargs):
        # DebugBatchSpider 继承 cls
        DebugBatchSpider.__bases__ = (cls,)
        DebugBatchSpider.__name__ = cls.__name__
        return DebugBatchSpider(*args, **kwargs)


class DebugBatchSpider(BatchSpider):
    """
    Debug批次爬虫
    """

    __debug_custom_setting__ = dict(
        COLLECTOR_SLEEP_TIME=1,
        COLLECTOR_TASK_COUNT=1,
        # SPIDER
        SPIDER_THREAD_COUNT=1,
        SPIDER_SLEEP_TIME=0,
        SPIDER_TASK_COUNT=1,
        SPIDER_MAX_RETRY_TIMES=10,
        REQUEST_LOST_TIMEOUT=600,  # 10分钟
        PROXY_ENABLE=False,
        RETRY_FAILED_REQUESTS=False,
        # 保存失败的request
        SAVE_FAILED_REQUEST=False,
        # 过滤
        ITEM_FILTER_ENABLE=False,
        REQUEST_FILTER_ENABLE=False,
        OSS_UPLOAD_TABLES=(),
        DELETE_KEYS=True,
        ITEM_PIPELINES=[CONSOLE_PIPELINE_PATH],
    )

    def __init__(
        self,
        task_id=None,
        task=None,
        save_to_db=False,
        update_stask=False,
        *args,
        **kwargs,
    ):
        """
        @param task_id:  任务id
        @param task:  任务  task 与 task_id 二者选一即可
        @param save_to_db: 数据是否入库 默认否
        @param update_stask: 是否更新任务 默认否
        @param args:
        @param kwargs:
        """
        warnings.warn(
            "您正处于debug模式下，该模式下不会更新任务状态及数据入库，仅用于调试。正式发布前请更改为正常模式", category=Warning
        )

        if not task and not task_id:
            raise Exception("task_id 与 task 不能同时为null")

        kwargs["redis_key"] = kwargs["redis_key"] + "_debug"
        if save_to_db and not self.__class__.__custom_setting__.get("ITEM_PIPELINES"):
            self.__class__.__debug_custom_setting__.update(
                ITEM_PIPELINES=[MYSQL_PIPELINE_PATH]
            )
        self.__class__.__custom_setting__.update(
            self.__class__.__debug_custom_setting__
        )

        super(DebugBatchSpider, self).__init__(*args, **kwargs)

        self._task_id = task_id
        self._task = task
        self._update_task = update_stask

    def start_monitor_task(self):
        """
        @summary: 监控任务状态
        ---------
        ---------
        @result:
        """
        if not self._parsers:  # 不是多模版模式， 将自己注入到parsers，自己为模版
            self._is_more_parsers = False
            self._parsers.append(self)

        elif len(self._parsers) <= 1:
            self._is_more_parsers = False

        if self._task:
            self.distribute_task([self._task])
        else:
            tasks = self.get_todo_task_from_mysql()
            if not tasks:
                raise Exception("未获取到任务 请检查 task_id: {} 是否存在".format(self._task_id))
            self.distribute_task(tasks)

        os.environ.setdefault("batch_date", "1970-00-00")
        log.debug("下发任务完毕")

    def get_todo_task_from_mysql(self):
        """
        @summary: 取待做的任务
        ---------
        ---------
        @result:
        """

        # 查询任务
        task_keys = ", ".join([f"`{key}`" for key in self._task_keys])
        sql = "select %s from %s where id=%s" % (
            task_keys,
            self._task_table,
            self._task_id,
        )
        tasks = self._mysqldb.find(sql)

        return tasks

    def save_cached(self, request, response, table):
        pass

    def update_task_state(self, task_id, state=1, *args, **kwargs):
        """
        @summary: 更新任务表中任务状态，做完每个任务时代码逻辑中要主动调用。可能会重写
        调用方法为 yield lambda : self.update_task_state(task_id, state)
        ---------
        @param task_id:
        @param state:
        ---------
        @result:
        """
        if self._update_task:
            kwargs["id"] = task_id
            kwargs[self._task_state] = state

            sql = tools.make_update_sql(
                self._task_table,
                kwargs,
                condition="id = {task_id}".format(task_id=task_id),
            )

            if self._mysqldb.update(sql):
                log.debug("置任务%s状态成功" % task_id)
            else:
                log.error("置任务%s状态失败  sql=%s" % (task_id, sql))

    def update_task_batch(self, task_id, state=1, *args, **kwargs):
        """
        批量更新任务 多处调用，更新的字段必须一致
        注意：需要 写成 yield update_task_batch(...) 否则不会更新
        @param task_id:
        @param state:
        @param kwargs:
        @return:
        """
        if self._update_task:
            kwargs["id"] = task_id
            kwargs[self._task_state] = state

            update_item = UpdateItem(**kwargs)
            update_item.table_name = self._task_table
            update_item.name_underline = self._task_table + "_item"

            return update_item

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

    def run(self):
        self.start_monitor_task()

        if not self._parsers:  # 不是add_parser 模式
            self._parsers.append(self)

        self._start()

        while True:
            if self.all_thread_is_done():
                self._stop_all_thread()
                break

            tools.delay_time(1)  # 1秒钟检查一次爬虫状态

        self.delete_tables([self._redis_key + "*"])

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
