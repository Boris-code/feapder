# 域名级QPS限流

域名级QPS限流功能可以针对不同域名配置独立的请求频率限制，防止因请求过快被目标网站封禁，同时支持单机和分布式两种模式。

## 1. 功能特点

- **域名级别控制**：可为不同域名配置不同的QPS限制
- **精确控制**：基于令牌桶算法，QPS控制误差 < 2%
- **通配符支持**：支持 `*.example.com` 匹配所有子域名
- **分布式支持**：多进程/多机器可共享同一QPS配额
- **零侵入性**：关闭时不影响原有流程和性能

## 2. 配置说明

在 `setting.py` 或 `__custom_setting__` 中配置：

```python
# 域名级QPS限流配置
DOMAIN_RATE_LIMIT_ENABLE = False          # 是否启用，默认关闭
DOMAIN_RATE_LIMIT_DEFAULT = 0             # 默认QPS限制，0表示不限制
DOMAIN_RATE_LIMIT_RULES = {}              # 域名QPS规则
DOMAIN_RATE_LIMIT_MAX_PREFETCH = 100      # 最大预取请求数
DOMAIN_RATE_LIMIT_STORAGE = "local"       # 存储模式：local/redis
```

### 配置项详解

| 配置项 | 类型 | 默认值 | 说明 |
|-------|------|-------|------|
| `DOMAIN_RATE_LIMIT_ENABLE` | bool | False | 是否启用QPS限流 |
| `DOMAIN_RATE_LIMIT_DEFAULT` | int | 0 | 默认QPS，0表示不限制 |
| `DOMAIN_RATE_LIMIT_RULES` | dict | {} | 域名QPS规则字典 |
| `DOMAIN_RATE_LIMIT_MAX_PREFETCH` | int | 100 | 最大预取数，防止内存溢出 |
| `DOMAIN_RATE_LIMIT_STORAGE` | str | "local" | 存储模式，local或redis |

### 存储模式

| 模式 | 说明 | 适用场景 |
|-----|------|---------|
| `local` | 本地内存存储 | AirSpider、单进程爬虫 |
| `redis` | Redis分布式存储 | 多进程/多机器部署，需共享QPS配额 |

## 3. 使用示例

### AirSpider 使用

```python
import feapder


class MySpider(feapder.AirSpider):
    __custom_setting__ = dict(
        DOMAIN_RATE_LIMIT_ENABLE=True,
        DOMAIN_RATE_LIMIT_RULES={
            "www.baidu.com": 2,      # 百度限制 2 QPS
            "*.taobao.com": 5,       # 淘宝全域名限制 5 QPS
        },
        DOMAIN_RATE_LIMIT_DEFAULT=10,  # 其他域名默认 10 QPS
    )

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com/s?wd=test1")
        yield feapder.Request("https://www.baidu.com/s?wd=test2")
        yield feapder.Request("https://item.taobao.com/item1")
        yield feapder.Request("https://detail.taobao.com/item2")

    def parse(self, request, response):
        print(f"处理: {request.url}")


if __name__ == "__main__":
    MySpider(thread_count=10).start()
```

上述代码中：
- `www.baidu.com` 的请求频率被限制为每秒2次
- `*.taobao.com` 匹配 `item.taobao.com`、`detail.taobao.com` 等，限制为每秒5次
- 其他未匹配的域名，使用默认限制每秒10次

### Spider 分布式使用

```python
import feapder


class MyDistributedSpider(feapder.Spider):
    __custom_setting__ = dict(
        REDISDB_IP_PORTS="localhost:6379",
        REDISDB_USER_PASS="",
        REDISDB_DB=0,

        # QPS限流配置
        DOMAIN_RATE_LIMIT_ENABLE=True,
        DOMAIN_RATE_LIMIT_STORAGE="redis",  # 使用Redis，多进程共享配额
        DOMAIN_RATE_LIMIT_RULES={
            "api.example.com": 10,   # API限制 10 QPS
        },
        DOMAIN_RATE_LIMIT_DEFAULT=20,
    )

    def start_requests(self):
        for i in range(100):
            yield feapder.Request(f"https://api.example.com/data/{i}")

    def parse(self, request, response):
        print(f"处理: {request.url}")


if __name__ == "__main__":
    MyDistributedSpider(redis_key="test:spider").start()
```

分布式模式下，多个进程共享同一个Redis令牌桶，确保所有进程合计的QPS不超过配置值。

### 混合限制示例

```python
__custom_setting__ = dict(
    DOMAIN_RATE_LIMIT_ENABLE=True,
    DOMAIN_RATE_LIMIT_RULES={
        "www.baidu.com": 2,         # 精确匹配
        "*.taobao.com": 5,          # 通配符匹配
        "api.jd.com": 10,           # 精确匹配
    },
    DOMAIN_RATE_LIMIT_DEFAULT=0,    # 其他域名不限制
)
```

匹配优先级：
1. **精确匹配**：先检查域名是否完全匹配
2. **通配符匹配**：检查是否匹配 `*.xxx.com` 模式
3. **默认值**：使用 `DOMAIN_RATE_LIMIT_DEFAULT`

