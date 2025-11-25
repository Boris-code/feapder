# -*- coding: utf-8 -*-
"""
QPS 开启/关闭 性能对比测试

专门测试 QPS 关闭时是否有性能损失

Author: ShellMonster
Created: 2024
"""

import time
import threading

import feapder.setting as setting
from feapder import AirSpider, Request


class MockResponse:
    """模拟响应对象"""
    def __init__(self, url):
        self.url = url
        self.status_code = 200
        self.text = f"Mock response for {url}"
        self.content = self.text.encode()


def run_performance_test():
    """性能对比测试"""
    print("=" * 70)
    print("性能对比测试：QPS 关闭 vs QPS 开启（高限制）")
    print("=" * 70)

    num_requests = 200  # 更多请求以减少启动/退出开销的影响
    num_threads = 32

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
            return MockResponse(request.url)

    spider1 = DisabledSpider()
    print(f"  _qps_scheduler: {spider1._qps_scheduler}")

    start1 = time.time()
    spider1.run()
    duration1 = time.time() - start1

    if len(times_disabled) >= 2:
        work_time1 = times_disabled[-1] - times_disabled[0]
        throughput1 = (len(times_disabled) - 1) / work_time1 if work_time1 > 0 else 0
    else:
        work_time1 = 0
        throughput1 = 0

    print(f"  总耗时: {duration1:.3f}秒")
    print(f"  实际工作时间: {work_time1:.3f}秒")
    print(f"  处理请求: {len(times_disabled)}")
    print(f"  吞吐量: {throughput1:.1f} 请求/秒")

    # ==================== 测试2：QPS 开启（极高限制，相当于不限制） ====================
    print(f"\n[测试2] QPS 开启（default_qps=10000），{num_requests}个请求，{num_threads}线程")

    times_enabled = []
    lock2 = threading.Lock()

    class EnabledHighSpider(AirSpider):
        __custom_setting__ = {
            "DOMAIN_RATE_LIMIT_ENABLE": True,
            "DOMAIN_RATE_LIMIT_DEFAULT": 10000,  # 极高限制
            "DOMAIN_RATE_LIMIT_RULES": {},
            "DOMAIN_RATE_LIMIT_MAX_PREFETCH": 200,
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
            return MockResponse(request.url)

    spider2 = EnabledHighSpider()
    print(f"  _qps_scheduler: {spider2._qps_scheduler}")

    start2 = time.time()
    spider2.run()
    duration2 = time.time() - start2

    if len(times_enabled) >= 2:
        work_time2 = times_enabled[-1] - times_enabled[0]
        throughput2 = (len(times_enabled) - 1) / work_time2 if work_time2 > 0 else 0
    else:
        work_time2 = 0
        throughput2 = 0

    print(f"  总耗时: {duration2:.3f}秒")
    print(f"  实际工作时间: {work_time2:.3f}秒")
    print(f"  处理请求: {len(times_enabled)}")
    print(f"  吞吐量: {throughput2:.1f} 请求/秒")

    # ==================== 结果对比 ====================
    print("\n" + "=" * 70)
    print("性能对比结果")
    print("=" * 70)

    print(f"\n{'指标':<20} {'QPS关闭':<15} {'QPS开启':<15} {'差异':<15}")
    print("-" * 70)
    print(f"{'总耗时':<20} {duration1:.3f}秒{'':<8} {duration2:.3f}秒{'':<8} {(duration2-duration1):.3f}秒")
    print(f"{'实际工作时间':<16} {work_time1:.3f}秒{'':<8} {work_time2:.3f}秒{'':<8} {(work_time2-work_time1):.3f}秒")
    print(f"{'吞吐量':<20} {throughput1:.1f}/秒{'':<7} {throughput2:.1f}/秒{'':<7}")

    # 关键指标：实际工作时间的差异
    if work_time1 > 0:
        overhead_pct = ((work_time2 - work_time1) / work_time1) * 100
        print(f"\n实际工作时间开销: {overhead_pct:.1f}%")

        if abs(overhead_pct) < 15:
            print("✅ QPS 架构对性能影响可忽略（<15%）")
        elif abs(overhead_pct) < 30:
            print("⚠️ QPS 架构有轻微性能影响（15-30%）")
        else:
            print("❌ QPS 架构性能影响较大（>30%）")

    # 总耗时差异（包含启动/退出开销）
    if duration1 > 0:
        total_overhead_pct = ((duration2 - duration1) / duration1) * 100
        print(f"总耗时开销: {total_overhead_pct:.1f}%（包含启动/退出开销）")


if __name__ == "__main__":
    run_performance_test()
