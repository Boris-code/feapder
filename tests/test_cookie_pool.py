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


class TestCookiePool(unittest.TestCase):
    def test_GuestUserPool(self):
        """
        测试直接获取游客用户
        Returns:

        """
        cookie_pool = GuestUserPool(
            "test:login_cookie_pool", page_url="https://www.baidu.com"
        )
        user = cookie_pool.get_user(block=True)
        print("取到user：", user)
        print("cookie：", user.cookies)
        print("user_agent：", user.user_agent)
        print("proxies：", user.proxies)
        cookie_pool.del_user(user.user_id)

    def test_GuestUserPool_create_user(self):
        """
        测试生产游客用户，面对需要大量cookie，需要单独起个进程维护cookie的场景
        Returns:

        """

        # 默认的GuestUserPool是通过浏览器获取cookie，开发者可以继承默认的，重写create_user方法
        class CookiePool(GuestUserPool):
            def create_user(self) -> Optional[GuestUser]:
                """
                生产用户
                Returns:

                """

                # 此处为假数据，正常需求需通过网站获取cookie
                user = GuestUser(
                    user_agent="xxx",
                    proxies="yyy",
                    cookies={"some_key": "some_value{}".format(time.time())},
                )
                return user

        # 最少保持10个cookie，常驻，以便不够及时补充
        cookie_pool = CookiePool(
            "test:login_cookie_pool", min_users=10, keep_alive=True
        )
        cookie_pool.run()


if __name__ == "__main__":
    unittest.main()
