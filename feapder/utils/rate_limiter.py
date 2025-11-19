# -*- coding: utf-8 -*-
"""
Created on 2025-11-19
---------
@summary: 域名级QPS限制器（令牌桶算法）
---------
@author: feapder
"""

import time
import threading
from typing import Dict

import feapder.setting as setting
from feapder.db.redisdb import RedisDB
from feapder.utils.log import log


class LocalTokenBucket:
    """
    本地内存版令牌桶

    用于AirSpider（单机爬虫）
    线程安全，适用于多线程环境
    """

    def __init__(self, qps: int):
        """
        初始化令牌桶

        Args:
            qps: 每秒允许的请求数（Queries Per Second）
        """
        self.capacity = qps  # 桶容量（最大令牌数）
        self.tokens = float(qps)  # 当前令牌数
        self.qps = qps  # 每秒生成的令牌数
        self.last_update = time.time()  # 上次更新时间
        self.lock = threading.Lock()  # 线程锁

    def acquire(self) -> float:
        """
        尝试获取一个令牌

        Returns:
            float: 0表示成功获取令牌，>0表示需要等待的秒数
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update  # 时间流逝

            # 根据时间流逝补充令牌
            self.tokens = min(self.capacity, self.tokens + elapsed * self.qps)
            self.last_update = now

            # 尝试消费一个令牌
            if self.tokens >= 1:
                self.tokens -= 1
                return 0  # 成功
            else:
                # 计算需要等待多久才能获得令牌
                wait_time = (1 - self.tokens) / self.qps
                return wait_time


class RedisTokenBucket:
    """
    Redis分布式令牌桶

    用于Spider/TaskSpider/BatchSpider（分布式爬虫）
    使用Lua脚本保证原子性，支持多机器共享QPS配额
    """

    # Lua脚本：原子性地检查并消费令牌
    ACQUIRE_SCRIPT = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local qps = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])

    -- 获取当前令牌数和上次更新时间
    local tokens = tonumber(redis.call('HGET', key, 'tokens'))
    local last_update = tonumber(redis.call('HGET', key, 'last_update'))

    -- 如果是第一次访问，初始化
    if not tokens then
        tokens = capacity
    end
    if not last_update then
        last_update = now
    end

    -- 计算应该补充的令牌数
    local elapsed = now - last_update
    tokens = math.min(capacity, tokens + elapsed * qps)

    -- 尝试消费一个令牌
    if tokens >= 1 then
        -- 有令牌，消费一个
        tokens = tokens - 1
        redis.call('HSET', key, 'tokens', tostring(tokens))
        redis.call('HSET', key, 'last_update', tostring(now))
        redis.call('EXPIRE', key, 3600)  -- 1小时无访问自动清理
        return 0  -- 成功
    else
        -- 无令牌，计算需要等待的时间
        local wait_time = (1 - tokens) / qps
        return wait_time
    end
    """

    def __init__(self, redis_db: RedisDB, rate_limit_key: str, qps: int):
        """
        初始化Redis令牌桶

        Args:
            redis_db: RedisDB实例
            rate_limit_key: Redis中的key（格式: {redis_key}:h_rate_limit:{domain}）
            qps: 每秒允许的请求数
        """
        self.redis = redis_db._redis
        self.rate_limit_key = rate_limit_key
        self.qps = qps
        self.capacity = qps
        self.acquire_sha = None  # Lua脚本的SHA值（延迟加载）

    def _ensure_script_loaded(self):
        """确保Lua脚本已加载到Redis"""
        if not self.acquire_sha:
            try:
                self.acquire_sha = self.redis.script_load(self.ACQUIRE_SCRIPT)
            except Exception as e:
                log.error(f"加载Lua脚本失败: {e}")
                raise

    def acquire(self) -> float:
        """
        尝试获取一个令牌

        Returns:
            float: 0表示成功获取令牌，>0表示需要等待的秒数
        """
        try:
            self._ensure_script_loaded()
            now = time.time()

            # 执行Lua脚本（原子操作）
            wait_time = self.redis.evalsha(
                self.acquire_sha,
                1,  # KEYS数量
                self.rate_limit_key,  # KEYS[1]
                self.capacity,  # ARGV[1]
                self.qps,  # ARGV[2]
                now,  # ARGV[3]
            )

            return float(wait_time)

        except Exception as e:
            # Redis异常时放行请求，避免阻塞爬虫
            log.error(f"Redis令牌桶异常: {e}, 放行请求")
            return 0


