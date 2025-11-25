# -*- coding: utf-8 -*-
"""
AirSpider QPS限流集成测试

测试AirSpider与QPS调度器的集成效果。

Author: ShellMonster
Created: 2024
"""

import time
import threading
import unittest

import feapder
import feapder.setting as setting
from feapder import AirSpider, Request


class QPSTestSpider(AirSpider):
    """测试用爬虫"""

    __custom_setting__ = {
        "DOMAIN_RATE_LIMIT_ENABLE": True,
        "DOMAIN_RATE_LIMIT_DEFAULT": 5,  # 5 QPS
        "DOMAIN_RATE_LIMIT_RULES": {
            "httpbin.org": 2,  # 2 QPS for httpbin
        },
        "DOMAIN_RATE_LIMIT_MAX_PREFETCH": 50,
        "SPIDER_THREAD_COUNT": 3,
    }

    def __init__(self):
        super().__init__()
        self.request_times = []
        self.request_lock = threading.Lock()

    def start_requests(self):
        # 生成10个请求
        for i in range(10):
            yield Request(f"https://httpbin.org/get?id={i}")

    def parse(self, request, response):
        with self.request_lock:
            self.request_times.append(time.time())


class TestAirSpiderQPSIntegration(unittest.TestCase):
    """AirSpider QPS集成测试"""

    def test_qps_scheduler_initialization(self):
        """测试QPS调度器是否正确初始化"""
        spider = QPSTestSpider()
        self.assertIsNotNone(spider._qps_scheduler)
        self.assertEqual(spider._qps_scheduler.max_prefetch, 50)

    def test_qps_disabled(self):
        """测试QPS禁用时调度器不初始化"""
        class NoQPSSpider(AirSpider):
            __custom_setting__ = {
                "DOMAIN_RATE_LIMIT_ENABLE": False,
            }

            def start_requests(self):
                yield Request("https://example.com")

            def parse(self, request, response):
                pass

        spider = NoQPSSpider()
        self.assertIsNone(spider._qps_scheduler)


class TestQPSConfigInheriting(unittest.TestCase):
    """测试QPS配置继承"""

    def test_custom_setting_override(self):
        """测试__custom_setting__覆盖全局配置"""
        # 保存原始设置
        original_enable = setting.DOMAIN_RATE_LIMIT_ENABLE

        # 测试自定义设置
        class CustomSpider(AirSpider):
            __custom_setting__ = {
                "DOMAIN_RATE_LIMIT_ENABLE": True,
                "DOMAIN_RATE_LIMIT_DEFAULT": 100,
            }

            def start_requests(self):
                yield Request("https://example.com")

            def parse(self, request, response):
                pass

        spider = CustomSpider()
        # 验证爬虫级别设置生效
        self.assertTrue(setting.DOMAIN_RATE_LIMIT_ENABLE)
        self.assertEqual(setting.DOMAIN_RATE_LIMIT_DEFAULT, 100)

        # 恢复原始设置
        setting.DOMAIN_RATE_LIMIT_ENABLE = original_enable


if __name__ == '__main__':
    unittest.main()
