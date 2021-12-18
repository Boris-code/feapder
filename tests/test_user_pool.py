# -*- coding: utf-8 -*-
"""
Created on 2021/9/13 2:33 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import time
import unittest
from typing import Optional

from feapder.network.user_pool import GuestUser
from feapder.network.user_pool import GuestUserPool
from feapder.network.user_pool import NormalUser
from feapder.network.user_pool import NormalUserPool


class TestUserPool(unittest.TestCase):
    def test_GuestUserPool(self):
        """
        测试直接获取游客用户
        Returns:

        """
        user_pool = GuestUserPool("test:user_pool", page_url="https://www.baidu.com")
        user = user_pool.get_user(block=True)
        print("取到user：", user)
        print("cookie：", user.cookies)
        print("user_agent：", user.user_agent)
        print("proxies：", user.proxies)
        user_pool.del_user(user.user_id)

    def test_GuestUserPool_keep_alive(self):
        """
        测试生产游客用户，面对需要大量cookie，需要单独起个进程维护cookie的场景
        Returns:

        """

        # 默认的GuestUserPool是通过浏览器获取cookie，开发者可以继承默认的，重写create_user方法
        class CustomGuestUserPool(GuestUserPool):
            def login(self) -> Optional[GuestUser]:
                # 此处为假数据，正常需通过网站获取cookie
                user = GuestUser(
                    user_agent="xxx",
                    proxies="yyy",
                    cookies={"some_key": "some_value{}".format(time.time())},
                )
                return user

        # 最少保持10个cookie，常驻，以便不够及时补充
        user_pool = CustomGuestUserPool(
            "test:user_pool", min_users=10, keep_alive=False
        )
        user_pool.run()

    def test_NormalUserPool(self):
        class CustomNormalUserPool(NormalUserPool):
            def login(self, user: NormalUser) -> NormalUser:
                # 此处为假数据，正常需通过登录网站获取cookie
                username = user.username
                password = user.password

                # 登录获取cookie
                cookie = "xxx"
                user.cookies = cookie

                return user

        user_pool = CustomNormalUserPool(
            "test:user_pool", table_userbase="test_userbase", login_retry_times=0
        )
        user = user_pool.get_user()
        print("取到user：", user)
        print("cookie：", user.cookies)
        print("user_agent：", user.user_agent)
        print("proxies：", user.proxies)
        user_pool.del_user(user.user_id)

        # user_pool.del_user(1)
        # user_pool.tag_user_locked(2)

    def test_NormalUserPool_keep_alive(self):
        class CustomNormalUserPool(NormalUserPool):
            def login(self, user: NormalUser) -> NormalUser:
                # 此处为假数据，正常需通过登录网站获取cookie
                username = user.username
                password = user.password

                # 登录获取cookie
                cookie = "xxx"
                user.cookies = cookie

                return user

        user_pool = CustomNormalUserPool(
            "test:user_pool",
            table_userbase="test_userbase",
            login_retry_times=1,
            keep_alive=True,
        )
        user_pool.run()


if __name__ == "__main__":
    unittest.main()
