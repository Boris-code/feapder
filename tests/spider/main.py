# -*- coding: utf-8 -*-
"""
Created on 2021-02-08 16:01:50
---------
@summary: 爬虫入口
---------
@author: liubo
"""

from spiders import *
from feapder import Request
from feapder import ArgumentParser


def spider_test():
    spider = test_spider.TestSpider(redis_key="feapder:test_spider")
    spider.start()


def spider2_test():
    spider = test_spider.TestSpider2(redis_key="feapder:test_spider2")
    spider.start()


def debug_spider_test():
    # debug爬虫
    spider = test_spider.TestSpider.to_DebugSpider(
        redis_key="feapder:test_spider", request=Request("http://www.baidu.com")
    )
    spider.start()


if __name__ == "__main__":
    parser = ArgumentParser(description="Spider测试")

    parser.add_argument(
        "--spider_test", action="store_true", help="测试Spider", function=spider_test
    )
    parser.add_argument(
        "--spider2_test", action="store_true", help="测试Spider2", function=spider2_test
    )
    parser.add_argument(
        "--test_debug_spider",
        action="store_true",
        help="测试DebugSpider",
        function=debug_spider_test,
    )

    parser.start()
