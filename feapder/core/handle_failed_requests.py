# -*- coding: utf-8 -*-
"""
Created on 2018-08-13 11:43:01
---------
@summary:
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""
import feapder.setting as setting
from feapder.buffer.request_buffer import RequestBuffer
from feapder.db.redisdb import RedisDB
from feapder.network.request import Request
from feapder.utils.log import log


class HandleFailedRequests(object):
    """docstring for HandleFailedRequests"""

    def __init__(self, redis_key):
        super(HandleFailedRequests, self).__init__()
        self._redis_key = redis_key

        self._redisdb = RedisDB()
        self._request_buffer = RequestBuffer(self._redis_key)

        self._table_failed_request = setting.TAB_FAILED_REQUESTS.format(
            redis_key=redis_key
        )

    def get_failed_requests(self, count=10000):
        failed_requests = self._redisdb.zget(self._table_failed_request, count=count)
        failed_requests = [eval(failed_request) for failed_request in failed_requests]
        return failed_requests

    def reput_failed_requests_to_requests(self):
        log.debug("正在重置失败的requests...")
        total_count = 0
        while True:
            try:
                failed_requests = self.get_failed_requests()
                if not failed_requests:
                    break

                for request in failed_requests:
                    request["retry_times"] = 0
                    request_obj = Request.from_dict(request)
                    self._request_buffer.put_request(request_obj)

                    total_count += 1
            except Exception as e:
                log.exception(e)

        self._request_buffer.flush()

        log.debug("重置%s条失败requests为待抓取requests" % total_count)
