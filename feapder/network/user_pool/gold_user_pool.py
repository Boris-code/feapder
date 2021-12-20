# -*- coding: utf-8 -*-
"""
Created on 2018/12/27 11:32 AM
---------
@summary: 账号昂贵、限制查询次数及使用时间的用户UserPool
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import os
import random
import time
from enum import Enum, unique
from typing import Optional, List

from feapder import setting
from feapder.db.redisdb import RedisDB
from feapder.network.user_pool.base_user_pool import GoldUser, UserPoolInterface
from feapder.utils import metrics
from feapder.utils.log import log
from feapder.utils.redis_lock import RedisLock
from feapder.utils.tools import send_msg


@unique
class GoldUserStatus(Enum):
    # 使用状态
    USED = "used"
    SUCCESS = "success"
    OVERDUE = "overdue"  # cookie 过期
    SLEEP = "sleep"
    EXCEPTION = "exception"
    # 登陆状态
    LOGIN_SUCCESS = "login_success"
    LOGIN_FALIED = "login_failed"


class GoldUserPool(UserPoolInterface):
    """
    账号昂贵、限制查询次数的用户的UserPool
    """

    def __init__(
        self,
        redis_key,
        *,
        users: List[GoldUser],
        keep_alive=False,
    ):
        """
        @param redis_key: user存放在redis中的key前缀
        @param users: 账号信息
        @param keep_alive: 是否保持常驻，以便user不足时立即补充
        """
        self._tab_user_pool = setting.TAB_USER_POOL.format(
            redis_key=redis_key, user_type="gold"
        )

        self.users = users
        self._keep_alive = keep_alive

        self._redisdb = RedisDB()
        self._users_id = []

        if not users:
            raise ValueError("not users")

        # 给user的类属性复制
        self.users[0].__class__.redisdb = self._redisdb
        self.users[0].__class__.redis_key = self._tab_user_pool

        self.__init_metrics()
        self.__sync_users_base_info()
        self.__sycn_users_info()

    def __init_metrics(self):
        metrics.init(**setting.METRICS_OTHER_ARGS)

    def __sync_users_base_info(self):
        # 本地同步基本信息到redis, 注 只能在初始化函数内同步
        for user in self.users:
            cache_user = self.get_user_by_id(user.user_id)
            if cache_user:
                for key, value in user.to_dict().items():
                    if not key.startswith("_"):
                        setattr(cache_user, key, value)
                cache_user.sycn_to_redis()

    def __sycn_users_info(self):
        # redis同步登录信息到本地
        for index, user in enumerate(self.users):
            cache_user = self.get_user_by_id(user.user_id)
            if cache_user:
                self.users[index] = cache_user

    def _load_users_id(self):
        self._users_id = self._redisdb.hkeys(self._tab_user_pool)
        if self._users_id:
            random.shuffle(self._users_id)

    def _get_user_id(self):
        if not self._users_id:
            self._load_users_id()

        if self._users_id:
            return self._users_id.pop()

    def login(self, user: GoldUser) -> GoldUser:
        """
        登录 生产cookie
        """
        raise NotImplementedError

    def get_user_by_id(self, user_id: str) -> GoldUser:
        user_str = self._redisdb.hget(self._tab_user_pool, user_id)
        if user_str:
            user = GoldUser(**eval(user_str))
            return user

    def get_user(
        self,
        block=True,
        username=None,
        used_for_spider_name=None,
        not_limit_use_interval=False,
    ) -> Optional[GoldUser]:
        """
        @params username: 获取指定的用户
        @params used_for_spider_name: 独享式使用，独享爬虫的名字。其他爬虫不可抢占
        @params block: 无用户时是否等待
        @params not_limit_frequence: 不限制使用频率
        @return: GoldUser
        """
        while True:
            try:
                user_id = username or self._get_user_id()
                user_str = None
                if user_id:
                    user_str = self._redisdb.hget(self._tab_user_pool, user_id)

                if (not user_id or not user_str) and block:
                    self._keep_alive = False
                    self.run(username)
                    continue

                # 取到用户
                user = GoldUser(**eval(user_str))

                # 独占式使用，若为其他爬虫，检查等待使用时间是否超过独占时间，若超过则可以使用
                if (
                    user.get_used_for_spider_name()
                    and user.get_used_for_spider_name() != used_for_spider_name
                ):
                    wait_time = time.time() - user.get_last_use_time()
                    if wait_time < user.exclusive_time:
                        log.info(
                            "用户{} 被 {} 爬虫独占，需等待 {} 秒后才可使用".format(
                                user.username,
                                user.get_used_for_spider_name(),
                                user.exclusive_time - wait_time,
                            )
                        )
                        time.sleep(1)
                        continue

                if not user.is_overwork() and user.is_at_work_time():
                    if not user.cookies:
                        log.debug(f"用户 {user.username} 未登录，尝试登录")
                        self._keep_alive = False
                        self.run(username)
                        continue

                    if not_limit_use_interval or user.is_time_to_use():
                        user.set_used_for_spider_name(used_for_spider_name)
                        log.debug("使用用户 {}".format(user.username))
                        self.record_user_status(user.user_id, GoldUserStatus.USED)
                        return user
                    else:
                        log.debug("{} 用户使用间隔过短 查看下一个用户".format(user.username))
                        time.sleep(1)
                        continue
                else:
                    if not user.is_at_work_time():
                        log.info("用户 {} 不在工作时间 sleep 60s".format(user.username))
                        if block:
                            time.sleep(60)
                            continue
                        else:
                            return None

            except Exception as e:
                log.exception(e)
                time.sleep(1)

    def del_user(self, user_id: str):
        user = self.get_user_by_id(user_id)
        if user:
            user.set_cookies(None)
            self.record_user_status(user.user_id, GoldUserStatus.OVERDUE)

    def add_user(self, user: GoldUser):
        user.sycn_to_redis()

    def delay_use(self, user_id: str, delay_seconds: int):
        user = self.get_user_by_id(user_id)
        if user:
            user.set_delay_use(delay_seconds)

        self.record_user_status(user_id, GoldUserStatus.SLEEP)

    def record_success_user(self, user_id: str):
        self.record_user_status(user_id, GoldUserStatus.SUCCESS)

    def record_exception_user(self, user_id: str):
        self.record_user_status(user_id, GoldUserStatus.EXCEPTION)

    def run(self, username=None):
        while True:
            try:
                with RedisLock(
                    key=self._tab_user_pool, lock_timeout=3600, wait_timeout=0
                ) as _lock:
                    if _lock.locked:
                        self.__sycn_users_info()
                        online_user = 0
                        for user in self.users:
                            if username and username != user.username:
                                continue

                            try:
                                if user.cookies:
                                    online_user += 1
                                    continue

                                # 预检查
                                if not user.is_time_to_login():
                                    log.info(
                                        "账号{}与上次登录时间间隔过短，暂不登录: 将在{}登录使用".format(
                                            user.username, user.next_login_time()
                                        )
                                    )
                                    continue

                                user = self.login(user)
                                if user.cookies:
                                    # 保存cookie
                                    user.set_login_time()
                                    self.add_user(user)
                                    self.record_user_status(
                                        user.user_id, GoldUserStatus.LOGIN_SUCCESS
                                    )
                                    log.debug("登录成功 {}".format(user.username))
                                    online_user += 1
                                else:
                                    log.info("登录失败 {}".format(user.username))
                                    self.record_user_status(
                                        user.user_id, GoldUserStatus.LOGIN_FALIED
                                    )
                            except NotImplementedError:
                                log.error(
                                    f"{self.__class__.__name__} must be implementation login method！"
                                )
                                os._exit(0)
                            except Exception as e:
                                log.exception(e)
                                msg = f"{user.username} 账号登陆失败 exception: {str(e)}"
                                log.info(msg)
                                self.record_user_status(
                                    user.user_id, GoldUserStatus.LOGIN_FALIED
                                )

                                send_msg(
                                    msg=msg,
                                    level="error",
                                    message_prefix=f"{user.username} 账号登陆失败",
                                )

                        log.info("当前在线user数为 {}".format(online_user))

                if self._keep_alive:
                    time.sleep(10)
                else:
                    break

            except Exception as e:
                log.exception(e)
                time.sleep(1)

    def record_user_status(self, user_id: str, status: GoldUserStatus):
        metrics.emit_counter(user_id, 1, classify=f"users_{status.value}")
