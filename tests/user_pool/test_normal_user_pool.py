# -*- coding: utf-8 -*-
"""
Created on 2021/9/13 2:33 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import unittest

from feapder.network.user_pool import NormalUser
from feapder.network.user_pool import NormalUserPool


class TestUserPool(unittest.TestCase):
    def setUp(self) -> None:
        class CustomNormalUserPool(NormalUserPool):
            def login(self, user: NormalUser) -> NormalUser:
                # 此处为假数据，正常需通过登录网站获取cookie
                username = user.username
                password = user.password

                # 登录获取cookie
                cookie = "xxx"
                user.cookies = cookie

                return user

        self.user_pool = CustomNormalUserPool(
            "test:user_pool",
            table_userbase="test_userbase",
            login_retry_times=0,
            keep_alive=True,
        )

    def test_get_user(self):
        user = self.user_pool.get_user()
        print("取到user：", user)
        print("cookie：", user.cookies)
        print("user_agent：", user.user_agent)
        print("proxies：", user.proxies)

    def test_del_user(self):
        self.user_pool.del_user(1)

    def test_tag_user_locked(self):
        self.user_pool.tag_user_locked(2)

    def test_keep_alive(self):
        self.user_pool.run()


if __name__ == "__main__":
    unittest.main()
