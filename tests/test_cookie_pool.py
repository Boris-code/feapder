# -*- coding: utf-8 -*-
"""
Created on 2021/9/13 2:33 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from feapder.network.cookie_pool import LoginCookiePool

cookie_pool = LoginCookiePool("test:login_cookie_pool", tab_userbase="test_userbase")
cookie = cookie_pool.get_cookie()
print(cookie)