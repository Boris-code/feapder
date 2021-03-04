# -*- coding: utf-8 -*-
"""
Created on 2021/3/4 11:01 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from feapder.db.redisdb import RedisDB

redis = RedisDB(ip_ports="localhost:6379", db=0)

redis.lpush("l_test", 2)
redis.lpush("l_test", 3)

print(redis.lrange("l_test"))
print(redis.lrem("l_test", 2))
print(redis.lrange("l_test"))
