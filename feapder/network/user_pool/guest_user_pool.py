# -*- coding: utf-8 -*-
"""
Created on 2018/12/27 11:32 AM
---------
@summary: 访客用户池 不需要登陆
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import random
from typing import Optional

import feapder.utils.tools as tools
from feapder import setting
from feapder.db.redisdb import RedisDB
from feapder.network.user_pool.base_user_pool import UserPoolInterface, GuestUser
from feapder.utils.log import log
from feapder.utils.redis_lock import RedisLock
from feapder.utils.webdriver import WebDriver


class GuestUserPool(UserPoolInterface):
    """
    访客用户池 不需要登陆
    """

    def __init__(
        self,
        redis_key,
        page_url=None,
        min_users=1,
        must_contained_keys=(),
        keep_alive=False,
        **kwargs,
    ):
        """
        @param redis_key: user存放在redis中的key前缀
        @param page_url: 生产user的url
        @param min_users: 最小user数
        @param must_contained_keys: cookie中必须包含的key，用于校验cookie是否正确
        @param keep_alive: 是否保持常驻，以便user不足时立即补充
        ---
        @param kwargs: WebDriver的一些参数
            load_images: 是否加载图片
            user_agent: 字符串 或 无参函数，返回值为user_agent
            proxy: xxx.xxx.xxx.xxx:xxxx 或 无参函数，返回值为代理地址
            headless: 是否启用无头模式
            driver_type: CHROME 或 PHANTOMJS,FIREFOX
            timeout: 请求超时时间
            window_size: # 窗口大小
            executable_path: 浏览器路径，默认为默认路径
        """

        self._redisdb = RedisDB()

        self._tab_user_pool = setting.TAB_USER_POOL.format(
            redis_key=redis_key, user_type="guest"
        )
        self._page_url = page_url
        self._min_users = min_users
        self._must_contained_keys = must_contained_keys
        self._keep_alive = keep_alive

        self._kwargs = kwargs
        self._kwargs.setdefault("load_images", False)
        self._kwargs.setdefault("headless", True)

        self._users_id = []

    def _load_users_id(self):
        self._users_id = self._redisdb.hkeys(self._tab_user_pool)
        if self._users_id:
            random.shuffle(self._users_id)

    def _get_user_id(self):
        if not self._users_id:
            self._load_users_id()

        if self._users_id:
            return self._users_id.pop()

    def login(self) -> Optional[GuestUser]:
        """
        默认使用webdirver去登录，生产cookie，可以重写
        """
        with WebDriver(**self._kwargs) as driver:
            driver.get(self._page_url)

            cookies = driver.cookies

            for key in self._must_contained_keys:
                if key not in cookies:
                    break
            else:
                user = GuestUser(user_agent=driver.user_agent, cookies=cookies)
                return user

            log.error("获取cookie失败 cookies = {}".format(cookies))
            return None

    def add_user(self, user: GuestUser):
        log.debug("add {}".format(user))
        self._redisdb.hset(self._tab_user_pool, user.user_id, user.to_dict())

    def get_user(self, block=True) -> Optional[GuestUser]:
        """

        Args:
            block: 无用户时是否等待

        Returns:

        """
        while True:
            try:
                user_id = self._get_user_id()
                user_str = None
                if user_id:
                    user_str = self._redisdb.hget(self._tab_user_pool, user_id)
                    # 如果没取到user，可能是其他爬虫将此用户删除了，需要重刷新本地缓存的用户id
                    if not user_str:
                        self._load_users_id()
                        continue

                if not user_id and block:
                    self._keep_alive = False
                    self._min_users = 1
                    self.run()
                    continue

                return user_str and GuestUser(**eval(user_str))
            except Exception as e:
                log.exception(e)
                tools.delay_time(1)

    def del_user(self, user_id: str):
        self._redisdb.hdel(self._tab_user_pool, user_id)
        self._load_users_id()

    def run(self):
        while True:
            try:
                now_user_count = self._redisdb.hget_count(self._tab_user_pool)
                need_user_count = self._min_users - now_user_count

                if need_user_count > 0:
                    log.info(
                        "当前在线user数为 {} 小于 {}, 生产user".format(
                            now_user_count, self._min_users
                        )
                    )
                    try:
                        user = self.login()
                        if user:
                            self.add_user(user)
                    except Exception as e:
                        log.exception(e)
                else:
                    log.debug("当前user数为 {} 数量足够 暂不生产".format(now_user_count))

                    if self._keep_alive:
                        tools.delay_time(10)
                    else:
                        break

            except Exception as e:
                log.exception(e)
                tools.delay_time(1)
