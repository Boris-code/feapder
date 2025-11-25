# -*- coding: utf-8 -*-
"""
基于 feapder AirSpider 的 QPS 限流集成测试

测试目标：
1. 验证 QPS 限流在真实 AirSpider 中的效果
2. 对比 QPS 开启/关闭时的性能差异
3. 验证 QPS 关闭时原有流程不受影响

Author: ShellMonster
Created: 2024
"""

import time
import threading
from collections import defaultdict

import feapder
import feapder.setting as setting
from feapder import AirSpider, Request


# 使用本地 HTTP 服务模拟，避免真实网络请求
# 这里用一个简单的 mock 响应来测试


class MockResponse:
    """模拟响应对象"""
    def __init__(self, url):
        self.url = url
        self.status_code = 200
        self.text = f"Mock response for {url}"
        self.content = self.text.encode()


def test_qps_enabled_spider():
    """测试1：QPS 开启时的 AirSpider"""
    print("=" * 60)
    print("测试1: QPS 开启时的 AirSpider 集成测试")
    print("=" * 60)

    request_times = defaultdict(list)
    lock = threading.Lock()

    class QPSEnabledSpider(AirSpider):
        __custom_setting__ = {
            "DOMAIN_RATE_LIMIT_ENABLE": True,
            "DOMAIN_RATE_LIMIT_DEFAULT": 0,  # 不在规则中的域名不限制
            "DOMAIN_RATE_LIMIT_RULES": {
                "site-a.com": 3,  # 3 QPS
                "site-b.com": 5,  # 5 QPS
            },
            "DOMAIN_RATE_LIMIT_MAX_PREFETCH": 50,
            "SPIDER_THREAD_COUNT": 4,
            "LOG_LEVEL": "ERROR",  # 减少日志输出
        }

        def start_requests(self):
            # 每个域名生成10个请求
            for i in range(10):
                yield Request(f"https://site-a.com/page{i}", auto_request=False)
            for i in range(10):
                yield Request(f"https://site-b.com/page{i}", auto_request=False)

        def parse(self, request, response):
            domain = request.url.split("/")[2]
            with lock:
                request_times[domain].append(time.time())

        def download_midware(self, request):
            # Mock 下载，不发真实请求
            return MockResponse(request.url)

    spider = QPSEnabledSpider()

    # 验证调度器已初始化
    print(f"QPS调度器已初始化: {spider._qps_scheduler is not None}")

    start_time = time.time()
    spider.run()
    total_time = time.time() - start_time

    print(f"\n总耗时: {total_time:.2f}秒")
    print(f"处理请求数: {sum(len(v) for v in request_times.values())}")
    print("\n各域名实际QPS:")
    print("-" * 40)

    results = {}
    for domain in sorted(request_times.keys()):
        times = sorted(request_times[domain])
        if len(times) >= 2:
            time_span = times[-1] - times[0]
            actual_qps = (len(times) - 1) / time_span if time_span > 0 else float('inf')
            configured_qps = spider.__custom_setting__["DOMAIN_RATE_LIMIT_RULES"].get(domain, 0)
            diff = abs(actual_qps - configured_qps)
            status = "✅" if diff < 1.0 else "⚠️"
            print(f"  {status} {domain}: 配置={configured_qps} QPS, 实际={actual_qps:.2f} QPS")
            results[domain] = {"configured": configured_qps, "actual": actual_qps}

    return total_time, results


def test_qps_disabled_spider():
    """测试2：QPS 关闭时的 AirSpider（验证原有流程不受影响）"""
    print("\n" + "=" * 60)
    print("测试2: QPS 关闭时的 AirSpider（验证性能无损）")
    print("=" * 60)

    request_times = []
    lock = threading.Lock()

    class QPSDisabledSpider(AirSpider):
        __custom_setting__ = {
            "DOMAIN_RATE_LIMIT_ENABLE": False,  # 关闭 QPS
            "SPIDER_THREAD_COUNT": 4,
            "LOG_LEVEL": "ERROR",
        }

        def start_requests(self):
            # 生成20个请求
            for i in range(20):
                yield Request(f"https://test.com/page{i}", auto_request=False)

        def parse(self, request, response):
            with lock:
                request_times.append(time.time())

        def download_midware(self, request):
            return MockResponse(request.url)

    spider = QPSDisabledSpider()

    # 验证调度器未初始化
    print(f"QPS调度器未初始化: {spider._qps_scheduler is None}")

    start_time = time.time()
    spider.run()
    total_time = time.time() - start_time

    print(f"\n总耗时: {total_time:.2f}秒")
    print(f"处理请求数: {len(request_times)}")

    if len(request_times) >= 2:
        time_span = request_times[-1] - request_times[0]
        actual_qps = (len(request_times) - 1) / time_span if time_span > 0 else float('inf')
        print(f"实际吞吐量: {actual_qps:.2f} 请求/秒（无限制）")

    return total_time, len(request_times)


