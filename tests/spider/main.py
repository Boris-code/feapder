# -*- coding: utf-8 -*-
"""
Created on 2021-02-08 16:01:50
---------
@summary: 爬虫入口
---------
@author: liubo
"""

from spiders import *


if __name__ == "__main__":
    test_spider.TestSpider(redis_key="feapder:test_spider").start()
