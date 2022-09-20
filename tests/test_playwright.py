# -*- coding: utf-8 -*-
"""
Created on 2022/9/15 8:47 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
from feapder.utils.webdriver import PlaywrightDriver


def test():
    url = "https://baijiahao.baidu.com/s?id=1742099690396876260&wfr=spider&for=pc"
    driver = PlaywrightDriver()
    driver.page.goto(url)
    print(driver.page.content())


test()
