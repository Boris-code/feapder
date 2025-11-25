# -*- coding: utf-8 -*-
"""
多域名、多线程QPS限流测试

测试目标：
1. 验证各域名的实际QPS是否符合配置
2. 验证不会出现"刚放进去又拿出来"的情况
3. 多线程并发场景下的正确性

Author: ShellMonster
Created: 2024
"""

import time
import threading
from collections import defaultdict
from feapder.utils.rate_limiter import DomainRateLimiter
from feapder.core.schedulers import QPSScheduler


class MockRequest:
    """模拟请求对象"""
    def __init__(self, url, submit_time=None):
        self.url = url
        self.submit_time = submit_time or time.time()  # 记录提交时间


def test_multi_domain_qps():
    """测试多域名QPS控制精度"""
    print("=" * 60)
    print("测试1: 多域名QPS控制精度测试")
    print("=" * 60)

    # 配置不同域名的QPS
    rules = {
        "www.baidu.com": 2,      # 百度 2 QPS
        "www.sogou.com": 3,      # 搜狗 3 QPS
        "www.sohu.com": 4,       # 搜狐 4 QPS
        "www.qq.com": 5,         # 腾讯 5 QPS
        "*.taobao.com": 2,       # 淘宝通配符 2 QPS
    }

    rate_limiter = DomainRateLimiter(rules=rules, default_qps=10)
    scheduler = QPSScheduler(rate_limiter, max_prefetch=100)
    scheduler.start()

    # 统计每个域名的请求完成时间
    domain_request_times = defaultdict(list)
    lock = threading.Lock()

    # 每个域名生成的请求数
    requests_per_domain = 10

    domains = [
        "www.baidu.com",
        "www.sogou.com",
        "www.sohu.com",
        "www.qq.com",
        "item.taobao.com",  # 测试通配符
        "detail.taobao.com",  # 测试通配符
    ]

    # 生产者：提交请求
    def submit_requests():
        for domain in domains:
            for i in range(requests_per_domain):
                url = f"https://{domain}/page{i}"
                request = MockRequest(url)
                scheduler.submit(request)
        print(f"已提交 {len(domains) * requests_per_domain} 个请求")

    # 消费者：获取并执行请求
    total_requests = len(domains) * requests_per_domain
    consumed = [0]

    def consume_requests():
        while consumed[0] < total_requests:
            request = scheduler.get_ready_request(timeout=0.5)
            if request:
                ready_time = time.time()
                domain = DomainRateLimiter.extract_domain(request.url)
                with lock:
                    domain_request_times[domain].append(ready_time)
                    consumed[0] += 1

    # 启动消费者线程（模拟多线程爬虫）
    num_consumers = 32
    consumer_threads = []
    for i in range(num_consumers):
        t = threading.Thread(target=consume_requests, name=f"Consumer-{i}")
        consumer_threads.append(t)
        t.start()

    # 提交请求
    start_time = time.time()
    submit_requests()

    # 等待所有消费者完成
    for t in consumer_threads:
        t.join(timeout=30)

    total_time = time.time() - start_time
    scheduler.stop()

    print(f"\n总耗时: {total_time:.2f}秒")
    print(f"处理请求数: {consumed[0]}")
    print("\n各域名实际QPS分析:")
    print("-" * 60)

    for domain in sorted(domain_request_times.keys()):
        times = sorted(domain_request_times[domain])
        if len(times) >= 2:
            # 计算实际QPS（请求数 / 时间跨度）
            time_span = times[-1] - times[0]
            if time_span > 0:
                actual_qps = (len(times) - 1) / time_span
            else:
                actual_qps = float('inf')

            # 计算平均间隔
            intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
            avg_interval = sum(intervals) / len(intervals) if intervals else 0

            configured_qps = rate_limiter.get_qps_limit(domain)
            expected_interval = 1.0 / configured_qps if configured_qps > 0 else 0

            print(f"{domain}:")
            print(f"  配置QPS: {configured_qps}, 实际QPS: {actual_qps:.2f}")
            print(f"  期望间隔: {expected_interval:.3f}s, 实际平均间隔: {avg_interval:.3f}s")
            print(f"  请求数: {len(times)}")
        else:
            print(f"{domain}: 请求数不足，无法计算QPS")

    print()


