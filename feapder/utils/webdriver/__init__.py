# -*- coding: utf-8 -*-
"""
Created on 2022/9/7 4:39 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
from .playwright_driver import PlaywrightDriver
from .selenium_driver import SeleniumDriver
from .webdirver import InterceptRequest, InterceptResponse
from .webdriver_pool import WebDriverPool

# 为了兼容老代码
WebDriver = SeleniumDriver
