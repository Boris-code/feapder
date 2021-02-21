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


def test_spider():
    spider = test_spider.TestSpider(redis_key="feapder:test_spider")
    spider.start()


def test_spider2():
    spider = test_spider.TestSpider2(redis_key="feapder:test_spider2")
    spider.start()


def test_debug_spider():
    # debug爬虫
    spider = test_spider.TestSpider.to_DebugSpider(
        redis_key="feapder:test_spider", request=Request("http://www.baidu.com")
    )
    spider.start()


if __name__ == "__main__":
    parser = ArgumentParser(description="Spider测试")

    parser.add_argument(
        "--test_spider", action="store_true", help="测试Spider", function=test_spider
    )
    parser.add_argument(
        "--test_spider2", action="store_true", help="测试Spider2", function=test_spider2
    )
    parser.add_argument(
        "--test_debug_spider",
        action="store_true",
        help="测试DebugSpider",
        function=test_debug_spider,
    )

    parser.start()
