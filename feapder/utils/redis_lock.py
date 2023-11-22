# -*- coding: utf-8 -*-
"""
Created on 2019/11/5 5:25 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import threading
import time

from feapder.db.redisdb import RedisDB
from feapder.utils.log import log


class RedisLock:
    redis_cli = None

    def __init__(
        self, key, *, wait_timeout=0, lock_timeout=86400, redis_cli=None, redis_url=None
    ):
        """
        redis超时锁
        :param key: 存储锁的key redis_lock:[key]
        :param wait_timeout: 等待加锁超时时间，为0时则不等待加锁，加锁失败
        :param lock_timeout: 锁超时时间 为0时则不会超时，直到锁释放或意外退出，默认超时为1天
        :param redis_cli: redis客户端对象
        :param redis_url: redis连接地址，若redis_cli传值，则不使用redis_url

        用法示例:
        with RedisLock(key="test") as _lock:
            if _lock.locked:
                # 用来判断是否加上了锁
                # do somethings
        """
        self.redis_conn = redis_cli
        self.redis_url = redis_url
        self.lock_key = "redis_lock:{}".format(key)
        # 锁超时时间
        self.lock_timeout = lock_timeout
        # 等待加锁时间
        self.wait_timeout = wait_timeout
        self.locked = False
        self.stop_prolong_life = False

    @property
    def redis_conn(self):
        if not self.__class__.redis_cli:
            self.__class__.redis_cli = RedisDB(url=self.redis_url).get_redis_obj()

        return self.__class__.redis_cli

    @redis_conn.setter
    def redis_conn(self, cli):
        if cli:
            self.__class__.redis_cli = cli

    def __enter__(self):
        if not self.locked:
            self.acquire()
            if self.locked:
                # 延长锁的时间
                thread = threading.Thread(target=self.prolong_life)
                thread.daemon = True
                thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_prolong_life = True
        self.release()

    def __repr__(self):
        return "<RedisLock: {} >".format(self.lock_key)

    def acquire(self):
        start = time.time()
        while True:
            # 尝试加锁
            if self.redis_conn.set(self.lock_key, time.time(), nx=True, ex=5):
                self.locked = True
                break

            if self.wait_timeout > 0:
                if time.time() - start > self.wait_timeout:
                    log.debug("获取锁失败")
                    break
            else:
                log.debug("获取锁失败")
                break
            log.debug("等待锁: {} wait:{}".format(self, time.time() - start))
            if self.wait_timeout > 10:
                time.sleep(5)
            else:
                time.sleep(1)
        return

    def release(self):
        if self.locked:
            self.redis_conn.delete(self.lock_key)
            self.locked = False
        return

    def prolong_life(self):
        """
        延长锁的过期时间
        :return:
        """

        spend_time = 0
        while not self.stop_prolong_life:
            expire = self.redis_conn.ttl(self.lock_key)
            if expire < 0:  # key 不存在
                time.sleep(1)
                continue
            self.redis_conn.expire(self.lock_key, expire + 5)  # 延长5秒
            time.sleep(expire)  # 临过期5秒前，再次延长
            spend_time += expire
            if self.lock_timeout and spend_time > self.lock_timeout:
                log.info("锁超时，释放")
                self.redis_conn.delete(self.lock_key)
                break
