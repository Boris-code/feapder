# -*- coding: utf-8 -*-
"""
分布式QPS测试 - 多进程共享QPS配额

测试场景：
- 启动2个进程，模拟2个爬虫实例
- 配置 baidu.com QPS=2（两个进程共享这个配额）
- 验证两个进程合计的QPS是否被控制在2

运行前请设置环境变量：
    export REDIS_HOST=your_redis_host
    export REDIS_PORT=6379
    export REDIS_PASSWORD=your_password

Author: ShellMonster
Created: 2024
"""

import os
import time
import redis
import multiprocessing
from collections import defaultdict

from feapder.core.schedulers import QPSScheduler
from feapder.utils.rate_limiter import DomainRateLimiter
from feapder.network.request import Request


# Redis配置（从环境变量读取）
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "password": os.getenv("REDIS_PASSWORD", ""),
    "decode_responses": True,
}

# 测试配置
TARGET_QPS = 2  # 目标QPS（两个进程共享）
NUM_REQUESTS_PER_PROCESS = 10  # 每个进程发送的请求数
NUM_PROCESSES = 2  # 进程数


def clear_redis_keys():
    """清理Redis中的测试数据"""
    r = redis.Redis(**REDIS_CONFIG)
    # 清理令牌桶相关的key
    keys = r.keys("feapder:rate_limit:*")
    if keys:
        r.delete(*keys)
    print(f"已清理 {len(keys)} 个Redis key")


def worker_process(process_id, result_queue):
    """
    工作进程：模拟一个爬虫实例

    @param process_id: 进程ID
    @param result_queue: 结果队列，用于收集请求时间
    """
    # 创建Redis客户端
    redis_client = redis.Redis(**REDIS_CONFIG)

    # 创建限流器（Redis模式）
    rate_limiter = DomainRateLimiter(
        rules={"www.baidu.com": TARGET_QPS},
        default_qps=0,
        storage="redis",
        redis_client=redis_client,
    )

    # 创建调度器
    scheduler = QPSScheduler(rate_limiter=rate_limiter, max_prefetch=50)
    scheduler.start()

    # 记录请求时间
    request_times = []

    # 提交请求
    for i in range(NUM_REQUESTS_PER_PROCESS):
        scheduler.submit(Request(f"https://www.baidu.com/process{process_id}/page{i}"))

    # 获取就绪的请求
    completed = 0
    while completed < NUM_REQUESTS_PER_PROCESS:
        request = scheduler.get_ready_request(timeout=1.0)
        if request:
            request_times.append(time.time())
            completed += 1
            print(f"[进程{process_id}] 获取请求 {completed}/{NUM_REQUESTS_PER_PROCESS}: {request.url}")

    scheduler.stop()

    # 将结果放入队列
    result_queue.put({
        "process_id": process_id,
        "times": request_times,
    })

    print(f"[进程{process_id}] 完成，共处理 {len(request_times)} 个请求")


def run_distributed_test():
    """运行分布式QPS测试"""
    print("=" * 70)
    print("分布式QPS测试 - 多进程共享QPS配额")
    print("=" * 70)
    print(f"\n配置:")
    print(f"  - 进程数: {NUM_PROCESSES}")
    print(f"  - 每进程请求数: {NUM_REQUESTS_PER_PROCESS}")
    print(f"  - 总请求数: {NUM_PROCESSES * NUM_REQUESTS_PER_PROCESS}")
    print(f"  - 目标共享QPS: {TARGET_QPS}")
    print(f"  - 预期总耗时: {(NUM_PROCESSES * NUM_REQUESTS_PER_PROCESS - 1) / TARGET_QPS:.1f}秒")

    # 清理Redis
    print("\n清理Redis...")
    clear_redis_keys()

    # 创建结果队列
    result_queue = multiprocessing.Queue()

    # 启动多个进程
    print(f"\n启动 {NUM_PROCESSES} 个进程...")
    start_time = time.time()

    processes = []
    for i in range(NUM_PROCESSES):
        p = multiprocessing.Process(target=worker_process, args=(i, result_queue))
        p.start()
        processes.append(p)

    # 等待所有进程完成
    for p in processes:
        p.join(timeout=60)

    total_duration = time.time() - start_time

    # 收集结果
    all_times = []
    process_results = {}

    while not result_queue.empty():
        result = result_queue.get()
        process_results[result["process_id"]] = result["times"]
        all_times.extend(result["times"])

    # 分析结果
    print("\n" + "=" * 70)
    print("测试结果")
    print("=" * 70)

    print(f"\n总耗时: {total_duration:.2f}秒")

    # 各进程统计
    for pid, times in sorted(process_results.items()):
        times = sorted(times)
        count = len(times)
        if count >= 2:
            time_span = times[-1] - times[0]
            qps = (count - 1) / time_span if time_span > 0 else float('inf')
        else:
            time_span = 0
            qps = 0
        print(f"\n进程{pid}:")
        print(f"  请求数: {count}")
        print(f"  时间跨度: {time_span:.2f}秒")
        print(f"  单进程QPS: {qps:.2f}")

    # 合并统计（关键指标）
    all_times.sort()
    total_count = len(all_times)
    if total_count >= 2:
        total_time_span = all_times[-1] - all_times[0]
        actual_qps = (total_count - 1) / total_time_span if total_time_span > 0 else float('inf')
    else:
        total_time_span = 0
        actual_qps = 0

    print("\n" + "-" * 50)
    print("【合并统计 - 所有进程】")
    print("-" * 50)
    print(f"  总请求数: {total_count}")
    print(f"  总时间跨度: {total_time_span:.2f}秒")
    print(f"  实际共享QPS: {actual_qps:.2f}")
    print(f"  配置QPS: {TARGET_QPS}")

    # 验证QPS
    qps_error = abs(actual_qps - TARGET_QPS) / TARGET_QPS * 100
    print(f"  误差: {qps_error:.1f}%")

    if qps_error < 10:
        print(f"\n✅ 分布式QPS共享控制精确！")
        print(f"   {NUM_PROCESSES}个进程共享 {TARGET_QPS} QPS 配额，实际 {actual_qps:.2f} QPS")
    else:
        print(f"\n⚠️ 分布式QPS控制有偏差")

    # 验证时间跨度
    expected_time = (total_count - 1) / TARGET_QPS
    print(f"\n时间跨度验证:")
    print(f"  预期: {expected_time:.1f}秒")
    print(f"  实际: {total_time_span:.1f}秒")

    # 清理
    print("\n清理Redis...")
    clear_redis_keys()


if __name__ == "__main__":
    run_distributed_test()
    print("\n" + "=" * 70)
    print("分布式QPS测试完成!")
    print("=" * 70)
