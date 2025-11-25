# -*- coding: utf-8 -*-
"""
混合QPS限制对比测试

测试①：QPS开启，部分域名限制、部分域名不限制
测试②：QPS关闭，测试不限制的域名

对比：
- ①中限制域名的QPS是否被精确控制
- ①中不限制域名 vs ②中同域名的性能差异

Author: ShellMonster
Created: 2024
"""

import time
import threading
from collections import defaultdict

from feapder.core.schedulers import QPSScheduler
from feapder.utils.rate_limiter import DomainRateLimiter
from feapder.network.request import Request


# 模拟处理时间（毫秒）
PROCESS_TIME_MS = 10


def run_mixed_qps_test():
    """
    测试①：QPS开启，混合限制
    - baidu.com: 限制 2 QPS
    - sogou.com: 不限制（default_qps=0）
    """
    print("=" * 70)
    print("测试①：QPS开启，混合限制（baidu=2QPS，sogou=不限制）")
    print("=" * 70)

    num_requests_per_domain = 20
    num_threads = 32

    # 创建限流器和调度器
    rate_limiter = DomainRateLimiter(
        rules={"www.baidu.com": 2},  # baidu 限制 2 QPS
        default_qps=0,  # 默认不限制
    )
    scheduler = QPSScheduler(rate_limiter=rate_limiter, max_prefetch=100)
    scheduler.start()

    # 记录每个域名的请求获取时间（从就绪队列获取的时间）
    request_times = defaultdict(list)
    lock = threading.Lock()
    completed = {"count": 0}

    def consumer():
        """消费者线程：从调度器获取请求"""
        while True:
            request = scheduler.get_ready_request(timeout=0.5)
            if request:
                domain = "baidu" if "baidu" in request.url else "sogou"
                with lock:
                    request_times[domain].append(time.time())
                    completed["count"] += 1
                # 模拟处理时间
                time.sleep(PROCESS_TIME_MS / 1000)
            elif completed["count"] >= num_requests_per_domain * 2:
                break

    # 提交所有请求
    print(f"配置: {num_threads}线程, 每域名{num_requests_per_domain}请求")
    print(f"  - www.baidu.com: 限制 2 QPS")
    print(f"  - www.sogou.com: 不限制 (default=0)")
    print(f"  - 模拟处理时间: {PROCESS_TIME_MS}ms")

    start = time.time()

    # 交替提交两个域名的请求
    for i in range(num_requests_per_domain):
        scheduler.submit(Request(f"https://www.baidu.com/page{i}"))
        scheduler.submit(Request(f"https://www.sogou.com/page{i}"))

    # 启动消费者线程
    consumers = []
    for _ in range(num_threads):
        t = threading.Thread(target=consumer)
        t.start()
        consumers.append(t)

    # 等待所有消费者完成
    for t in consumers:
        t.join(timeout=30)

    duration = time.time() - start
    scheduler.stop()

    print(f"\n总耗时: {duration:.2f}秒")
    print(f"调度器统计: {scheduler.get_stats()}")

    results = {}
    for domain in ["baidu", "sogou"]:
        times = sorted(request_times[domain])
        count = len(times)
        if count >= 2:
            time_span = times[-1] - times[0]
            actual_qps = (count - 1) / time_span if time_span > 0 else float('inf')
        else:
            time_span = 0
            actual_qps = 0

        results[domain] = {
            "count": count,
            "time_span": time_span,
            "actual_qps": actual_qps,
        }

        print(f"\n{domain}.com:")
        print(f"  处理请求: {count}")
        print(f"  时间跨度: {time_span:.3f}秒")
        print(f"  实际QPS: {actual_qps:.2f}")

    # 验证 baidu QPS 是否被控制
    baidu_qps = results["baidu"]["actual_qps"]
    if 1.8 <= baidu_qps <= 2.2:
        print(f"\n✅ baidu.com QPS控制精确 (配置2, 实际{baidu_qps:.2f})")
    else:
        print(f"\n⚠️ baidu.com QPS控制有偏差 (配置2, 实际{baidu_qps:.2f})")

    return results


def run_qps_disabled_test(target_domain="sogou"):
    """
    测试②：QPS关闭，直接从队列获取（模拟原始流程）
    """
    print("\n" + "=" * 70)
    print(f"测试②：QPS关闭，测试 {target_domain}.com（与测试①中不限制域名对比）")
    print("=" * 70)

    from queue import Queue

    num_requests = 20
    num_threads = 32

    # 使用普通队列模拟QPS关闭时的行为
    request_queue = Queue()
    request_times = []
    lock = threading.Lock()
    completed = {"count": 0}

    def consumer():
        """消费者线程"""
        while True:
            try:
                request = request_queue.get(timeout=0.5)
                with lock:
                    request_times.append(time.time())
                    completed["count"] += 1
                # 模拟处理时间
                time.sleep(PROCESS_TIME_MS / 1000)
            except:
                if completed["count"] >= num_requests:
                    break

    print(f"配置: {num_threads}线程, {num_requests}请求, QPS关闭")
    print(f"  - 模拟处理时间: {PROCESS_TIME_MS}ms")

    start = time.time()

    # 提交所有请求
    for i in range(num_requests):
        request_queue.put(Request(f"https://www.{target_domain}.com/page{i}"))

    # 启动消费者线程
    consumers = []
    for _ in range(num_threads):
        t = threading.Thread(target=consumer)
        t.start()
        consumers.append(t)

    # 等待所有消费者完成
    for t in consumers:
        t.join(timeout=30)

    duration = time.time() - start

    request_times.sort()
    count = len(request_times)
    if count >= 2:
        time_span = request_times[-1] - request_times[0]
        actual_qps = (count - 1) / time_span if time_span > 0 else float('inf')
    else:
        time_span = 0
        actual_qps = 0

    print(f"\n总耗时: {duration:.2f}秒")
    print(f"处理请求: {count}")
    print(f"时间跨度: {time_span:.3f}秒")
    print(f"实际QPS: {actual_qps:.2f}")

    return {
        "count": count,
        "time_span": time_span,
        "actual_qps": actual_qps,
        "duration": duration,
    }


