# -*- coding: utf-8 -*-
"""
Created on 2018-06-19 17:17
---------
@summary: request 管理器， 负责缓冲添加到数据库中的request
---------
@author: Boris
@email: boris@bzkj.tech
"""

import collections
import threading

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.db.redisdb import RedisDB
from feapder.utils.log import log
from feapder.dedup import Dedup

MAX_URL_COUNT = 1000  # 缓存中最大request数


class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_inst"):
            cls._inst = super(Singleton, cls).__new__(cls)

        return cls._inst


class RequestBuffer(threading.Thread, Singleton):
    dedup = None

    def __init__(self, redis_key):
        if not hasattr(self, "_requests_deque"):
            super(RequestBuffer, self).__init__()

            self._thread_stop = False
            self._is_adding_to_db = False

            self._requests_deque = collections.deque()
            self._del_requests_deque = collections.deque()
            self._db = RedisDB()

            self._table_request = setting.TAB_REQUSETS.format(redis_key=redis_key)
            self._table_failed_request = setting.TAB_FAILED_REQUSETS.format(
                redis_key=redis_key
            )

            if not self.__class__.dedup and setting.REQUEST_FILTER_ENABLE:
                self.__class__.dedup = Dedup(
                    filter_type=Dedup.ExpireFilter,
                    name=redis_key,
                    expire_time=2592000,
                    to_md5=False,
                )  # 过期时间为一个月

    def run(self):
        while not self._thread_stop:
            try:
                self.__add_request_to_db()
            except Exception as e:
                log.exception(e)

            tools.delay_time(1)

    def stop(self):
        self._thread_stop = True

    def put_request(self, request):
        self._requests_deque.append(request)

        if self.get_requests_count() > MAX_URL_COUNT:  # 超过最大缓存，主动调用
            self.flush()

    def put_del_request(self, request):
        self._del_requests_deque.append(request)

    def put_failed_request(self, request, table=None):
        try:
            request_dict = request.to_dict
            self._db.zadd(
                table or self._table_failed_request, str(request_dict), request.priority
            )
        except Exception as e:
            log.exception(e)

    def flush(self):
        try:
            self.__add_request_to_db()
        except Exception as e:
            log.exception(e)

    def get_requests_count(self):
        return len(self._requests_deque)

    def is_adding_to_db(self):
        return self._is_adding_to_db

    def __add_request_to_db(self):
        request_list = []
        prioritys = []
        callbacks = []

        while self._requests_deque:
            request = self._requests_deque.popleft()
            self._is_adding_to_db = True

            if callable(request):
                # 函数
                # 注意：应该考虑闭包情况。闭包情况可写成
                # def test(xxx = xxx):
                #     # TODO 业务逻辑 使用 xxx
                # 这么写不会导致xxx为循环结束后的最后一个值
                callbacks.append(request)
                continue

            priority = request.priority

            # 如果需要去重并且库中已重复 则continue
            if (
                request.filter_repeat
                and setting.REQUEST_FILTER_ENABLE
                and not self.__class__.dedup.add(request.fingerprint)
            ):
                log.debug("request已存在  url = %s" % request.url)
                continue
            else:
                request_list.append(str(request.to_dict))
                prioritys.append(priority)

            if len(request_list) > MAX_URL_COUNT:
                self._db.zadd(self._table_request, request_list, prioritys)
                request_list = []
                prioritys = []

        # 入库
        if request_list:
            self._db.zadd(self._table_request, request_list, prioritys)

        # 执行回调
        for callback in callbacks:
            try:
                callback()
            except Exception as e:
                log.exception(e)

        # 删除已做任务
        if self._del_requests_deque:
            request_done_list = []
            while self._del_requests_deque:
                request_done_list.append(self._del_requests_deque.popleft())

            # 去掉request_list中的requests， 否则可能会将刚添加的request删除
            request_done_list = list(set(request_done_list) - set(request_list))

            if request_done_list:
                self._db.zrem(self._table_request, request_done_list)

        self._is_adding_to_db = False
