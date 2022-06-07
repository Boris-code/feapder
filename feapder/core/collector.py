# -*- coding: utf-8 -*-
"""
Created on 2016-12-23 11:24
---------
@summary: request 管理
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import threading
import time
from queue import Queue, Empty

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

        self._todo_requests = Queue(maxsize=setting.COLLECTOR_TASK_COUNT)
        self._tab_requests = setting.TAB_REQUESTS.format(redis_key=redis_key)
        self._is_collector_task = False

    def run(self):
        self._thread_stop = False
        while not self._thread_stop:
            try:
                self.__input_data()
            except Exception as e:
                log.exception(e)
                time.sleep(0.1)

            self._is_collector_task = False

    def stop(self):
        self._thread_stop = True
        self._started.clear()

    def __input_data(self):
        if setting.COLLECTOR_TASK_COUNT / setting.SPIDER_THREAD_COUNT > 1 and (
            self._todo_requests.qsize() > setting.SPIDER_THREAD_COUNT
            or self._todo_requests.qsize() >= self._todo_requests.maxsize
        ):
            time.sleep(0.1)
            return

        current_timestamp = tools.get_current_timestamp()

        # 取任务，只取当前时间搓以内的任务，同时将任务分数修改为 current_timestamp + setting.REQUEST_LOST_TIMEOUT
        requests_list = self._db.zrangebyscore_set_score(
            self._tab_requests,
            priority_min="-inf",
            priority_max=current_timestamp,
            score=current_timestamp + setting.REQUEST_LOST_TIMEOUT,
            count=setting.COLLECTOR_TASK_COUNT,
        )

        if requests_list:
            self._is_collector_task = True
            # 存request
            self.__put_requests(requests_list)
        else:
            time.sleep(0.1)

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
                self._todo_requests.put(request_dict)

    def get_request(self):
        try:
            request = self._todo_requests.get(timeout=1)
            return request
        except Empty as e:
            return None

    def get_requests_count(self):
        return (
            self._todo_requests.qsize() or self._db.zget_count(self._tab_requests) or 0
        )

    def is_collector_task(self):
        return self._is_collector_task