def run_comparison():
    """运行完整对比测试"""
    print("\n" + "=" * 70)
    print("域名级QPS混合限制对比测试")
    print("=" * 70)

    # 测试①：QPS开启，混合限制
    results_mixed = run_mixed_qps_test()

    # 测试②：QPS关闭
    results_disabled = run_qps_disabled_test("sogou")

    # 对比分析
    print("\n" + "=" * 70)
    print("对比分析结果")
    print("=" * 70)

    print("\n【1】QPS限制精度验证（baidu.com, 配置2QPS）")
    print("-" * 50)
    baidu_qps = results_mixed["baidu"]["actual_qps"]
    print(f"  配置QPS: 2")
    print(f"  实际QPS: {baidu_qps:.2f}")
    qps_error = abs(baidu_qps - 2) / 2 * 100 if baidu_qps != float('inf') else 100
    print(f"  误差: {qps_error:.1f}%")
    if qps_error < 10:
        print(f"  ✅ QPS限制精确控制")
    else:
        print(f"  ⚠️ QPS限制有偏差")

    print("\n【2】不限制域名性能对比（sogou.com）")
    print("-" * 50)
    sogou_qps_enabled = results_mixed["sogou"]["actual_qps"]
    sogou_qps_disabled = results_disabled["actual_qps"]
    sogou_time_enabled = results_mixed["sogou"]["time_span"]
    sogou_time_disabled = results_disabled["time_span"]

    print(f"  QPS开启(不限制域名):")
    print(f"      时间跨度: {sogou_time_enabled:.3f}秒")
    print(f"      实际QPS: {sogou_qps_enabled:.2f}")
    print(f"  QPS关闭:")
    print(f"      时间跨度: {sogou_time_disabled:.3f}秒")
    print(f"      实际QPS: {sogou_qps_disabled:.2f}")

    # 用时间跨度来对比性能更准确
    if sogou_time_disabled > 0 and sogou_time_enabled > 0:
        # 时间跨度差异
        time_diff_pct = ((sogou_time_enabled - sogou_time_disabled) / sogou_time_disabled) * 100
        print(f"\n  时间跨度差异: {time_diff_pct:.1f}% {'(QPS架构更慢)' if time_diff_pct > 0 else '(QPS架构更快)'}")

        if abs(time_diff_pct) < 10:
            print(f"  ✅ QPS架构对不限制域名性能影响很小（<10%）")
        elif abs(time_diff_pct) < 20:
            print(f"  ⚠️ QPS架构对不限制域名有一定性能影响（10-20%）")
        else:
            print(f"  ❌ QPS架构对不限制域名性能影响较大（>{abs(time_diff_pct):.0f}%）")
    elif sogou_time_enabled == 0 and sogou_time_disabled == 0:
        print(f"\n  ✅ 两种模式时间跨度都接近0，说明请求几乎瞬间被处理（不限制情况下）")

    print("\n【3】总结")
    print("-" * 50)
    print(f"  • 有限制域名(baidu):")
    print(f"      - 配置QPS: 2")
    print(f"      - 实际QPS: {baidu_qps:.2f}")
    print(f"      - 时间跨度: {results_mixed['baidu']['time_span']:.2f}秒")
    print(f"  • 无限制域名(sogou): ")
    print(f"      - QPS开启: 时间跨度 {sogou_time_enabled:.3f}秒")
    print(f"      - QPS关闭: 时间跨度 {sogou_time_disabled:.3f}秒")

    # 额外验证：baidu的时间跨度应该约为 (20-1)/2 = 9.5秒
    if results_mixed["baidu"]["count"] > 1:
        expected_baidu_time = (results_mixed["baidu"]["count"] - 1) / 2
        actual_baidu_time = results_mixed["baidu"]["time_span"]
        print(f"\n  • baidu时间跨度验证:")
        print(f"      - 预期: {expected_baidu_time:.1f}秒 ({results_mixed['baidu']['count']-1}请求 / 2QPS)")
        print(f"      - 实际: {actual_baidu_time:.1f}秒")
        time_error = abs(actual_baidu_time - expected_baidu_time) / expected_baidu_time * 100
        if time_error < 5:
            print(f"      - ✅ 误差 {time_error:.1f}%")
        else:
            print(f"      - ⚠️ 误差 {time_error:.1f}%")


if __name__ == "__main__":
    run_comparison()
    print("\n" + "=" * 70)
    print("混合QPS对比测试完成!")
    print("=" * 70)