class DomainRateLimiter:
    """
    域名级QPS限制器（统一管理器）

    职责:
    1. 自动检测Spider类型（AirSpider或分布式Spider）
    2. 为每个域名创建对应的令牌桶（本地或Redis）
    3. 提供统一的acquire接口
    """

    def __init__(self):
        """
        初始化限速器

        自动检测是否使用Redis（判断是否为分布式爬虫）
        """
        self.local_buckets: Dict[str, LocalTokenBucket] = {}  # 本地令牌桶缓存
        self.redis_buckets: Dict[str, RedisTokenBucket] = {}  # Redis令牌桶缓存
        self.redis_db = None  # Redis连接（延迟初始化）
        self.use_redis = self._should_use_redis()  # 是否使用Redis

    def _should_use_redis(self) -> bool:
        """
        判断是否应该使用Redis

        Returns:
            bool: True表示使用Redis（分布式爬虫），False表示使用本地内存（AirSpider）
        """
        # 检查是否配置了Redis连接
        if hasattr(setting, "REDISDB_IP_PORTS") and setting.REDISDB_IP_PORTS:
            return True
        return False

    def _get_redis_db(self):
        """获取Redis连接（单例模式）"""
        if not self.redis_db:
            self.redis_db = RedisDB()
        return self.redis_db

    def _get_rate_limit_key(self, request, domain: str) -> str:
        """
        生成QPS限制的Redis key

        格式: {redis_key}:h_rate_limit:{domain}

        Args:
            request: 请求对象
            domain: 域名

        Returns:
            str: Redis key
        """
        # 延迟导入避免循环依赖
        from feapder.network.request import Request

        # 获取redis_key
        # 优先从Request类变量获取（分布式Spider）
        redis_key = getattr(Request, "cached_redis_key", None)

        if not redis_key:
            # AirSpider情况，使用parser_name
            redis_key = getattr(request, "parser_name", None) or "default"

        # 使用setting中定义的模板
        return setting.TAB_RATE_LIMIT.format(redis_key=redis_key, domain=domain)

    def _get_local_bucket(self, domain: str, qps: int) -> LocalTokenBucket:
        """
        获取本地令牌桶（缓存）

        Args:
            domain: 域名
            qps: QPS限制

        Returns:
            LocalTokenBucket: 本地令牌桶实例
        """
        cache_key = f"{domain}:{qps}"

        if cache_key not in self.local_buckets:
            self.local_buckets[cache_key] = LocalTokenBucket(qps)

        return self.local_buckets[cache_key]

    def _get_redis_bucket(self, rate_limit_key: str, qps: int) -> RedisTokenBucket:
        """
        获取Redis令牌桶（缓存）

        Args:
            rate_limit_key: Redis key
            qps: QPS限制

        Returns:
            RedisTokenBucket: Redis令牌桶实例
        """
        cache_key = f"{rate_limit_key}:{qps}"

        if cache_key not in self.redis_buckets:
            redis_db = self._get_redis_db()
            self.redis_buckets[cache_key] = RedisTokenBucket(
                redis_db, rate_limit_key, qps
            )

        return self.redis_buckets[cache_key]

    def acquire(self, request, domain: str, qps_limit: int) -> float:
        """
        尝试获取令牌（统一入口）

        根据Spider类型自动选择本地或Redis令牌桶

        Args:
            request: 请求对象
            domain: 域名
            qps_limit: QPS限制

        Returns:
            float: 0表示成功，>0表示需要等待的秒数
        """
        if self.use_redis:
            # 使用Redis分布式令牌桶
            rate_limit_key = self._get_rate_limit_key(request, domain)
            bucket = self._get_redis_bucket(rate_limit_key, qps_limit)
        else:
            # 使用本地内存令牌桶
            bucket = self._get_local_bucket(domain, qps_limit)

        return bucket.acquire()
