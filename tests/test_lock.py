# -*- coding: utf-8 -*-
"""
Created on 2021/7/15 5:00 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from feapder.utils.redis_lock import RedisLock
from feapder.db.redisdb import RedisDB
import time

def test_lock():
    with RedisLock(key="test", redis_cli=RedisDB().get_redis_obj(), wait_timeout=10) as _lock:
        if _lock.locked:
            print(1)
            time.sleep(100)

if __name__ == '__main__':
    test_lock()