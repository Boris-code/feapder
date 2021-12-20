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
from feapder.network.user_pool import GoldUser
from feapder.network.user_pool import GoldUserPool


class TestUserPool(unittest.TestCase):
    def setUp(self) -> None:
        # 默认的用户池，使用webdriver访问page_url生产cookie
        self.user_pool = GuestUserPool(
            "test:user_pool", page_url="https://www.baidu.com"
        )

        # 自定义生产cookie的方法
        class CustomGuestUserPool(GuestUserPool):
            def login(self) -> Optional[GuestUser]:
                # 此处为假数据，正常需通过网站获取cookie
                user = GuestUser(
                    user_agent="xxx",
                    proxies="yyy",
                    cookies={"some_key": "some_value{}".format(time.time())},
                )
                return user

        self.custom_user_pool = CustomGuestUserPool(
            "test:custom_user_pool", min_users=10, keep_alive=True
        )

    def test_get_user(self):
        """
        测试直接获取游客用户
        Returns:

        """
        user = self.custom_user_pool.get_user(block=True)
        print("取到user：", user)
        print("cookie：", user.cookies)
        print("user_agent：", user.user_agent)
        print("proxies：", user.proxies)

    def test_del_user(self):
        user = GuestUser(
            **{
                "user_id": "9f1654ba654e12adfea548eae89a8f6f",
                "user_agent": "xxx",
                "proxies": "yyy",
                "cookies": {"some_key": "some_value1640006728.908013"},
            }
        )
        print(user.user_id)
        self.custom_user_pool.del_user(user.user_id)

    def test_keep_alive(self):
        """
        测试生产游客用户，面对需要大量cookie，需要单独起个进程维护cookie的场景
        Returns:

        """

        self.custom_user_pool.run()


if __name__ == "__main__":
    unittest.main()