def test_no_immediate_return():
    """测试不会出现'刚放进去又拿出来'的问题"""
    print("=" * 60)
    print("测试2: 验证不会'刚放进去又拿出来'")
    print("=" * 60)

    rate_limiter = DomainRateLimiter(
        rules={"test.com": 2},  # 2 QPS，即每0.5秒一个
        default_qps=0
    )
    scheduler = QPSScheduler(rate_limiter, max_prefetch=100)
    scheduler.start()

    # 先消耗掉初始令牌
    for i in range(2):
        req = MockRequest(f"https://test.com/init{i}")
        scheduler.submit(req)

    time.sleep(0.1)  # 等待调度器处理

    # 消费掉初始的2个
    scheduler.get_ready_request(timeout=0.5)
    scheduler.get_ready_request(timeout=0.5)

    print("初始令牌已消耗完毕，现在测试新请求的延迟...")

    # 记录提交和获取时间
    results = []

    for i in range(5):
        submit_time = time.time()
        req = MockRequest(f"https://test.com/page{i}", submit_time)
        scheduler.submit(req)

        # 立即尝试获取
        ready_req = scheduler.get_ready_request(timeout=2.0)
        ready_time = time.time()

        if ready_req:
            delay = ready_time - submit_time
            results.append({
                'index': i,
                'submit_time': submit_time,
                'ready_time': ready_time,
                'delay': delay
            })
            print(f"  请求{i}: 提交后 {delay:.3f}s 后获取到")

    scheduler.stop()

    # 验证：除了第一个可能立即获取，后续的应该都有延迟
    immediate_count = sum(1 for r in results if r['delay'] < 0.1)
    delayed_count = sum(1 for r in results if r['delay'] >= 0.1)

    print(f"\n立即获取: {immediate_count}个, 延迟获取: {delayed_count}个")

    if delayed_count >= 4:
        print("✅ 测试通过：请求正确地被延迟处理")
    else:
        print("⚠️ 警告：可能存在'刚放进去又拿出来'的问题")

    print()


def test_concurrent_producers_consumers():
    """测试多生产者多消费者场景"""
    print("=" * 60)
    print("测试3: 多生产者多消费者并发测试")
    print("=" * 60)

    rules = {
        "www.baidu.com": 5,
        "www.sogou.com": 5,
        "www.sohu.com": 5,
        "www.qq.com": 5,
    }

    rate_limiter = DomainRateLimiter(rules=rules, default_qps=0)
    scheduler = QPSScheduler(rate_limiter, max_prefetch=50)
    scheduler.start()

    domains = list(rules.keys())
    requests_per_producer = 20
    num_producers = 8
    num_consumers = 32

    submitted = [0]
    consumed = [0]
    submit_lock = threading.Lock()
    consume_lock = threading.Lock()

    # 记录每个请求的提交时间和完成时间
    request_records = {}
    records_lock = threading.Lock()

    total_requests = num_producers * requests_per_producer

    def producer(producer_id):
        for i in range(requests_per_producer):
            domain = domains[i % len(domains)]
            url = f"https://{domain}/p{producer_id}_r{i}"
            req = MockRequest(url)

            with records_lock:
                request_records[url] = {'submit': time.time(), 'ready': None}

            scheduler.submit(req)

            with submit_lock:
                submitted[0] += 1

    def consumer(consumer_id):
        while True:
            with consume_lock:
                if consumed[0] >= total_requests:
                    break

            req = scheduler.get_ready_request(timeout=0.5)
            if req:
                ready_time = time.time()
                with records_lock:
                    if req.url in request_records:
                        request_records[req.url]['ready'] = ready_time

                with consume_lock:
                    consumed[0] += 1

    start_time = time.time()

    # 启动生产者
    producer_threads = []
    for i in range(num_producers):
        t = threading.Thread(target=producer, args=(i,))
        producer_threads.append(t)
        t.start()

    # 启动消费者
    consumer_threads = []
    for i in range(num_consumers):
        t = threading.Thread(target=consumer, args=(i,))
        consumer_threads.append(t)
        t.start()

    # 等待完成
    for t in producer_threads:
        t.join()
    for t in consumer_threads:
        t.join(timeout=30)

    total_time = time.time() - start_time
    scheduler.stop()

    print(f"生产者数: {num_producers}, 消费者数: {num_consumers}")
    print(f"总请求数: {total_requests}")
    print(f"已提交: {submitted[0]}, 已消费: {consumed[0]}")
    print(f"总耗时: {total_time:.2f}秒")

    # 分析延迟
    delays = []
    for url, record in request_records.items():
        if record['ready']:
            delay = record['ready'] - record['submit']
            delays.append(delay)

    if delays:
        avg_delay = sum(delays) / len(delays)
        max_delay = max(delays)
        min_delay = min(delays)
        print(f"\n延迟统计:")
        print(f"  平均延迟: {avg_delay:.3f}s")
        print(f"  最小延迟: {min_delay:.3f}s")
        print(f"  最大延迟: {max_delay:.3f}s")

    # 按域名统计
    print(f"\n各域名QPS验证:")
    domain_times = defaultdict(list)
    for url, record in request_records.items():
        if record['ready']:
            domain = DomainRateLimiter.extract_domain(url)
            domain_times[domain].append(record['ready'])

    for domain in sorted(domain_times.keys()):
        times = sorted(domain_times[domain])
        if len(times) >= 2:
            time_span = times[-1] - times[0]
            actual_qps = (len(times) - 1) / time_span if time_span > 0 else 0
            configured = rules.get(domain, 0)
            diff = abs(actual_qps - configured)
            status = "✅" if diff < 1 else "⚠️"
            print(f"  {status} {domain}: 配置={configured} QPS, 实际={actual_qps:.2f} QPS")

    print()


