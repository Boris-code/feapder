# -*- coding: utf-8 -*-
"""
Created on 2021-02-08 16:01:50
---------
@summary: 爬虫入口
---------
@author: Boris
"""

from spiders import *

if __name__ == "__main__":
    spider = test_spider.TestSpider(redis_key="feapder3:test_spider", thread_count=100, keep_alive=False)
    spider.start()