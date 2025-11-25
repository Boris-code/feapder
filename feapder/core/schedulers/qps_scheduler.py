# -*- coding: utf-8 -*-
"""
Created on 2024
---------
@summary: QPS调度器模块，基于令牌桶算法的域名级QPS限流调度器
---------
@author: ShellMonster
"""

import heapq
import threading
import time
from collections import defaultdict
from queue import Queue, Empty
from typing import Dict, Optional, Any

from feapder.utils.rate_limiter import DomainRateLimiter
from feapder.utils.log import log


class DelayedRequest:
    """
    延迟请求包装类，用于在延迟堆中存储等待执行的请求，支持按调度时间排序
    """

    __slots__ = ('scheduled_time', 'request', 'domain')

    def __init__(self, scheduled_time: float, request: Any, domain: str):
        """
        @summary: 初始化延迟请求
        ---------
        @param scheduled_time: 计划执行时间（Unix时间戳）
        @param request: 原始请求对象
        @param domain: 请求的域名
        ---------
        @result:
        """
        self.scheduled_time = scheduled_time
        self.request = request
        self.domain = domain

    def __lt__(self, other: 'DelayedRequest') -> bool:
        """按调度时间排序（最小堆）"""
        return self.scheduled_time < other.scheduled_time

    def __repr__(self) -> str:
        return f"DelayedRequest(scheduled={self.scheduled_time:.3f}, domain={self.domain})"


