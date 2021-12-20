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

from feapder.network.user_pool import GoldUser
from feapder.network.user_pool import GoldUserPool


class TestUserPool(unittest.TestCase):
    def setUp(self) -> None:
        users = [
            GoldUser(
                username="zhangsan",
                password="1234",
                max_use_times=10,
                use_interval=5,
            ),
            GoldUser(
                username="lisi",
                password="1234",
                max_use_times=10,
                use_interval=5,
                login_interval=50,
            ),
        ]

        class CustomGoldUserPool(GoldUserPool):
            def login(self, user: GoldUser) -> GoldUser:
                # 此处为假数据，正常需通过登录网站获取cookie
                username = user.username
                password = user.password

                # 登录获取cookie
                cookie = "zzzz"
                user.cookies = cookie

                return user

        self.user_pool = CustomGoldUserPool(
            "test:user_pool",
            users=users,
            keep_alive=True,
        )

    def test_run(self):
        self.user_pool.run()

    def test_get_user(self):
        user = self.user_pool.get_user()
        print(user)

        user = self.user_pool.get_user(username="zhangsan")
        print(user)

    def test_del_user(self):
        self.user_pool.del_user("lisi")

    def test_delay_user(self):
        user = self.user_pool.get_user(username="lisi")
        print(user)
        self.user_pool.delay_use("lisi", 60)
        user = self.user_pool.get_user(username="lisi")
        print(user)

    def test_exclusive(self):
        """
        测试独占
        """
        # 用户lisi被test_spider爬虫独占
        user = self.user_pool.get_user(
            username="lisi", used_for_spider_name="test_spider"
        )
        print(user)

        # test_spider爬虫可以正常使用
        user = self.user_pool.get_user(
            username="lisi", used_for_spider_name="test_spider"
        )
        print(user)

        # 其他的爬虫需要在独占的间隔后使用
        user = self.user_pool.get_user(username="lisi")
        print(user)


if __name__ == "__main__":
    unittest.main()
