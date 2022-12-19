# -*- coding: utf-8 -*-
"""
Created on 2018/12/13 9:44 PM
---------
@summary: 带有有效期的去重集合
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import time

from feapder.db.redisdb import RedisDB
from feapder.dedup.basefilter import BaseFilter


class ExpireFilter(BaseFilter):
    redis_db = None

    def __init__(
        self, name: str, expire_time: int, expire_time_record_key=None, redis_url=None
    ):
        if not name:
            raise ValueError("name cant't be None")
        if not expire_time:
            raise ValueError("please set expire time, units is seconds")

        if not self.__class__.redis_db:
            self.__class__.redis_db = RedisDB(url=redis_url)

        self.name = name
        self.expire_time = expire_time
        self.expire_time_record_key = expire_time_record_key
        self.del_expire_key_time = None

        self.record_expire_time()

        self.del_expire_key()

    def __repr__(self):
        return "<ExpireSet: {}>".format(self.name)

    @property
    def current_timestamp(self):
        return int(time.time())

    def add(self, keys, *args, **kwargs):
        """
        @param keys: 检查关键词在zset中是否存在，支持列表批量
        @return: list / 单个值
        """
        if self.current_timestamp - self.del_expire_key_time > self.expire_time:
            self.del_expire_key()

        is_added = self.redis_db.zadd(self.name, keys, self.current_timestamp)
        return is_added

    def get(self, keys):
        is_exist = self.redis_db.zexists(self.name, keys)
        if isinstance(keys, list):
            # 判断数据本身是否重复
            temp_set = set()
            for i, key in enumerate(keys):
                if key in temp_set:
                    is_exist[i] = 1
                else:
                    temp_set.add(key)

        return is_exist

    def del_expire_key(self):
        self.redis_db.zremrangebyscore(
            self.name, "-inf", self.current_timestamp - self.expire_time
        )
        self.del_expire_key_time = self.current_timestamp

    def record_expire_time(self):
        if self.expire_time_record_key:
            self.redis_db.hset(
                self.expire_time_record_key, key=self.name, value=self.expire_time
            )
