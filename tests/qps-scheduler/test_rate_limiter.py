# -*- coding: utf-8 -*-
"""
域名级QPS限流模块单元测试

测试 LocalTokenBucket、DomainRateLimiter 的功能正确性。

Author: ShellMonster
Created: 2024
"""

import time
import threading
import unittest

from feapder.utils.rate_limiter import (
    LocalTokenBucket,
    DomainRateLimiter,
)


class TestLocalTokenBucket(unittest.TestCase):
    """本地令牌桶测试"""

    def test_init_with_valid_qps(self):
        """测试正常初始化"""
        bucket = LocalTokenBucket(qps=10)
        self.assertEqual(bucket.qps, 10)
        self.assertEqual(bucket.capacity, 10)
        # 初始令牌为1（避免突发）
        self.assertEqual(bucket.tokens, 1.0)

    def test_init_with_invalid_qps(self):
        """测试无效QPS值"""
        with self.assertRaises(ValueError):
            LocalTokenBucket(qps=0)
        with self.assertRaises(ValueError):
            LocalTokenBucket(qps=-1)

    def test_acquire_immediate(self):
        """测试立即获取令牌"""
        bucket = LocalTokenBucket(qps=10)
        # 初始有1个令牌，第1次应该立即返回
        wait_time = bucket.acquire()
        self.assertEqual(wait_time, 0)
        # 第2次应该需要等待
        wait_time = bucket.acquire()
        self.assertGreater(wait_time, 0)

    def test_acquire_with_wait(self):
        """测试需要等待的情况"""
        bucket = LocalTokenBucket(qps=2)  # 每秒2个令牌
        # 消耗初始令牌
        bucket.acquire()
        # 第2次应该需要等待约0.5秒（1/2 QPS）
        wait_time = bucket.acquire()
        self.assertGreater(wait_time, 0)
        self.assertLessEqual(wait_time, 0.6)  # 约0.5秒

    def test_token_replenish(self):
        """测试令牌补充"""
        bucket = LocalTokenBucket(qps=10)
        # 消耗初始令牌并预扣一个
        bucket.acquire()  # 消耗初始的1个令牌
        bucket.acquire()  # 预扣，返回等待时间

        # 等待一段时间让令牌补充
        time.sleep(0.2)  # 0.2秒应该补充2个令牌

        # 应该能立即获取
        wait_time = bucket.acquire()
        self.assertEqual(wait_time, 0)

    def test_thread_safety(self):
        """测试线程安全性"""
        bucket = LocalTokenBucket(qps=100)
        results = []

        def acquire_tokens():
            for _ in range(10):
                wait_time = bucket.acquire()
                results.append(wait_time)

        threads = [threading.Thread(target=acquire_tokens) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该有50个结果
        self.assertEqual(len(results), 50)


class TestDomainRateLimiter(unittest.TestCase):
    """域名级限流器测试"""

    def test_exact_domain_match(self):
        """测试精确域名匹配"""
        limiter = DomainRateLimiter(
            rules={"www.baidu.com": 5, "www.google.com": 10},
            default_qps=20
        )
        self.assertEqual(limiter.get_qps_limit("www.baidu.com"), 5)
        self.assertEqual(limiter.get_qps_limit("www.google.com"), 10)

    def test_wildcard_match(self):
        """测试通配符匹配"""
        limiter = DomainRateLimiter(
            rules={"*.taobao.com": 3},
            default_qps=10
        )
        self.assertEqual(limiter.get_qps_limit("item.taobao.com"), 3)
        self.assertEqual(limiter.get_qps_limit("detail.taobao.com"), 3)
        self.assertEqual(limiter.get_qps_limit("taobao.com"), 3)  # 主域名也匹配

    def test_default_qps(self):
        """测试默认QPS"""
        limiter = DomainRateLimiter(
            rules={"www.baidu.com": 5},
            default_qps=20
        )
        self.assertEqual(limiter.get_qps_limit("www.unknown.com"), 20)

    def test_zero_default_qps_no_limit(self):
        """测试默认QPS为0时不限制"""
        limiter = DomainRateLimiter(
            rules={"www.baidu.com": 5},
            default_qps=0
        )
        # 未匹配的域名应该返回0（不限制）
        wait_time = limiter.acquire("www.unknown.com")
        self.assertEqual(wait_time, 0)

    def test_acquire_with_limit(self):
        """测试获取令牌"""
        limiter = DomainRateLimiter(
            rules={"www.test.com": 2},
            default_qps=0
        )
        # 第1次应该立即返回（初始有1个令牌）
        self.assertEqual(limiter.acquire("www.test.com"), 0)
        # 第2次应该需要等待
        wait_time = limiter.acquire("www.test.com")
        self.assertGreater(wait_time, 0)

    def test_extract_domain(self):
        """测试URL域名提取"""
        self.assertEqual(
            DomainRateLimiter.extract_domain("https://www.baidu.com/path"),
            "www.baidu.com"
        )
        self.assertEqual(
            DomainRateLimiter.extract_domain("http://example.com:8080/api"),
            "example.com"
        )
        self.assertEqual(
            DomainRateLimiter.extract_domain(""),
            ""
        )
        self.assertEqual(
            DomainRateLimiter.extract_domain(None),
            ""
        )

    def test_empty_domain(self):
        """测试空域名"""
        limiter = DomainRateLimiter(default_qps=10)
        self.assertEqual(limiter.get_qps_limit(""), 10)
        self.assertEqual(limiter.get_qps_limit(None), 10)


class TestDomainRateLimiterQPSAccuracy(unittest.TestCase):
    """QPS精度测试"""

    def test_qps_accuracy(self):
        """测试QPS控制精度 - 验证预扣机制正确排队"""
        limiter = DomainRateLimiter(
            rules={"test.com": 10},  # 10 QPS
            default_qps=0
        )

        # 模拟获取多个令牌
        wait_times = []
        for i in range(5):
            wait_time = limiter.acquire("test.com")
            wait_times.append(wait_time)

        # 第1个应该立即返回（初始有1个令牌）
        self.assertEqual(wait_times[0], 0)
        # 后续应该需要等待，且等待时间递增（排队效果）
        for i in range(1, len(wait_times)):
            self.assertGreater(wait_times[i], 0)
            if i > 1:
                # 由于预扣机制，后续请求的等待时间应该比前一个多约0.1秒
                self.assertGreater(wait_times[i], wait_times[i-1] - 0.01)

    def test_strict_qps_mode(self):
        """测试严格QPS模式 - 验证等待时间按1/QPS递增"""
        limiter = DomainRateLimiter(
            rules={"strict.com": 5},  # 5 QPS = 每0.2秒1个请求
            default_qps=0
        )

        # 消耗初始令牌
        wait_time0 = limiter.acquire("strict.com")
        self.assertEqual(wait_time0, 0)  # 第1个立即返回

        # 后续获取应该返回递增的等待时间
        wait_time1 = limiter.acquire("strict.com")
        self.assertAlmostEqual(wait_time1, 0.2, delta=0.05,
            msg=f"First wait time: expected ~0.2, got {wait_time1}")

        # 连续获取，由于预扣机制，等待时间应该继续递增
        wait_time2 = limiter.acquire("strict.com")
        self.assertAlmostEqual(wait_time2, 0.4, delta=0.05,
            msg=f"Second wait time: expected ~0.4, got {wait_time2}")


if __name__ == '__main__':
    unittest.main()
