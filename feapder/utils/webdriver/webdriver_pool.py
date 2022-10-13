# -*- coding: utf-8 -*-
"""
Created on 2021/3/18 4:59 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import queue
import threading

from feapder.utils.log import log
from feapder.utils.tools import Singleton
from feapder.utils.webdriver.selenium_driver import SeleniumDriver


@Singleton
class WebDriverPool:
    def __init__(
        self, pool_size=5, driver_cls=SeleniumDriver, thread_safe=False, **kwargs
    ):
        """

        Args:
            pool_size: driver池的大小
            driver: 驱动类型
            thread_safe: 是否线程安全
                是则每个线程拥有一个driver，pool_size无效，driver数量为线程数
                否则每个线程从池中获取driver
            **kwargs:
        """
        self.pool_size = pool_size
        self.driver_cls = driver_cls
        self.thread_safe = thread_safe
        self.kwargs = kwargs

        self.queue = queue.Queue(maxsize=pool_size)
        self.lock = threading.RLock()
        self.driver_count = 0
        self.ctx = threading.local()

    @property
    def driver(self):
        if not hasattr(self.ctx, "driver"):
            self.ctx.driver = None
        return self.ctx.driver

    @driver.setter
    def driver(self, driver):
        self.ctx.driver = driver

    @property
    def is_full(self):
        return self.driver_count >= self.pool_size

    def create_driver(self, user_agent: str = None, proxy: str = None):
        kwargs = self.kwargs.copy()
        if user_agent:
            kwargs["user_agent"] = user_agent
        if proxy:
            kwargs["proxy"] = proxy
        return self.driver_cls(**kwargs)

    def get(self, user_agent: str = None, proxy: str = None):
        """
        获取webdriver
        当webdriver为新实例时会使用 user_agen, proxy, cookie参数来创建
        Args:
            user_agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36
            proxy: xxx.xxx.xxx.xxx
        Returns:

        """
        if not self.is_full and not self.thread_safe:
            with self.lock:
                if not self.is_full:
                    driver = self.create_driver(user_agent, proxy)
                    self.queue.put(driver)
                    self.driver_count += 1
        else:
            if not self.driver:
                driver = self.create_driver(user_agent, proxy)
                self.driver = driver
                self.driver_count += 1

        if self.thread_safe:
            driver = self.driver
        else:
            driver = self.queue.get()

        return driver

    def put(self, driver):
        if not self.thread_safe:
            self.queue.put(driver)

    def remove(self, driver):
        if self.thread_safe:
            if self.driver:
                self.driver.quit()
                self.driver = None
        else:
            driver.quit()
        self.driver_count -= 1

    def close(self):
        if self.thread_safe:
            log.info("暂不支持关闭需线程安全的driver")

        while not self.queue.empty():
            driver = self.queue.get()
            driver.quit()
            self.driver_count -= 1
