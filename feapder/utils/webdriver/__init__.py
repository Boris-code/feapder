# -*- coding: utf-8 -*-
"""
Created on 2022/9/7 4:39 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
from feapder.utils.webdriver.playwright_driver import PlaywrightDriver
from feapder.utils.webdriver.selenium_driver import SeleniumDriver
from feapder.utils.webdriver.webdriver_pool import WebDriverPool

# 为了兼容老代码
WebDriver = SeleniumDriver