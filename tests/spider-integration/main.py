# -*- coding: utf-8 -*-
"""
Created on 2021-03-02 23:38:24
---------
@summary: 爬虫入口
---------
@author: liubo
"""

from feapder import Spider

from spiders import *


def spider_integration_test():
    """
    Spider集成测试
    """
    spider = Spider(redis_key="feapder:test_spider_integration")
    # 集成
    spider.add_parser(sina_news_parser.SinaNewsParser)
    spider.add_parser(tencent_news_parser.TencentNewsParser)

    spider.start()


if __name__ == "__main__":
    spider_integration_test()
