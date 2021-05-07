# -*- coding: utf-8 -*-
"""
Created on 2021/3/18 7:05 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
from feapder.utils.webdriver import WebDriverPool, WebDriver
import threading


def test_webdirver_pool():

    webdriver_pool = WebDriverPool(
        pool_size=2, load_images=False, driver_type=WebDriver.FIREFOX, timeout=30
    )

    def request():
        try:
            browser = webdriver_pool.get()
            browser.get("https://baidu.com")
            print(browser.title)
            webdriver_pool.put(browser)
        except:
            print("失败")

    for i in range(5):
        threading.Thread(target=request).start()


def test_webdriver():
    with WebDriver(
        load_images=False, driver_type=WebDriver.FIREFOX, timeout=30
    ) as browser:
        browser.get("https://httpbin.org/get")
        html = browser.page_source
        print(html)
