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
from collections.abc import Iterable
from typing import List, Tuple, Dict, Union

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.core.base_parser import TaskParser
from feapder.core.scheduler import Scheduler
from feapder.db.mysqldb import MysqlDB
from feapder.db.redisdb import RedisDB
from feapder.network.item import Item
from feapder.network.item import UpdateItem
from feapder.network.request import Request
from feapder.utils.log import log
from feapder.utils.perfect_dict import PerfectDict

CONSOLE_PIPELINE_PATH = "feapder.pipelines.console_pipeline.ConsolePipeline"
MYSQL_PIPELINE_PATH = "feapder.pipelines.mysql_pipeline.MysqlPipeline"


class TaskSpider(TaskParser, Scheduler):
    def __init__(
        self,
        redis_key,
        task_table,
        task_table_type="mysql",
        task_keys=None,
        task_state="state",
        min_task_count=10000,
        check_task_interval=5,
        task_limit=10000,
        related_redis_key=None,
        related_batch_record=None,
        task_condition="",
        task_order_by="",
        thread_count=None,
        begin_callback=None,
        end_callback=None,
        delete_keys=(),
        keep_alive=None,
        batch_interval=0,
        **kwargs,
    ):
        """
        @summary: 任务爬虫
        必要条件 需要指定任务表，可以是redis表或者mysql表作为任务种子
        redis任务种子表：zset类型。值为 {"xxx":xxx, "xxx2":"xxx2"}；若为集成模式，需指定parser_name字段，如{"xxx":xxx, "xxx2":"xxx2", "parser_name":"TestTaskSpider"}
        mysql任务表：
            任务表中必须有id及任务状态字段 如 state, 其他字段可根据爬虫需要的参数自行扩充。若为集成模式，需指定parser_name字段。

            参考建表语句如下：
            CREATE TABLE `table_name` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `param` varchar(1000) DEFAULT NULL COMMENT '爬虫需要的抓取数据需要的参数',
              `state` int(11) DEFAULT NULL COMMENT '任务状态',
              `parser_name` varchar(255) DEFAULT NULL COMMENT '任务解析器的脚本类名',
              PRIMARY KEY (`id`),
              UNIQUE KEY `nui` (`param`) USING BTREE
            ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

        ---------
        @param task_table: mysql中的任务表 或 redis中存放任务种子的key，zset类型
        @param task_table_type: 任务表类型 支持 redis 、mysql
        @param task_keys: 需要获取的任务字段 列表 [] 如需指定解析的parser，则需将parser_name字段取出来。
        @param task_state: mysql中任务表的任务状态字段
        @param min_task_count: redis 中最少任务数, 少于这个数量会从种子表中取任务
        @param check_task_interval: 检查是否还有任务的时间间隔；
        @param task_limit: 每次从数据库中取任务的数量
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
        @param batch_interval: 抓取时间间隔 默认为0 天为单位 多次启动时，只有当前时间与第一次抓取结束的时间间隔大于指定的时间间隔时，爬虫才启动
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
        self._task_keys = task_keys  # 需要获取的任务字段
        self._task_table_type = task_table_type

        if self._task_table_type == "mysql" and not self._task_keys:
            raise Exception("需指定任务字段 使用task_keys")

        self._task_state = task_state  # mysql中任务表的state字段名
        self._min_task_count = min_task_count  # redis 中最少任务数
        self._check_task_interval = check_task_interval
        self._task_limit = task_limit  # mysql中一次取的任务数量
        self._related_task_tables = [
            setting.TAB_REQUESTS.format(redis_key=redis_key)
        ]  # 自己的task表也需要检查是否有任务
        if related_redis_key:
            self._related_task_tables.append(
                setting.TAB_REQUESTS.format(redis_key=related_redis_key)
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
        self.reset_task(heartbeat_interval=60)

    def init_property(self):
        """
        每个批次开始时需要重置的属性
        @return:
        """
        self._last_send_msg_time = None

        self._spider_last_done_time = None
        self._spider_last_done_count = 0  # 爬虫刚开始启动时已做任务数量

    def add_parser(self, parser, **kwargs):
        parser = parser(
            self._task_table,
            self._task_state,
            self._mysqldb,
            **kwargs,
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

        # 添加任务
        for parser in self._parsers:
            parser.add_task()

        while True:
            try:
                # 检查redis中是否有任务 任务小于_min_task_count 则从mysql中取
                tab_requests = setting.TAB_REQUESTS.format(redis_key=self._redis_key)
                todo_task_count = self._redisdb.zget_count(tab_requests)

                tasks = []
                if todo_task_count < self._min_task_count:
                    tasks = self.get_task(todo_task_count)
                    if not tasks:
                        if not todo_task_count:
                            if self._keep_alive:
                                log.info("任务均已做完，爬虫常驻, 等待新任务")
                                time.sleep(self._check_task_interval)
                                continue
                            else:
                                log.info("任务均已做完，爬虫结束")
                                break

                else:
                    log.info("redis 中尚有%s条积压任务，暂时不派发新任务" % todo_task_count)

                if not tasks:
                    if todo_task_count >= self._min_task_count:
                        # log.info('任务正在进行 redis中剩余任务 %s' % todo_task_count)
                        pass
                    else:
                        log.info("无待做种子 redis中剩余任务 %s" % todo_task_count)
                else:
                    # make start requests
                    self.distribute_task(tasks)
                    log.info(f"添加任务到redis成功 共{len(tasks)}条")

            except Exception as e:
                log.exception(e)

            time.sleep(self._check_task_interval)

    def get_task(self, todo_task_count) -> List[Union[Tuple, Dict]]:
        """
        获取任务
        Args:
            todo_task_count: redis里剩余的任务数

        Returns:

        """
        tasks = []
        if self._task_table_type == "mysql":
            # 从mysql中取任务
            log.info("redis 中剩余任务%s 数量过小 从mysql中取任务追加" % todo_task_count)
            tasks = self.get_todo_task_from_mysql()
            if not tasks:  # 状态为0的任务已经做完，需要检查状态为2的任务是否丢失
                # redis 中无待做任务，此时mysql中状态为2的任务为丢失任务。需重新做
                if todo_task_count == 0:
                    log.info("无待做任务，尝试取丢失的任务")
                    tasks = self.get_doing_task_from_mysql()
        elif self._task_table_type == "redis":
            log.info("redis 中剩余任务%s 数量过小 从redis种子任务表中取任务追加" % todo_task_count)
            tasks = self.get_task_from_redis()
        else:
            raise Exception(
                f"task_table_type expect mysql or redis，bug got {self._task_table_type}"
            )

        return tasks

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
                        if isinstance(task, dict):
                            task = PerfectDict(_dict=task)
                        else:
                            task = PerfectDict(
                                _dict=dict(zip(self._task_keys, task)),
                                _values=list(task),
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
                                    >= setting.ITEM_MAX_CACHED_COUNT
                                ):
                                    self._item_buffer.flush()

                            elif callable(request):  # callbale的request可能是更新数据库操作的函数
                                if result_type == 1:
                                    self._request_buffer.put_request(request)
                                else:
                                    self._item_buffer.put_item(request)

                                    if (
                                        self._item_buffer.get_items_count()
                                        >= setting.ITEM_MAX_CACHED_COUNT
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
                    if isinstance(task, dict):
                        task = PerfectDict(_dict=task)
                    else:
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
                                >= setting.ITEM_MAX_CACHED_COUNT
                            ):
                                self._item_buffer.flush()

                        elif callable(request):  # callbale的request可能是更新数据库操作的函数
                            if result_type == 1:
                                self._request_buffer.put_request(request)
                            else:
                                self._item_buffer.put_item(request)

                                if (
                                    self._item_buffer.get_items_count()
                                    >= setting.ITEM_MAX_CACHED_COUNT
                                ):
                                    self._item_buffer.flush()

        self._request_buffer.flush()
        self._item_buffer.flush()

    def get_task_from_redis(self):
        tasks = self._redisdb.zget(self._task_table, count=self._task_limit)
        tasks = [eval(task) for task in tasks]
        return tasks

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
        sql = "select count(1) from %s where %s = 2%s" % (
            self._task_table,
            self._task_state,
            self._task_condition_prefix_and,
        )
        doing_count = self._mysqldb.find(sql)[0][0]
        return doing_count

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

    # -------- 批次结束逻辑 ------------

    def task_is_done(self):
        """
        @summary: 检查种子表是否做完
        ---------
        ---------
        @result: True / False （做完 / 未做完）
        """
        is_done = False
        if self._task_table_type == "mysql":
            sql = "select 1 from %s where (%s = 0 or %s=2)%s limit 1" % (
                self._task_table,
                self._task_state,
                self._task_state,
                self._task_condition_prefix_and,
            )
            count = self._mysqldb.find(sql)  # [(1,)]  / []
        elif self._task_table_type == "redis":
            count = self._redisdb.zget_count(self._task_table)
        else:
            raise Exception(
                f"task_table_type expect mysql or redis，bug got {self._task_table_type}"
            )

        if not count:
            log.info("种子表中任务均已完成")
            is_done = True

        return is_done

    def run(self):
        """
        @summary: 重写run方法 检查mysql中的任务是否做完， 做完停止
        ---------
        ---------
        @result:
        """
        try:
            if not self._parsers:  # 不是add_parser 模式
                self._parsers.append(self)

            self._start()

            while True:
                try:
                    self.heartbeat()
                    if (
                        self.all_thread_is_done() and self.task_is_done()
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

                except Exception as e:
                    log.exception(e)

                tools.delay_time(10)  # 10秒钟检查一次爬虫状态

        except Exception as e:
            msg = "《%s》主线程异常 爬虫结束 exception: %s" % (self.name, e)
            log.error(msg)
            self.send_msg(
                msg, level="error", message_prefix="《%s》爬虫异常结束".format(self.name)
            )

            os._exit(137)  # 使退出码为35072 方便爬虫管理器重启

    @classmethod
    def to_DebugTaskSpider(cls, *args, **kwargs):
        # DebugBatchSpider 继承 cls
        DebugTaskSpider.__bases__ = (cls,)
        DebugTaskSpider.__name__ = cls.__name__
        return DebugTaskSpider(*args, **kwargs)


class DebugTaskSpider(TaskSpider):
    """
    Debug批次爬虫
    """

    __debug_custom_setting__ = dict(
        COLLECTOR_TASK_COUNT=1,
        # SPIDER
        SPIDER_THREAD_COUNT=1,
        SPIDER_SLEEP_TIME=0,
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

        super(DebugTaskSpider, self).__init__(*args, **kwargs)

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
                log.debug("正在清理表 %s" % table)
                redis.clear(table)

    def run(self):
        self.start_monitor_task()

        if not self._parsers:  # 不是add_parser 模式
            self._parsers.append(self)

        self._start()

        while True:
            try:
                if self.all_thread_is_done():
                    self._stop_all_thread()
                    break

            except Exception as e:
                log.exception(e)

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
