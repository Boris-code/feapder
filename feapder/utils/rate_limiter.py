# -*- coding: utf-8 -*-
"""
Created on 2024
---------
@summary: 域名级QPS限流模块，提供基于令牌桶算法的域名级别请求频率控制
---------
@author: ShellMonster
"""
import time
import threading
from typing import Dict, Optional
from urllib.parse import urlparse


class LocalTokenBucket:
    """
    本地内存令牌桶，基于令牌桶算法实现的单机限流器
    特点：线程安全、令牌按时间自动补充、支持预扣模式
    """

    def __init__(self, qps: int):
        """
        @summary: 初始化本地令牌桶
        ---------
        @param qps: 每秒允许的请求数（同时也是桶容量）
        ---------
        @result:
        """
        if qps <= 0:
            raise ValueError("qps must be positive")

        self.capacity = qps           # 桶容量（最大令牌数）
        self.tokens = 1.0             # 当前令牌数（初始1个，避免突发）
        self.qps = qps                # 每秒生成的令牌数
        self.last_update = time.time()
        self.lock = threading.Lock()

    def acquire(self) -> float:
        """
        @summary: 获取一个令牌
        ---------
        @result: 0 表示立即获得令牌，>0 表示需要等待的秒数（令牌已预扣）
        """
        with self.lock:
            now = time.time()
            # 防止系统时钟回拨导致的问题
            elapsed = max(0, now - self.last_update)

            # 根据时间流逝补充令牌（不超过桶容量）
            self.tokens = min(self.capacity, self.tokens + elapsed * self.qps)
            self.last_update = now

            if self.tokens >= 1:
                # 有令牌可用，消费一个
                self.tokens -= 1
                return 0
            else:
                # 无令牌，计算需要等待的时间
                # 等待时间 = (需要的令牌数 - 当前令牌数) / 每秒生成速率
                wait_time = (1 - self.tokens) / self.qps
                # 预扣令牌：tokens减1（可为负数），确保后续请求排队等待
                self.tokens -= 1
                return wait_time

    def __repr__(self) -> str:
        return f"LocalTokenBucket(qps={self.qps}, tokens={self.tokens:.2f})"


