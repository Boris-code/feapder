# -*- coding: utf-8 -*-
"""
Created on 2016-12-23 11:24
---------
@summary: request 管理
---------
@author: Boris
@email: boris@bzkj.tech
"""

import collections
import threading
import time

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.db.redisdb import RedisDB
from feapder.network.request import Request
from feapder.utils.log import log

LOCAL_HOST_IP = tools.get_localhost_ip()


class Collector(threading.Thread):
    def __init__(self, table_folder, process_num=None):
        """
        @summary:
        ---------
        @param table_folder:
        @param process_num: 进程编号
        ---------
        @result:
        """

        super(Collector, self).__init__()
        self._db = RedisDB()

        self._thread_stop = False

        self._todo_requests = collections.deque()

        self._tab_requests = setting.TAB_REQUSETS.format(table_folder=table_folder)
        self._tab_spider_status = setting.TAB_SPIDER_STATUS.format(
            table_folder=table_folder
        )

        self._spider_mark = LOCAL_HOST_IP + (
            "_%s" % process_num if process_num else "_0"
        )

        self._interval = setting.COLLECTOR_SLEEP_TIME
        self._request_count = setting.COLLECTOR_TASK_COUNT
        self._is_collector_task = False

        self._db.clear(self._tab_spider_status)

    def run(self):
        while not self._thread_stop:

            try:
                self.__input_data()
            except Exception as e:
                log.exception(e)

            self._is_collector_task = False

            time.sleep(self._interval)

    def stop(self):
        self._thread_stop = True

    def __input_data(self):
        if len(self._todo_requests) >= self._request_count:
            return

        # 汇报节点信息
        self._db.zadd(self._tab_spider_status, self._spider_mark, 0)  # 未做

        request_count = self._request_count  # 先赋值
        # 根据等待节点数量，动态分配request
        spider_wait_count = self._db.zget_count(
            self._tab_spider_status, priority_min=0, priority_max=0
        )
        if spider_wait_count:
            # 任务数量
            task_count = self._db.zget_count(self._tab_requests)
            # 动态分配的数量 = 任务数量 / 休息的节点数量 + 1
            request_count = task_count // spider_wait_count + 1

        request_count = (
            request_count
            if request_count <= self._request_count
            else self._request_count
        )

        if not request_count:
            return

        # requests_list = self._db.zget(self._tab_requests, count = request_count)

        # 取任务
        current_timestamp = tools.get_current_timestamp()
        priority_max = current_timestamp - setting.REQUEST_TIME_OUT  # 普通的任务 与 已经超时的任务
        requests_list = self._db.zrangebyscore_set_score(
            self._tab_requests,
            priority_min="-inf",
            priority_max=priority_max,
            score=current_timestamp,
            count=request_count,
        )
        # print('取任务', len(requests_list))

        if not requests_list:
            pass
        else:
            self._is_collector_task = True
            # 将取到的任务放回到redis， 以当前时间戳标记，表示正在做的任务。任务做完在request_buffer中删除，没做完则到超时时间后重新做
            # self._db.zadd(self._tab_requests, requests_list, prioritys=current_timestamp)

            # 汇报节点信息
            self._db.zadd(self._tab_spider_status, self._spider_mark, 1)  # 正在做

            # 存request
            self.__put_requests(requests_list)

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
        return len(self._todo_requests) or self._db.zget_count(self._tab_requests)

    def is_collector_task(self):
        return self._is_collector_task
