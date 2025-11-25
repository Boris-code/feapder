# -*- coding: utf-8 -*-
"""
模拟真实场景的性能对比测试

模拟网络延迟，对比 QPS 开启/关闭时的性能差异

Author: ShellMonster
Created: 2024
"""

import time
import threading
import random

import feapder.setting as setting
from feapder import AirSpider, Request


class MockResponse:
    """模拟响应对象"""
    def __init__(self, url):
        self.url = url
        self.status_code = 200
        self.text = f"Mock response for {url}"
        self.content = self.text.encode()


def run_realistic_test():
    """模拟真实场景的性能测试"""
    print("=" * 70)
    print("真实场景性能测试：模拟网络延迟 50-100ms")
    print("=" * 70)

    num_requests = 100
    num_threads = 32
    network_delay = (0.05, 0.1)  # 模拟 50-100ms 网络延迟

    # ==================== 测试1：QPS 关闭 ====================
    print(f"\n[测试1] QPS 关闭，{num_requests}个请求，{num_threads}线程")

    times_disabled = []
    lock1 = threading.Lock()

    class DisabledSpider(AirSpider):
        __custom_setting__ = {
            "DOMAIN_RATE_LIMIT_ENABLE": False,
            "SPIDER_THREAD_COUNT": num_threads,
            "LOG_LEVEL": "ERROR",
        }

        def start_requests(self):
            for i in range(num_requests):
                yield Request(f"https://test.com/page{i}", auto_request=False)

        def parse(self, request, response):
            with lock1:
                times_disabled.append(time.time())

        def download_midware(self, request):
            # 模拟网络延迟
            time.sleep(random.uniform(*network_delay))
            return MockResponse(request.url)

    start1 = time.time()
    DisabledSpider().run()
    duration1 = time.time() - start1

    if len(times_disabled) >= 2:
        work_time1 = times_disabled[-1] - times_disabled[0]
    else:
        work_time1 = 0

    print(f"  总耗时: {duration1:.3f}秒")
    print(f"  处理请求: {len(times_disabled)}")

    # ==================== 测试2：QPS 开启（极高限制） ====================
    print(f"\n[测试2] QPS 开启（default_qps=10000），{num_requests}个请求，{num_threads}线程")

    times_enabled = []
    lock2 = threading.Lock()

    class EnabledSpider(AirSpider):
        __custom_setting__ = {
            "DOMAIN_RATE_LIMIT_ENABLE": True,
            "DOMAIN_RATE_LIMIT_DEFAULT": 10000,
            "DOMAIN_RATE_LIMIT_RULES": {},
            "DOMAIN_RATE_LIMIT_MAX_PREFETCH": 100,
            "SPIDER_THREAD_COUNT": num_threads,
            "LOG_LEVEL": "ERROR",
        }

        def start_requests(self):
            for i in range(num_requests):
                yield Request(f"https://test.com/page{i}", auto_request=False)

        def parse(self, request, response):
            with lock2:
                times_enabled.append(time.time())

        def download_midware(self, request):
            # 模拟网络延迟
            time.sleep(random.uniform(*network_delay))
            return MockResponse(request.url)

    start2 = time.time()
    EnabledSpider().run()
    duration2 = time.time() - start2

    if len(times_enabled) >= 2:
        work_time2 = times_enabled[-1] - times_enabled[0]
    else:
        work_time2 = 0

    print(f"  总耗时: {duration2:.3f}秒")
    print(f"  处理请求: {len(times_enabled)}")

    # ==================== 结果对比 ====================
    print("\n" + "=" * 70)
    print("性能对比结果（真实场景，有网络延迟）")
    print("=" * 70)

    print(f"\n{'指标':<20} {'QPS关闭':<15} {'QPS开启':<15} {'差异':<15}")
    print("-" * 70)
    print(f"{'总耗时':<20} {duration1:.3f}秒{'':<8} {duration2:.3f}秒{'':<8} {(duration2-duration1):.3f}秒")

    if duration1 > 0:
        overhead_pct = ((duration2 - duration1) / duration1) * 100
        print(f"\n总耗时开销: {overhead_pct:.1f}%")

        if abs(overhead_pct) < 5:
            print("✅ QPS 架构对真实场景性能几乎无影响（<5%）")
        elif abs(overhead_pct) < 15:
            print("✅ QPS 架构对真实场景性能影响可接受（5-15%）")
        else:
            print(f"⚠️ QPS 架构对真实场景性能有影响（{overhead_pct:.1f}%）")


def run_qps_accuracy_with_delay():
    """带网络延迟的 QPS 精度测试"""
    print("\n" + "=" * 70)
    print("QPS 精度测试：模拟真实网络延迟场景")
    print("=" * 70)

    request_times = []
    lock = threading.Lock()

    class QPSTestSpider(AirSpider):
        __custom_setting__ = {
            "DOMAIN_RATE_LIMIT_ENABLE": True,
            "DOMAIN_RATE_LIMIT_DEFAULT": 5,  # 5 QPS
            "DOMAIN_RATE_LIMIT_RULES": {},
            "DOMAIN_RATE_LIMIT_MAX_PREFETCH": 50,
            "SPIDER_THREAD_COUNT": 8,
            "LOG_LEVEL": "ERROR",
        }

        def start_requests(self):
            for i in range(20):
                yield Request(f"https://test.com/page{i}", auto_request=False)

        def parse(self, request, response):
            with lock:
                request_times.append(time.time())

        def download_midware(self, request):
            # 模拟 100ms 网络延迟
            time.sleep(0.1)
            return MockResponse(request.url)

    print(f"配置: 5 QPS, 20个请求, 8线程, 每请求100ms延迟")
    print(f"预期: 网络延迟不影响 QPS 控制精度")

    start = time.time()
    QPSTestSpider().run()
    duration = time.time() - start

    print(f"\n总耗时: {duration:.2f}秒")
    print(f"处理请求: {len(request_times)}")

    if len(request_times) >= 2:
        request_times.sort()
        time_span = request_times[-1] - request_times[0]
        actual_qps = (len(request_times) - 1) / time_span if time_span > 0 else 0

        print(f"配置QPS: 5")
        print(f"实际QPS: {actual_qps:.2f}")

        if 4.5 <= actual_qps <= 5.5:
            print("✅ QPS 控制精确")
        else:
            print("⚠️ QPS 控制有偏差")


if __name__ == "__main__":
    run_realistic_test()
    run_qps_accuracy_with_delay()

    print("\n" + "=" * 70)
    print("真实场景测试完成!")
    print("=" * 70)