class QPSScheduler:
    """
    QPS调度器，单线程调度器，负责管理请求的QPS限流
    采用生产者-消费者模式，单线程处理避免令牌桶的并发竞争
    """

    def __init__(
        self,
        rate_limiter: DomainRateLimiter,
        max_prefetch: int = 100
    ):
        """
        @summary: 初始化QPS调度器
        ---------
        @param rate_limiter: 域名级限流器实例
        @param max_prefetch: 每个域名最大预取请求数，超过后阻塞提交（默认100）
        ---------
        @result:
        """
        self.rate_limiter = rate_limiter
        self.max_prefetch = max_prefetch

        # 提交队列：外部提交的请求先进入这里
        self._submit_queue: Queue = Queue()

        # 就绪队列：已获取令牌的请求
        self._ready_queue: Queue = Queue()

        # 延迟堆：等待令牌的请求（最小堆，按scheduled_time排序）
        self._delay_heap: list = []
        self._heap_lock = threading.Lock()

        # 每个域名当前在调度器中的请求数（提交队列 + 延迟堆 + 就绪队列）
        self._domain_pending_count: Dict[str, int] = defaultdict(int)
        self._count_lock = threading.Lock()

        # 调度线程控制
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None

        # 统计信息
        self._stats = {
            'submitted': 0,       # 提交的请求总数
            'immediate': 0,       # 立即获得令牌的请求数
            'delayed': 0,         # 需要延迟的请求数
            'ready': 0,           # 已就绪的请求数
        }

        # 状态日志控制
        self._last_status_log_time = 0
        self._status_log_interval = 10  # 每10秒输出一次状态

    def start(self) -> None:
        """
        @summary: 启动调度器，启动后台调度线程开始处理请求的QPS限流
        ---------
        @result:
        """
        if self._running:
            return

        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="QPSScheduler",
            daemon=True
        )
        self._scheduler_thread.start()
        log.debug("QPSScheduler started")

    def stop(self) -> None:
        """
        @summary: 停止调度器，优雅关闭调度线程
        ---------
        @result:
        """
        if not self._running:
            return

        self._running = False
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)
        log.debug("QPSScheduler stopped")

    def submit(self, request: Any, block: bool = True, timeout: float = None) -> bool:
        """
        @summary: 提交请求到调度器
                  请求会先进入提交队列，由调度线程处理QPS控制后放入就绪队列
        ---------
        @param request: 请求对象（需有url属性）或字典（分布式爬虫格式：{"request_obj": Request, "request_redis": str}）
        @param block: 当域名预取数达到上限时是否阻塞等待
        @param timeout: 阻塞超时时间（秒），None表示无限等待
        ---------
        @result: 提交成功返回True，超时返回False
        """
        # 提取域名，支持两种格式：
        # 1. AirSpider: request 是 Request 对象，有 url 属性
        # 2. Spider/BatchSpider/TaskSpider: request 是字典 {"request_obj": Request, "request_redis": str}
        if isinstance(request, dict) and 'request_obj' in request:
            url = getattr(request['request_obj'], 'url', '') or ''
        else:
            url = getattr(request, 'url', '') or ''
        domain = DomainRateLimiter.extract_domain(url)

        # 检查是否需要背压
        if self.max_prefetch > 0:
            start_time = time.time()
            logged_backpressure = False
            while True:
                with self._count_lock:
                    if self._domain_pending_count[domain] < self.max_prefetch:
                        self._domain_pending_count[domain] += 1
                        break

                if not block:
                    return False

                if timeout is not None and (time.time() - start_time) >= timeout:
                    return False

                # 背压阻塞日志（只输出一次，避免刷屏）
                if not logged_backpressure:
                    log.debug(
                        f"QPS背压: 域名 {domain} 待处理数达到上限 {self.max_prefetch}，等待释放..."
                    )
                    logged_backpressure = True

                # 等待一小段时间后重试
                time.sleep(0.01)
        else:
            with self._count_lock:
                self._domain_pending_count[domain] += 1

        # 放入提交队列
        self._submit_queue.put((request, domain))
        self._stats['submitted'] += 1
        return True

    def get_ready_request(self, timeout: float = 1.0) -> Optional[Any]:
        """
        @summary: 获取一个就绪的请求，从就绪队列获取已经获得令牌的请求
        ---------
        @param timeout: 等待超时时间（秒）
        ---------
        @result: 请求对象，超时返回None
        """
        try:
            request, domain = self._ready_queue.get(timeout=timeout)
            # 减少域名计数
            with self._count_lock:
                self._domain_pending_count[domain] = max(
                    0, self._domain_pending_count[domain] - 1
                )
            return request
        except Empty:
            return None

    def get_ready_request_nowait(self) -> Optional[Any]:
        """
        @summary: 非阻塞获取就绪请求
        ---------
        @result: 请求对象，队列为空返回None
        """
        try:
            request, domain = self._ready_queue.get_nowait()
            with self._count_lock:
                self._domain_pending_count[domain] = max(
                    0, self._domain_pending_count[domain] - 1
                )
            return request
        except Empty:
            return None

    def _scheduler_loop(self) -> None:
        """
        @summary: 调度器主循环
                  持续处理提交队列中的新请求，检查延迟堆中是否有到期的请求
        ---------
        @result:
        """
        while self._running:
            try:
                # 处理提交队列（非阻塞，处理所有待处理的）
                processed = self._process_submit_queue()

                # 处理延迟堆（将到期的请求移入就绪队列）
                moved = self._process_delay_heap()

                # 定期输出状态日志（DEBUG模式下）
                self._log_status_if_needed()

                # 如果没有任何工作，短暂休眠避免CPU空转
                if not processed and not moved:
                    time.sleep(0.001)  # 1ms

            except Exception as e:
                log.error(f"QPSScheduler error: {e}")
                time.sleep(0.01)

    def _process_submit_queue(self) -> int:
        """
        @summary: 处理提交队列
                  从提交队列取出请求，立即获得令牌则放入就绪队列，否则放入延迟堆
        ---------
        @result: 处理的请求数量
        """
        count = 0
        while True:
            try:
                request, domain = self._submit_queue.get_nowait()
            except Empty:
                break

            count += 1

            # 获取令牌
            wait_time = self.rate_limiter.acquire(domain)

            if wait_time <= 0:
                # 立即可执行，放入就绪队列
                self._ready_queue.put((request, domain))
                self._stats['immediate'] += 1
                self._stats['ready'] += 1
            else:
                # 需要等待，放入延迟堆
                scheduled_time = time.time() + wait_time
                delayed = DelayedRequest(scheduled_time, request, domain)
                with self._heap_lock:
                    heapq.heappush(self._delay_heap, delayed)
                self._stats['delayed'] += 1

        return count

    def _process_delay_heap(self) -> int:
        """
        @summary: 处理延迟堆，检查是否有到期的请求，将到期的移入就绪队列
        ---------
        @result: 移动的请求数量
        """
        count = 0
        now = time.time()

        with self._heap_lock:
            while self._delay_heap:
                # 查看堆顶（最早到期的）
                top = self._delay_heap[0]
                if top.scheduled_time > now:
                    # 还没到期，停止处理
                    break

                # 到期了，弹出并放入就绪队列
                heapq.heappop(self._delay_heap)
                self._ready_queue.put((top.request, top.domain))
                self._stats['ready'] += 1
                count += 1

        return count

    def _log_status_if_needed(self) -> None:
        """
        @summary: 定期输出调度器状态日志（DEBUG模式下）
        ---------
        @result:
        """
        now = time.time()
        if now - self._last_status_log_time >= self._status_log_interval:
            self._last_status_log_time = now

            with self._heap_lock:
                delay_heap_size = len(self._delay_heap)

            submit_queue_size = self._submit_queue.qsize()
            ready_queue_size = self._ready_queue.qsize()

            # 只有当有请求在处理时才输出日志
            if delay_heap_size > 0 or submit_queue_size > 0 or ready_queue_size > 0:
                log.debug(
                    f"QPS调度器状态: 提交队列={submit_queue_size}, "
                    f"延迟堆={delay_heap_size}, 就绪队列={ready_queue_size}, "
                    f"统计={self._stats}"
                )

    def is_empty(self) -> bool:
        """
        @summary: 检查调度器是否为空
                  当提交队列、延迟堆、就绪队列都为空时返回True
        ---------
        @result: 是否为空
        """
        with self._heap_lock:
            heap_empty = len(self._delay_heap) == 0

        return (
            self._submit_queue.empty() and
            heap_empty and
            self._ready_queue.empty()
        )

    def pending_count(self, domain: str = None) -> int:
        """
        @summary: 获取待处理请求数
        ---------
        @param domain: 指定域名，None表示所有域名
        ---------
        @result: 待处理请求数
        """
        with self._count_lock:
            if domain:
                return self._domain_pending_count.get(domain, 0)
            return sum(self._domain_pending_count.values())

    def get_stats(self) -> Dict[str, int]:
        """
        @summary: 获取统计信息
        ---------
        @result: 统计数据字典，包含submitted/immediate/delayed/ready等计数
        """
        return dict(self._stats)

    def __repr__(self) -> str:
        with self._heap_lock:
            heap_size = len(self._delay_heap)
        return (
            f"QPSScheduler("
            f"submit_queue={self._submit_queue.qsize()}, "
            f"delay_heap={heap_size}, "
            f"ready_queue={self._ready_queue.qsize()}, "
            f"running={self._running})"
        )