def test_performance_comparison():
    """测试3：性能对比（QPS 开启 vs 关闭）"""
    print("\n" + "=" * 60)
    print("测试3: 性能对比（验证 QPS 关闭时无性能损失）")
    print("=" * 60)

    # 相同请求数量，对比 QPS 开启/关闭的性能
    num_requests = 30
    request_times_enabled = []
    request_times_disabled = []
    lock = threading.Lock()

    # QPS 开启，但设置很高的限制（模拟不限制）
    class HighQPSSpider(AirSpider):
        __custom_setting__ = {
            "DOMAIN_RATE_LIMIT_ENABLE": True,
            "DOMAIN_RATE_LIMIT_DEFAULT": 1000,  # 极高的 QPS，基本不限制
            "DOMAIN_RATE_LIMIT_RULES": {},
            "SPIDER_THREAD_COUNT": 4,
            "LOG_LEVEL": "ERROR",
        }

        def start_requests(self):
            for i in range(num_requests):
                yield Request(f"https://perf-test.com/page{i}", auto_request=False)

        def parse(self, request, response):
            with lock:
                request_times_enabled.append(time.time())

        def download_midware(self, request):
            return MockResponse(request.url)

    # QPS 关闭
    class NoQPSSpider(AirSpider):
        __custom_setting__ = {
            "DOMAIN_RATE_LIMIT_ENABLE": False,
            "SPIDER_THREAD_COUNT": 4,
            "LOG_LEVEL": "ERROR",
        }

        def start_requests(self):
            for i in range(num_requests):
                yield Request(f"https://perf-test.com/page{i}", auto_request=False)

        def parse(self, request, response):
            with lock:
                request_times_disabled.append(time.time())

        def download_midware(self, request):
            return MockResponse(request.url)

    # 运行 QPS 关闭的爬虫
    print("\n运行 QPS 关闭的爬虫...")
    start1 = time.time()
    NoQPSSpider().run()
    time_disabled = time.time() - start1

    # 运行 QPS 开启（高限制）的爬虫
    print("运行 QPS 开启（高限制）的爬虫...")
    start2 = time.time()
    HighQPSSpider().run()
    time_enabled = time.time() - start2

    print(f"\n性能对比结果:")
    print(f"  QPS 关闭: {time_disabled:.3f}秒 ({len(request_times_disabled)} 请求)")
    print(f"  QPS 开启: {time_enabled:.3f}秒 ({len(request_times_enabled)} 请求)")

    # 计算性能差异
    if time_disabled > 0:
        overhead = ((time_enabled - time_disabled) / time_disabled) * 100
        print(f"  性能开销: {overhead:.1f}%")

        if overhead < 20:  # 允许20%以内的开销
            print("  ✅ 性能开销在可接受范围内")
        else:
            print("  ⚠️ 性能开销较大，需要优化")

    return time_disabled, time_enabled


