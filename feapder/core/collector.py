# -*- coding: utf-8 -*-
"""
Created on 2016-12-23 11:24
---------
@summary: request 管理
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import collections
import threading
import time

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.db.redisdb import RedisDB
from feapder.network.request import Request
from feapder.utils.log import log


class Collector(threading.Thread):
    def __init__(self, redis_key):
        """
        @summary:
        ---------
        @param redis_key:
        ---------
        @result:
        """

        super(Collector, self).__init__()
        self._db = RedisDB()

        self._thread_stop = False

        self._todo_requests = collections.deque()

        self._tab_requests = setting.TAB_REQUSETS.format(redis_key=redis_key)
        self._tab_spider_status = setting.TAB_SPIDER_STATUS.format(redis_key=redis_key)

        self._spider_mark = tools.get_localhost_ip() + f"-{time.time()}"

        self._interval = setting.COLLECTOR_SLEEP_TIME
        self._request_count = setting.COLLECTOR_TASK_COUNT
        self._is_collector_task = False
        self._first_get_task = True

        self.__delete_dead_node()

    def run(self):
        while not self._thread_stop:
            try:
                self.__report_node_heartbeat()
                self.__input_data()
            except Exception as e:
                log.exception(e)

            self._is_collector_task = False

            time.sleep(self._interval)

    def stop(self):
        self._thread_stop = True
        self._started.clear()

    def __input_data(self):
        current_timestamp = tools.get_current_timestamp()
        if len(self._todo_requests) >= self._request_count:
            return

        request_count = self._request_count  # 先赋值
        # 查询最近有心跳的节点数量
        spider_count = self._db.zget_count(
            self._tab_spider_status,
            priority_min=current_timestamp - (self._interval + 10),
            priority_max=current_timestamp,
        )
        # 根据等待节点数量，动态分配request
        if spider_count:
            # 任务数量
            task_count = self._db.zget_count(self._tab_requests)
            # 动态分配的数量 = 任务数量 / 休息的节点数量 + 1
            request_count = task_count // spider_count + 1

        request_count = (
            request_count
            if request_count <= self._request_count
            else self._request_count
        )

        if not request_count:
            return

        # 当前无其他节点，并且是首次取任务，则重置丢失的任务
        if self._first_get_task and spider_count <= 1:
            datas = self._db.zrangebyscore_set_score(
                self._tab_requests,
                priority_min=current_timestamp,
                priority_max=current_timestamp + setting.REQUEST_LOST_TIMEOUT,
                score=300,
                count=None,
            )
            self._first_get_task = False
            lose_count = len(datas)
            if lose_count:
                log.info("重置丢失任务完毕，共{}条".format(len(datas)))

        # 取任务，只取当前时间搓以内的任务，同时将任务分数修改为 current_timestamp + setting.REQUEST_LOST_TIMEOUT
        requests_list = self._db.zrangebyscore_set_score(
            self._tab_requests,
            priority_min="-inf",
            priority_max=current_timestamp,
            score=current_timestamp + setting.REQUEST_LOST_TIMEOUT,
            count=request_count,
        )

        if requests_list:
            self._is_collector_task = True
            # 存request
            self.__put_requests(requests_list)

    def __report_node_heartbeat(self):
        """
        汇报节点心跳，以便任务平均分配
        """
        self._db.zadd(
            self._tab_spider_status, self._spider_mark, tools.get_current_timestamp()
        )

    def __delete_dead_node(self):
        """
        删除没有心跳的节点信息
        """
        self._db.zremrangebyscore(
            self._tab_spider_status,
            "-inf",
            tools.get_current_timestamp() - (self._interval + 10),
        )

    def __put_requests(self, requests_list):
        for request in requests_list:
            try:
                request_dict = {
                    "request_obj": Request.from_dict(eval(request)),
                    "request_redis": request,
                }
            except Exception as e:
                log.exception(
                    """
                error %s
                request %s
                """
                    % (e, request)
                )

                request_dict = None

            if request_dict:
                self._todo_requests.append(request_dict)

    def get_requests(self, count):
        requests = []
        count = count if count <= len(self._todo_requests) else len(self._todo_requests)
        while count:
            requests.append(self._todo_requests.popleft())
            count -= 1

        return requests

    def get_requests_count(self):
        return len(self._todo_requests) or self._db.zget_count(self._tab_requests) or 0

    def is_collector_task(self):
        return self._is_collector_task
