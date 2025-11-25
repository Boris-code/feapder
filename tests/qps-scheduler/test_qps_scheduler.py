# -*- coding: utf-8 -*-
"""
QPS调度器单元测试

测试 QPSScheduler 的功能正确性。

Author: ShellMonster
Created: 2024
"""

import time
import threading
import unittest
from unittest.mock import MagicMock

from feapder.utils.rate_limiter import DomainRateLimiter
from feapder.core.schedulers.qps_scheduler import QPSScheduler, DelayedRequest


class MockRequest:
    """模拟请求对象"""
    def __init__(self, url):
        self.url = url


class TestDelayedRequest(unittest.TestCase):
    """延迟请求包装类测试"""

    def test_ordering(self):
        """测试按时间排序"""
        req1 = DelayedRequest(1.0, "request1", "domain1")
        req2 = DelayedRequest(2.0, "request2", "domain2")
        req3 = DelayedRequest(0.5, "request3", "domain3")

        # 按scheduled_time排序
        sorted_reqs = sorted([req1, req2, req3])
        self.assertEqual(sorted_reqs[0].scheduled_time, 0.5)
        self.assertEqual(sorted_reqs[1].scheduled_time, 1.0)
        self.assertEqual(sorted_reqs[2].scheduled_time, 2.0)


class TestQPSScheduler(unittest.TestCase):
    """QPS调度器测试"""

    def setUp(self):
        """测试前准备"""
        self.rate_limiter = DomainRateLimiter(
            rules={"test.com": 5},  # 5 QPS
            default_qps=10
        )

    def tearDown(self):
        """测试后清理"""
        pass

    def test_init(self):
        """测试初始化"""
        scheduler = QPSScheduler(self.rate_limiter, max_prefetch=50)
        self.assertEqual(scheduler.max_prefetch, 50)
        self.assertFalse(scheduler._running)

    def test_start_stop(self):
        """测试启动和停止"""
        scheduler = QPSScheduler(self.rate_limiter)
        scheduler.start()
        self.assertTrue(scheduler._running)
        time.sleep(0.1)  # 让调度线程启动

        scheduler.stop()
        self.assertFalse(scheduler._running)

    def test_submit_immediate(self):
        """测试立即可执行的请求提交"""
        scheduler = QPSScheduler(self.rate_limiter)
        scheduler.start()

        # 提交一个请求
        request = MockRequest("https://test.com/page1")
        result = scheduler.submit(request)
        self.assertTrue(result)

        # 等待调度器处理
        time.sleep(0.1)

        # 应该能立即从就绪队列获取
        ready = scheduler.get_ready_request_nowait()
        self.assertIsNotNone(ready)
        self.assertEqual(ready.url, "https://test.com/page1")

        scheduler.stop()

    def test_submit_delayed(self):
        """测试需要延迟的请求"""
        # 使用低QPS
        rate_limiter = DomainRateLimiter(
            rules={"delay.com": 2},  # 2 QPS
            default_qps=0
        )
        scheduler = QPSScheduler(rate_limiter)
        scheduler.start()

        # 提交多个请求超过QPS限制
        for i in range(4):
            request = MockRequest(f"https://delay.com/page{i}")
            scheduler.submit(request)

        # 等待调度器处理
        time.sleep(0.1)

        # 初始只有1个令牌，只有1个应该立即可用
        ready1 = scheduler.get_ready_request_nowait()
        self.assertIsNotNone(ready1)

        # 第2个应该还在延迟堆中
        ready2 = scheduler.get_ready_request_nowait()
        self.assertIsNone(ready2)

        # 等待令牌恢复后应该能获取更多
        time.sleep(0.6)  # 等待超过0.5秒（2 QPS = 每0.5秒1个）
        ready2 = scheduler.get_ready_request_nowait()
        self.assertIsNotNone(ready2)

        scheduler.stop()

    def test_max_prefetch_backpressure(self):
        """测试max_prefetch背压机制"""
        rate_limiter = DomainRateLimiter(
            rules={"bp.com": 1},  # 1 QPS
            default_qps=0
        )
        scheduler = QPSScheduler(rate_limiter, max_prefetch=3)
        scheduler.start()

        # 提交3个请求应该成功
        for i in range(3):
            request = MockRequest(f"https://bp.com/page{i}")
            result = scheduler.submit(request, block=False)
            self.assertTrue(result)

        # 等待调度器处理
        time.sleep(0.1)

        # 第4个请求应该被阻塞（非阻塞模式下返回False）
        request4 = MockRequest("https://bp.com/page4")
        result = scheduler.submit(request4, block=False)
        self.assertFalse(result)

        # 消费一个请求后应该能提交
        scheduler.get_ready_request(timeout=0.1)
        result = scheduler.submit(request4, block=False)
        self.assertTrue(result)

        scheduler.stop()

    def test_is_empty(self):
        """测试空检测"""
        scheduler = QPSScheduler(self.rate_limiter)
        scheduler.start()

        # 初始为空
        self.assertTrue(scheduler.is_empty())

        # 提交请求后不为空
        scheduler.submit(MockRequest("https://test.com/page"))
        time.sleep(0.1)
        self.assertFalse(scheduler.is_empty())

        # 消费后为空
        scheduler.get_ready_request(timeout=0.5)
        time.sleep(0.1)
        self.assertTrue(scheduler.is_empty())

        scheduler.stop()

    def test_stats(self):
        """测试统计信息"""
        scheduler = QPSScheduler(self.rate_limiter)
        scheduler.start()

        # 提交几个请求
        for i in range(3):
            scheduler.submit(MockRequest(f"https://test.com/page{i}"))

        time.sleep(0.1)

        stats = scheduler.get_stats()
        self.assertEqual(stats['submitted'], 3)
        self.assertGreaterEqual(stats['immediate'] + stats['delayed'], 3)

        scheduler.stop()

    def test_multiple_domains(self):
        """测试多域名支持"""
        rate_limiter = DomainRateLimiter(
            rules={
                "domain1.com": 2,
                "domain2.com": 3
            },
            default_qps=5
        )
        scheduler = QPSScheduler(rate_limiter)
        scheduler.start()

        # 提交不同域名的请求
        requests = [
            MockRequest("https://domain1.com/1"),
            MockRequest("https://domain1.com/2"),
            MockRequest("https://domain2.com/1"),
            MockRequest("https://domain2.com/2"),
            MockRequest("https://domain2.com/3"),
        ]

        for req in requests:
            scheduler.submit(req)

        time.sleep(0.2)

        # 每个域名初始有1个令牌，所以立即可用的是2个（domain1.com和domain2.com各1个）
        ready_count = 0
        while True:
            ready = scheduler.get_ready_request_nowait()
            if ready is None:
                break
            ready_count += 1

        self.assertEqual(ready_count, 2)

        # 等待更长时间让所有请求就绪
        time.sleep(1.5)
        while True:
            ready = scheduler.get_ready_request_nowait()
            if ready is None:
                break
            ready_count += 1

        # 所有5个请求都应该被处理了
        self.assertEqual(ready_count, 5)

        scheduler.stop()