## 4. 工作原理

### 架构图

```
                    ┌──────────────────────────────────────┐
                    │           QPSScheduler               │
                    │                                      │
   Request ───────▶ │  ┌────────────────────────────────┐  │
                    │  │      DomainRateLimiter         │  │
                    │  │  ┌──────────┐ ┌──────────────┐ │  │
                    │  │  │ 令牌桶1  │ │   令牌桶2    │ │  │
                    │  │  │(baidu)   │ │ (*.taobao)   │ │  │
                    │  │  └──────────┘ └──────────────┘ │  │
                    │  └────────────────────────────────┘  │
                    │           │                          │
                    │           ▼                          │
                    │  ┌─────────────┐  ┌─────────────┐   │
                    │  │  DelayHeap  │  │ ReadyQueue  │   │
                    │  │ (等待队列)  │  │ (就绪队列)  │   │
                    │  └─────────────┘  └─────────────┘   │
                    │                          │          │
                    └──────────────────────────│──────────┘
                                               ▼
                                        ParserControl
                                         (消费处理)
```

### 令牌桶算法

采用令牌桶算法实现精确的QPS控制：

1. **令牌生成**：按配置的QPS速率持续生成令牌
2. **令牌消费**：每个请求消费一个令牌
3. **预扣机制**：请求到达时立即预扣令牌，返回等待时间
4. **排队等待**：令牌不足时，请求进入延迟队列等待

### 分布式模式

分布式模式使用Redis + Lua脚本实现：

```
进程A ──┐
        ├──▶ Redis令牌桶 ──▶ 统一QPS配额
进程B ──┘

Lua脚本保证操作原子性，避免竞争条件
```

## 5. 支持的爬虫类型

| 爬虫类型 | 支持 | 推荐存储模式 |
|---------|-----|-------------|
| AirSpider | ✅ | local |
| Spider | ✅ | redis（多进程时） |
| BatchSpider | ✅ | redis（多进程时） |
| TaskSpider | ✅ | redis（多进程时） |

## 6. 注意事项

1. **QPS=0 表示不限制**：配置为0的域名或默认值为0时，对应请求不受QPS限制

2. **多进程必须用Redis模式**：`local` 模式下每个进程有独立的令牌桶，无法共享配额

3. **预取数量**：`DOMAIN_RATE_LIMIT_MAX_PREFETCH` 控制调度器预取的请求数，过大会占用内存，过小可能影响性能

4. **性能影响**：QPS关闭时（`DOMAIN_RATE_LIMIT_ENABLE=False`），代码流程与原始完全一致，无任何性能损耗

5. **通配符匹配**：`*.example.com` 可匹配 `a.example.com`、`b.c.example.com` 等，但不匹配 `example.com` 本身

## 7. 完整代码示例

### 示例1：基础使用

```python
import feapder


class BasicQPSSpider(feapder.AirSpider):
    __custom_setting__ = dict(
        DOMAIN_RATE_LIMIT_ENABLE=True,
        DOMAIN_RATE_LIMIT_RULES={
            "httpbin.org": 2,  # 限制 2 QPS
        },
    )

    def start_requests(self):
        for i in range(10):
            yield feapder.Request(f"https://httpbin.org/get?id={i}")

    def parse(self, request, response):
        print(f"状态码: {response.status_code}, URL: {request.url}")


if __name__ == "__main__":
    BasicQPSSpider(thread_count=10).start()
```

### 示例2：分布式多进程

```python
import feapder


class DistributedQPSSpider(feapder.Spider):
    __custom_setting__ = dict(
        REDISDB_IP_PORTS="localhost:6379",
        REDISDB_USER_PASS="",
        REDISDB_DB=0,

        DOMAIN_RATE_LIMIT_ENABLE=True,
        DOMAIN_RATE_LIMIT_STORAGE="redis",
        DOMAIN_RATE_LIMIT_RULES={
            "api.example.com": 5,  # 多进程合计 5 QPS
        },
    )

    def start_requests(self):
        for i in range(50):
            yield feapder.Request(f"https://api.example.com/item/{i}")

    def parse(self, request, response):
        print(f"处理: {request.url}")


if __name__ == "__main__":
    # 可启动多个进程，共享 5 QPS 配额
    DistributedQPSSpider(redis_key="qps:spider").start()
```

## 8. 常见问题

### Q: QPS设置了但没生效？

A: 检查以下几点：
1. `DOMAIN_RATE_LIMIT_ENABLE` 是否为 `True`
2. 域名规则是否正确匹配（注意 `www.baidu.com` 和 `baidu.com` 是不同的）
3. 分布式模式下是否配置了 `DOMAIN_RATE_LIMIT_STORAGE="redis"`

### Q: 多进程QPS不准确？

A: 确保使用 `redis` 存储模式，`local` 模式下各进程独立计算，无法共享配额。

### Q: 如何关闭某个域名的限制？

A: 将该域名的QPS设置为0，或不在规则中配置该域名且 `DOMAIN_RATE_LIMIT_DEFAULT=0`。