class RedisTokenBucket:
    """
    Redis分布式令牌桶，基于Redis + Lua脚本实现的分布式限流器
    特点：多进程/多机器共享QPS配额、Lua脚本保证操作原子性、自动过期清理
    """

    # Lua脚本：原子性地检查并消费令牌
    ACQUIRE_SCRIPT = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local qps = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])

    -- 获取当前状态
    local tokens = tonumber(redis.call('HGET', key, 'tokens'))
    local last_update = tonumber(redis.call('HGET', key, 'last_update'))

    -- 初始化（首次访问，初始1个令牌避免突发）
    if not tokens then
        tokens = 1
    end
    if not last_update then
        last_update = now
    end

    -- 计算应补充的令牌数（防止时钟回拨）
    local elapsed = math.max(0, now - last_update)
    tokens = math.min(capacity, tokens + elapsed * qps)

    -- 尝试消费令牌
    if tokens >= 1 then
        tokens = tokens - 1
        redis.call('HSET', key, 'tokens', tostring(tokens))
        redis.call('HSET', key, 'last_update', tostring(now))
        redis.call('EXPIRE', key, 3600)  -- 1小时无访问自动清理
        return 0  -- 成功获取
    else
        -- 计算等待时间并预扣
        local wait_time = (1 - tokens) / qps
        tokens = tokens - 1  -- 预扣令牌（可为负数），确保后续请求排队
        redis.call('HSET', key, 'tokens', tostring(tokens))
        redis.call('HSET', key, 'last_update', tostring(now))
        redis.call('EXPIRE', key, 3600)
        return wait_time
    end
    """

    def __init__(self, redis_client, key: str, qps: int):
        """
        @summary: 初始化Redis分布式令牌桶
        ---------
        @param redis_client: Redis客户端实例
        @param key: Redis中存储令牌桶状态的key
        @param qps: 每秒允许的请求数
        ---------
        @result:
        """
        if qps <= 0:
            raise ValueError("qps must be positive")

        self.redis = redis_client
        self.key = key
        self.qps = qps
        self.capacity = qps
        self._script = None  # 延迟注册脚本

    def acquire(self) -> float:
        """
        @summary: 获取一个令牌（分布式版本）
        ---------
        @result: 0 表示立即获得令牌，>0 表示需要等待的秒数
        """
        # 延迟注册Lua脚本（首次调用时）
        if self._script is None:
            self._script = self.redis.register_script(self.ACQUIRE_SCRIPT)

        result = self._script(
            keys=[self.key],
            args=[self.capacity, self.qps, time.time()]
        )
        return float(result)

    def __repr__(self) -> str:
        return f"RedisTokenBucket(key={self.key}, qps={self.qps})"


class DomainRateLimiter:
    """
    域名级限流管理器，统一管理多个域名的QPS限制
    支持精确域名匹配、通配符匹配、默认QPS、自动选择本地/Redis模式
    """

    def __init__(
        self,
        rules: Optional[Dict[str, int]] = None,
        default_qps: int = 0,
        storage: str = "local",
        redis_client=None
    ):
        """
        @summary: 初始化域名级限流管理器
        ---------
        @param rules: 域名QPS规则字典，格式 {"域名或通配符": QPS值}
        @param default_qps: 默认QPS限制，0表示不限制
        @param storage: 存储模式，"local"（本地内存）或 "redis"（分布式）
        @param redis_client: Redis客户端实例（storage="redis"时必须提供）
        ---------
        @result:
        """
        self.rules = rules or {}
        self.default_qps = default_qps
        self.storage = storage
        self.redis_client = redis_client

        # 令牌桶缓存（按域名+QPS组合）
        self._local_buckets: Dict[str, LocalTokenBucket] = {}
        self._redis_buckets: Dict[str, RedisTokenBucket] = {}

        # 验证参数
        if storage == "redis" and redis_client is None:
            raise ValueError("redis_client is required when storage='redis'")

    def get_qps_limit(self, domain: str) -> int:
        """
        @summary: 获取指定域名的QPS限制
                  匹配优先级：1.精确匹配 2.通配符匹配 3.默认值
        ---------
        @param domain: 域名（如 "www.baidu.com"）
        ---------
        @result: QPS限制值，0表示不限制
        """
        if not domain:
            return self.default_qps

        # 1. 精确匹配
        if domain in self.rules:
            return self.rules[domain]

        # 2. 通配符匹配（*.example.com）
        for pattern, qps in self.rules.items():
            if pattern.startswith("*."):
                suffix = pattern[2:]  # 去掉 "*."
                # 匹配 "sub.example.com" 或 "example.com" 本身
                if domain.endswith("." + suffix) or domain == suffix:
                    return qps

        # 3. 默认值
        return self.default_qps

    def acquire(self, domain: str) -> float:
        """
        @summary: 获取指定域名的一个令牌
        ---------
        @param domain: 域名
        ---------
        @result: 0 表示立即可执行，>0 表示需要等待的秒数
        """
        qps_limit = self.get_qps_limit(domain)

        # QPS <= 0 表示不限制
        if qps_limit <= 0:
            return 0

        # 根据存储模式选择令牌桶
        if self.storage == "redis" and self.redis_client:
            return self._acquire_redis(domain, qps_limit)
        else:
            return self._acquire_local(domain, qps_limit)

    def _acquire_local(self, domain: str, qps_limit: int) -> float:
        """从本地令牌桶获取令牌"""
        # 使用 "域名:QPS" 作为key，支持同一域名不同QPS配置
        cache_key = f"{domain}:{qps_limit}"

        if cache_key not in self._local_buckets:
            self._local_buckets[cache_key] = LocalTokenBucket(qps_limit)

        return self._local_buckets[cache_key].acquire()

    def _acquire_redis(self, domain: str, qps_limit: int) -> float:
        """从Redis令牌桶获取令牌"""
        # Redis key格式：feapder:rate_limit:域名:QPS
        redis_key = f"feapder:rate_limit:{domain}:{qps_limit}"

        if redis_key not in self._redis_buckets:
            self._redis_buckets[redis_key] = RedisTokenBucket(
                self.redis_client, redis_key, qps_limit
            )

        return self._redis_buckets[redis_key].acquire()

    @staticmethod
    def extract_domain(url: str) -> str:
        """
        @summary: 从URL中提取域名
        ---------
        @param url: 完整URL（如 "https://www.baidu.com/path?query=1"）
        ---------
        @result: 域名（如 "www.baidu.com"），提取失败返回空字符串
        """
        if not url:
            return ""

        try:
            parsed = urlparse(url)
            return parsed.hostname or ""
        except Exception:
            return ""

    def __repr__(self) -> str:
        return (
            f"DomainRateLimiter(rules={self.rules}, "
            f"default_qps={self.default_qps}, storage={self.storage})"
        )