def test_qps_scheduler_flow():
    """测试4：验证 QPS 调度器的完整流程"""
    print("\n" + "=" * 60)
    print("测试4: 验证 QPS 调度器完整流程")
    print("=" * 60)

    request_sequence = []
    lock = threading.Lock()

    class FlowTestSpider(AirSpider):
        __custom_setting__ = {
            "DOMAIN_RATE_LIMIT_ENABLE": True,
            "DOMAIN_RATE_LIMIT_DEFAULT": 2,  # 2 QPS
            "DOMAIN_RATE_LIMIT_RULES": {},
            "DOMAIN_RATE_LIMIT_MAX_PREFETCH": 10,
            "SPIDER_THREAD_COUNT": 2,
            "LOG_LEVEL": "ERROR",
        }

        def start_requests(self):
            for i in range(6):
                yield Request(f"https://flow-test.com/page{i}", auto_request=False)

        def parse(self, request, response):
            with lock:
                request_sequence.append({
                    "url": request.url,
                    "time": time.time()
                })

        def download_midware(self, request):
            return MockResponse(request.url)

    spider = FlowTestSpider()

    print(f"配置: 2 QPS, 6个请求, 2线程")
    print(f"预期: 第1个立即执行，后续每0.5秒执行1个")
    print(f"预期总时间: 约2.5秒（(6-1)/2 = 2.5秒）")

    start_time = time.time()
    spider.run()
    total_time = time.time() - start_time

    print(f"\n实际总耗时: {total_time:.2f}秒")
    print(f"处理请求数: {len(request_sequence)}")

    # 分析请求间隔
    if len(request_sequence) >= 2:
        request_sequence.sort(key=lambda x: x["time"])
        intervals = []
        for i in range(1, len(request_sequence)):
            interval = request_sequence[i]["time"] - request_sequence[i-1]["time"]
            intervals.append(interval)

        avg_interval = sum(intervals) / len(intervals)
        print(f"\n请求间隔分析:")
        print(f"  平均间隔: {avg_interval:.3f}秒 (期望: ~0.5秒)")

        # 验证间隔是否合理
        if 0.4 <= avg_interval <= 0.6:
            print("  ✅ 请求间隔符合预期")
        else:
            print(f"  ⚠️ 请求间隔偏离预期")

    # 打印调度器统计
    if spider._qps_scheduler:
        stats = spider._qps_scheduler.get_stats()
        print(f"\n调度器统计:")
        print(f"  提交请求数: {stats['submitted']}")
        print(f"  立即执行数: {stats['immediate']}")
        print(f"  延迟执行数: {stats['delayed']}")
        print(f"  就绪请求数: {stats['ready']}")


def test_multi_domain_real_spider():
    """测试5：多域名真实场景测试"""
    print("\n" + "=" * 60)
    print("测试5: 多域名真实场景（百度、搜狗、搜狐、腾讯）")
    print("=" * 60)

    domain_times = defaultdict(list)
    lock = threading.Lock()

    class MultiDomainSpider(AirSpider):
        __custom_setting__ = {
            "DOMAIN_RATE_LIMIT_ENABLE": True,
            "DOMAIN_RATE_LIMIT_DEFAULT": 0,
            "DOMAIN_RATE_LIMIT_RULES": {
                "www.baidu.com": 2,
                "www.sogou.com": 3,
                "www.sohu.com": 4,
                "www.qq.com": 5,
            },
            "DOMAIN_RATE_LIMIT_MAX_PREFETCH": 50,
            "SPIDER_THREAD_COUNT": 32,  # 多线程
            "LOG_LEVEL": "ERROR",
        }

        def start_requests(self):
            domains = ["www.baidu.com", "www.sogou.com", "www.sohu.com", "www.qq.com"]
            for domain in domains:
                for i in range(8):
                    yield Request(f"https://{domain}/page{i}", auto_request=False)

        def parse(self, request, response):
            domain = request.url.split("/")[2]
            with lock:
                domain_times[domain].append(time.time())

        def download_midware(self, request):
            return MockResponse(request.url)

    spider = MultiDomainSpider()
    rules = spider.__custom_setting__["DOMAIN_RATE_LIMIT_RULES"]

    print(f"配置: {rules}")
    print(f"每域名8个请求，共32个请求，8线程")

    start_time = time.time()
    spider.run()
    total_time = time.time() - start_time

    print(f"\n总耗时: {total_time:.2f}秒")
    print(f"总请求数: {sum(len(v) for v in domain_times.values())}")
    print("\n各域名QPS验证:")
    print("-" * 50)

    all_passed = True
    for domain in sorted(domain_times.keys()):
        times = sorted(domain_times[domain])
        if len(times) >= 2:
            time_span = times[-1] - times[0]
            actual_qps = (len(times) - 1) / time_span if time_span > 0 else 0
            configured_qps = rules.get(domain, 0)
            diff = abs(actual_qps - configured_qps)
            status = "✅" if diff < 0.5 else "⚠️"
            if diff >= 0.5:
                all_passed = False
            print(f"  {status} {domain}: 配置={configured_qps} QPS, 实际={actual_qps:.2f} QPS")

    if all_passed:
        print("\n✅ 所有域名 QPS 控制精确")
    else:
        print("\n⚠️ 部分域名 QPS 控制存在偏差")


if __name__ == "__main__":
    # 运行所有测试
    test_qps_enabled_spider()
    test_qps_disabled_spider()
    test_performance_comparison()
    test_qps_scheduler_flow()
    test_multi_domain_real_spider()

    print("\n" + "=" * 60)
    print("所有 feapder 集成测试完成!")
    print("=" * 60)
