# -*- coding: utf-8 -*-
"""
Created on 2018-07-25 11:41:57
---------
@summary: parser 的基类
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""
import os

import feapder.utils.tools as tools
from feapder.db.mysqldb import MysqlDB
from feapder.network.item import UpdateItem
from feapder.utils.log import log


class BaseParser(object):
    def start_requests(self):
        """
        @summary: 添加初始url
        ---------
        ---------
        @result: yield Request()
        """

        pass

    def parse(self, request, response):
        """
        @summary: 默认的回调函数
        ---------
        @param request:
        @param response:
        ---------
        @result:
        """

        pass

    def download_midware(self, request):
        """
        @summary: 下载中间件 可修改请求的一些参数
        ---------
        @param request:
        ---------
        @result: return request / None (不会修改原来的request)
        """

        pass

    def exception_request(self, request, response):
        """
        @summary: 请求或者parser里解析出异常的request
        ---------
        @param request:
        @param response:
        ---------
        @result: request / callback / None (返回值必须可迭代)
        """

        pass

    def failed_request(self, request, response):
        """
        @summary: 超过最大重试次数的request
        可返回修改后的request  若不返回request，则将传进来的request直接人redis的failed表。否则将修改后的request入failed表
        ---------
        @param request:
        ---------
        @result: request / item / callback / None (返回值必须可迭代)
        """

        pass

    def start_callback(self):
        """
        @summary: 程序开始的回调
        ---------
        ---------
        @result: None
        """

        pass

    def end_callback(self):
        """
        @summary: 程序结束的回调
        ---------
        ---------
        @result: None
        """

        pass

    @property
    def name(self):
        return self.__class__.__name__

    def close(self):
        pass


class BatchParser(BaseParser):
    """
    @summary: 批次爬虫模版
    ---------
    """

    def __init__(
        self,
        task_table,
        batch_record_table,
        task_state,
        date_format,
        mysqldb=None,
    ):
        self._mysqldb = mysqldb or MysqlDB()  # mysqldb

        self._task_table = task_table  # mysql中的任务表
        self._batch_record_table = batch_record_table  # mysql 中的批次记录表
        self._task_state = task_state  # mysql中任务表的state字段名
        self._date_format = date_format  # 批次日期格式

    def add_task(self):
        """
        @summary: 添加任务, 每次启动start_monitor 都会调用，且在init_task之前调用
        ---------
        ---------
        @result:
        """

    def start_requests(self, task):
        """
        @summary:
        ---------
        @param task: 任务信息 list
        ---------
        @result:
        """

    def update_task_state(self, task_id, state=1, **kwargs):
        """
        @summary: 更新任务表中任务状态，做完每个任务时代码逻辑中要主动调用。可能会重写
        调用方法为 yield lambda : self.update_task_state(task_id, state)
        ---------
        @param task_id:
        @param state:
        ---------
        @result:
        """

        kwargs["id"] = task_id
        kwargs[self._task_state] = state

        sql = tools.make_update_sql(
            self._task_table, kwargs, condition="id = {task_id}".format(task_id=task_id)
        )

        if self._mysqldb.update(sql):
            log.debug("置任务%s状态成功" % task_id)
        else:
            log.error("置任务%s状态失败  sql=%s" % (task_id, sql))

    def update_task_batch(self, task_id, state=1, **kwargs):
        """
        批量更新任务 多处调用，更新的字段必须一致
        注意：需要 写成 yield update_task_batch(...) 否则不会更新
        @param task_id:
        @param state:
        @param kwargs:
        @return:
        """
        kwargs["id"] = task_id
        kwargs[self._task_state] = state

        update_item = UpdateItem(**kwargs)
        update_item.table_name = self._task_table
        update_item.name_underline = self._task_table + "_item"

        return update_item

    @property
    def batch_date(self):
        """
        @summary: 获取批次时间
        ---------
        ---------
        @result:
        """

        batch_date = os.environ.get("batch_date")
        if not batch_date:
            sql = 'select date_format(batch_date, "{date_format}") from {batch_record_table} order by id desc limit 1'.format(
                date_format=self._date_format.replace(":%M", ":%i"),
                batch_record_table=self._batch_record_table,
            )
            batch_info = MysqlDB().find(sql)  # (('2018-08-19'),)
            if batch_info:
                os.environ["batch_date"] = batch_date = batch_info[0][0]
            else:
                log.error("需先运行 start_monitor_task()")
                os._exit(137)  # 使退出码为35072 方便爬虫管理器重启

        return batch_date