class TestQPSSchedulerConcurrency(unittest.TestCase):
    """并发测试"""

    def test_concurrent_submit(self):
        """测试并发提交"""
        rate_limiter = DomainRateLimiter(
            rules={"concurrent.com": 100},
            default_qps=0
        )
        scheduler = QPSScheduler(rate_limiter)
        scheduler.start()

        submit_count = [0]
        lock = threading.Lock()

        def submit_requests():
            for i in range(20):
                request = MockRequest(f"https://concurrent.com/{threading.current_thread().name}/{i}")
                if scheduler.submit(request):
                    with lock:
                        submit_count[0] += 1

        threads = [threading.Thread(target=submit_requests) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 等待处理完成
        time.sleep(0.5)

        self.assertEqual(submit_count[0], 100)

        scheduler.stop()

    def test_concurrent_consume(self):
        """测试并发消费"""
        rate_limiter = DomainRateLimiter(
            rules={"consume.com": 100},
            default_qps=0
        )
        scheduler = QPSScheduler(rate_limiter)
        scheduler.start()

        # 先提交100个请求
        for i in range(100):
            scheduler.submit(MockRequest(f"https://consume.com/page{i}"))

        time.sleep(0.2)

        consumed = []
        lock = threading.Lock()

        def consume_requests():
            for _ in range(25):
                request = scheduler.get_ready_request(timeout=1.0)
                if request:
                    with lock:
                        consumed.append(request)

        threads = [threading.Thread(target=consume_requests) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(consumed), 100)

        scheduler.stop()


if __name__ == '__main__':
    unittest.main()
