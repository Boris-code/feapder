# -*- coding: utf-8 -*-
"""
Created on 2021/9/13 2:33 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from feapder.network.cookie_pool import PageCookiePool,LoginCookiePool, LimitTimesUserPool


import unittest



class TestCookiePool(unittest.TestCase):
    def test_page_cookie_pool(self):
        cookie_pool = PageCookiePool(redis_key="test:page_cookie_pool", page_url="https://www.baidu.com")
        cookies = cookie_pool.get_cookie()
        print(cookies)

    def test_login_cookie_pool(self):
        cookie_pool = LoginCookiePool("test:login_cookie_pool", tab_userbase="test_userbase")
        cookie = cookie_pool.get_cookie()
        print(cookie)

if __name__ == "__main__":
    unittest.main()