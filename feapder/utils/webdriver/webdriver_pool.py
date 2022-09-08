# -*- coding: utf-8 -*-
"""
Created on 2021/3/18 4:59 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import logging
import queue
import threading

from feapder.utils.log import OTHERS_LOG_LEVAL
from feapder.utils.tools import Singleton
from feapder.utils.webdriver.selenium_driver import SeleniumDriver
from feapder.utils.webdriver.webdirver import WebDriver

# 屏蔽webdriver_manager日志
logging.getLogger("WDM").setLevel(OTHERS_LOG_LEVAL)


@Singleton
class WebDriverPool:
    def __init__(self, pool_size=5, driver: WebDriver = SeleniumDriver, **kwargs):
        self.queue = queue.Queue(maxsize=pool_size)
        self.kwargs = kwargs
        self.lock = threading.RLock()
        self.driver_count = 0
        self.driver = driver

    @property
    def is_full(self):
        return self.driver_count >= self.queue.maxsize

    def get(self, user_agent: str = None, proxy: str = None):
        """
        获取webdriver
        当webdriver为新实例时会使用 user_agen, proxy, cookie参数来创建
        Args:
            user_agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36
            proxy: xxx.xxx.xxx.xxx
        Returns:

        """
        if not self.is_full:
            with self.lock:
                if not self.is_full:
                    kwargs = self.kwargs.copy()
                    if user_agent:
                        kwargs["user_agent"] = user_agent
                    if proxy:
                        kwargs["proxy"] = proxy
                    driver = self.driver(**kwargs)
                    self.queue.put(driver)
                    self.driver_count += 1

        driver = self.queue.get()
        return driver

    def put(self, driver):
        self.queue.put(driver)

    def remove(self, driver):
        driver.quit()
        self.driver_count -= 1

    def close(self):
        while not self.queue.empty():
            driver = self.queue.get()
            driver.quit()
            self.driver_count -= 1