def test_strict_qps_measurement():
    """精确测量QPS"""
    print("=" * 60)
    print("测试4: 精确QPS测量（单域名）")
    print("=" * 60)

    target_qps = 5
    test_duration = 3  # 测试3秒

    rate_limiter = DomainRateLimiter(
        rules={"measure.com": target_qps},
        default_qps=0
    )
    scheduler = QPSScheduler(rate_limiter, max_prefetch=100)
    scheduler.start()

    request_times = []
    lock = threading.Lock()
    stop_flag = [False]

    # 持续提交请求
    def producer():
        i = 0
        while not stop_flag[0]:
            req = MockRequest(f"https://measure.com/page{i}")
            scheduler.submit(req, block=False)
            i += 1
            time.sleep(0.01)  # 避免提交太快

    # 持续消费并记录时间
    def consumer():
        while not stop_flag[0]:
            req = scheduler.get_ready_request(timeout=0.1)
            if req:
                with lock:
                    request_times.append(time.time())

    # 启动线程
    num_consumers = 32
    producer_thread = threading.Thread(target=producer)
    consumer_threads = [threading.Thread(target=consumer) for _ in range(num_consumers)]

    producer_thread.start()
    for t in consumer_threads:
        t.start()

    # 运行指定时间
    time.sleep(test_duration)
    stop_flag[0] = True

    producer_thread.join()
    for t in consumer_threads:
        t.join()

    scheduler.stop()

    # 分析结果
    if len(request_times) >= 2:
        request_times.sort()
        time_span = request_times[-1] - request_times[0]
        actual_qps = (len(request_times) - 1) / time_span if time_span > 0 else 0

        # 计算每秒的请求数
        second_counts = defaultdict(int)
        base_time = int(request_times[0])
        for t in request_times:
            second = int(t) - base_time
            second_counts[second] += 1

        print(f"配置QPS: {target_qps}")
        print(f"测试时长: {time_span:.2f}秒")
        print(f"总请求数: {len(request_times)}")
        print(f"实际QPS: {actual_qps:.2f}")
        print(f"\n每秒请求数分布:")
        for sec in sorted(second_counts.keys()):
            count = second_counts[sec]
            bar = "█" * count
            status = "✅" if abs(count - target_qps) <= 1 else "⚠️"
            print(f"  第{sec}秒: {count} 个 {status} {bar}")

        # 验证
        deviation = abs(actual_qps - target_qps) / target_qps * 100
        print(f"\nQPS偏差: {deviation:.1f}%")
        if deviation < 10:
            print("✅ QPS控制精度良好")
        else:
            print("⚠️ QPS控制存在较大偏差")

    print()


if __name__ == "__main__":
    test_multi_domain_qps()
    test_no_immediate_return()
    test_concurrent_producers_consumers()
    test_strict_qps_measurement()

    print("=" * 60)
    print("所有测试完成!")
    print("=" * 60)
