# 域名级QPS限制

域名级QPS限制功能允许你为不同的域名设置独立的请求速率限制（Queries Per Second），防止爬虫对目标网站造成过大压力，同时避免被反爬虫机制封禁。

## 1. 功能特性

- ✅ **支持所有Spider类型**：AirSpider、Spider、TaskSpider、BatchSpider
- ✅ **灵活的域名匹配**：支持精确域名、通配符域名（`*.google.com`）、www回退策略
- ✅ **分布式友好**：多台机器共享QPS配额（基于Redis）
- ✅ **非阻塞设计**：延迟调度机制，不会卡住工作线程
- ✅ **开箱即用**：只需配置，无需编写代码
- ✅ **容错能力强**：Redis异常时自动降级，不影响爬虫运行

## 2. 工作原理

QPS限制基于**令牌桶算法**实现：

- **AirSpider**：使用本地内存版令牌桶（线程安全）
- **Spider/TaskSpider/BatchSpider**：使用Redis分布式令牌桶（支持多机器共享配额）

当请求超过配置的QPS限制时，会自动延迟执行，而不是阻塞线程。

## 3. 基础使用

### 3.1 AirSpider示例

```python
import feapder

class MySpider(feapder.AirSpider):
    __custom_setting__ = dict(
        # 启用域名级QPS限制
        DOMAIN_RATE_LIMIT_ENABLE=True,
        # 默认每个域名10 QPS
        DOMAIN_RATE_LIMIT_DEFAULT=10,
        # 特定域名的QPS规则
        DOMAIN_RATE_LIMIT_RULES={
            "baidu.com": 5,              # 百度主域名限制5 QPS
            "api.baidu.com": 20,         # 百度API限制20 QPS
            "*.google.com": 8,           # 所有谷歌系域名8 QPS
        }
    )

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com")
        yield feapder.Request("https://api.baidu.com/v1/data")
        yield feapder.Request("https://maps.google.com")

    def parse(self, request, response):
        print(f"成功抓取: {request.url}")

if __name__ == "__main__":
    MySpider().start()
```

### 3.2 Spider示例

```python
import feapder

class MySpider(feapder.Spider):
    __custom_setting__ = dict(
        REDISDB_IP_PORTS="localhost:6379",
        REDISDB_USER_PASS="",
        REDISDB_DB=0,
        # QPS配置
        DOMAIN_RATE_LIMIT_ENABLE=True,
        DOMAIN_RATE_LIMIT_DEFAULT=10,
        DOMAIN_RATE_LIMIT_RULES={
            "baidu.com": 5,
            "zhihu.com": 3,
        }
    )

    def start_requests(self):
        for i in range(100):
            yield feapder.Request(f"https://www.baidu.com/s?wd={i}")

    def parse(self, request, response):
        print(f"成功抓取: {request.url}")

if __name__ == "__main__":
    MySpider(redis_key="test:qps").start()
```

## 4. 配置详解

### 4.1 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DOMAIN_RATE_LIMIT_ENABLE` | bool | False | 是否启用域名级QPS限制 |
| `DOMAIN_RATE_LIMIT_DEFAULT` | int | 10 | 默认每个域名的QPS限制 |
| `DOMAIN_RATE_LIMIT_RULES` | dict | {} | 特定域名的QPS规则 |

### 4.2 域名匹配规则

QPS配置按以下优先级匹配（从高到低）：

1. **单个请求的 qps_limit 参数**（最高优先级）
2. **精确域名匹配**（完全一致，包括www前缀）
3. **通配符匹配**（支持 `*.domain` 格式）
4. **www回退策略**（如果访问www.baidu.com未匹配，自动尝试baidu.com）
5. **默认值** `DOMAIN_RATE_LIMIT_DEFAULT`

#### 示例1：简化配置（推荐）

只配置主域名，www会自动回退：

```python
DOMAIN_RATE_LIMIT_RULES = {
    "baidu.com": 5,           # www.baidu.com 和 baidu.com 都限制为 5 QPS
    "api.baidu.com": 10,      # api.baidu.com 限制为 10 QPS
}
```

匹配结果：
- `https://www.baidu.com` → 5 QPS（回退到 baidu.com）
- `https://baidu.com` → 5 QPS（精确匹配）
- `https://api.baidu.com` → 10 QPS（精确匹配）
- `https://tieba.baidu.com` → 10 QPS（默认值）

#### 示例2：精确控制

区分www和非www：

```python
DOMAIN_RATE_LIMIT_RULES = {
    "www.example.com": 20,    # www流量大，限制宽松
    "example.com": 5,         # 非www流量小，限制严格
}
```

匹配结果：
- `https://www.example.com` → 20 QPS（精确匹配）
- `https://example.com` → 5 QPS（精确匹配）

#### 示例3：通配符匹配

限制整个域名族群：

```python
DOMAIN_RATE_LIMIT_RULES = {
    "*.google.com": 8,        # 所有谷歌三级域名
    "*.amazonaws.com": 15,    # 所有AWS服务
}
```

匹配结果：
- `https://maps.google.com` → 8 QPS（通配符匹配）
- `https://apis.google.com` → 8 QPS（通配符匹配）
- `https://google.com` → 10 QPS（通配符不匹配无子域名的情况，使用默认值）

## 5. 高级用法

### 5.1 单个请求自定义QPS

可以为单个请求设置独立的QPS限制：

```python
def start_requests(self):
    # 重要接口，限制1 QPS
    yield feapder.Request(
        "https://api.important.com/data",
        qps_limit=1  # 单独设置这个请求的QPS
    )

    # 普通接口，使用默认配置
    yield feapder.Request("https://www.baidu.com")
```

### 5.2 精细化域名控制

为不同级别的域名设置不同QPS：

```python
DOMAIN_RATE_LIMIT_RULES = {
    # 主域名
    "example.com": 5,

    # API子域名（通常可以承受更高QPS）
    "api.example.com": 20,

    # CDN子域名（静态资源，可以更高）
    "cdn.example.com": 50,

    # 通配符兜底
    "*.example.com": 3,       # 其他子域名保守限制
}
```

### 5.3 多爬虫任务独立限速

不同的爬虫任务使用不同的 `redis_key`，QPS配额相互独立：

```python
# 爬虫任务1：百度搜索，限制5 QPS
class BaiduSpider(feapder.Spider):
    __custom_setting__ = dict(
        DOMAIN_RATE_LIMIT_ENABLE=True,
        DOMAIN_RATE_LIMIT_RULES={"baidu.com": 5}
    )

# 爬虫任务2：同时抓取百度，限制10 QPS（不冲突）
class BaiduSpider2(feapder.Spider):
    __custom_setting__ = dict(
        DOMAIN_RATE_LIMIT_ENABLE=True,
        DOMAIN_RATE_LIMIT_RULES={"baidu.com": 10}
    )

if __name__ == "__main__":
    # 两个爬虫可以同时运行，各自有独立的QPS配额
    spider1 = BaiduSpider(redis_key="task1")
    spider2 = BaiduSpider2(redis_key="task2")

    spider1.start()
    # spider2.start()  # 可以在另一台机器上运行
```

## 6. 注意事项

### 6.1 Redis配置要求

- **Spider/TaskSpider/BatchSpider** 需要配置Redis才能使用分布式QPS限制
- **AirSpider** 使用本地内存，无需Redis

### 6.2 QPS计算方式

QPS = Queries Per Second（每秒请求数）

例如：配置 `"baidu.com": 5` 表示每秒最多发送5个请求到baidu.com

### 6.3 性能影响

- 本地令牌桶：几乎无性能损耗
- Redis令牌桶：每次请求增加 1-10ms 延迟（取决于Redis网络延迟）
- 对比HTTP请求耗时（通常100-1000ms），性能开销可忽略

### 6.4 容错机制

- Redis连接失败时，自动降级为放行所有请求
- 不会因为QPS限制模块异常而导致爬虫停止

## 7. 调试与监控

### 7.1 查看QPS限制日志

启用DEBUG日志级别可以看到QPS限制的详细信息：

```python
LOG_LEVEL = "DEBUG"
```

日志输出示例：

```
[QPS限制] 域名 baidu.com 达到限制 5 QPS, 延迟 0.20秒后重试
```

### 7.2 验证QPS是否生效

可以通过记录请求时间来验证：

```python
import time

class TestSpider(feapder.AirSpider):
    __custom_setting__ = dict(
        DOMAIN_RATE_LIMIT_ENABLE=True,
        DOMAIN_RATE_LIMIT_RULES={"httpbin.org": 2}  # 2 QPS
    )

    def parse(self, request, response):
        print(f"[{time.strftime('%H:%M:%S')}] 请求完成: {request.url}")
```

如果配置正确，你会看到请求按照设定的QPS速率执行。

## 8. 常见问题

### Q1: 为什么配置了QPS限制，但请求还是很快？

**A:** 检查以下几点：
1. 确认 `DOMAIN_RATE_LIMIT_ENABLE` 设置为 `True`
2. 检查域名是否匹配（注意www前缀）
3. 检查并发线程数 `SPIDER_THREAD_COUNT` 是否过大

### Q2: 多个域名同时爬取时，QPS如何计算？

**A:** 每个域名的QPS是独立计算的。例如：
- 同时爬取 baidu.com（5 QPS）和 google.com（8 QPS）
- 总QPS = 5 + 8 = 13 QPS

### Q3: AirSpider和Spider的QPS限制有什么区别？

**A:**
- **AirSpider**：本地内存版，单机独立QPS配额
- **Spider**：Redis分布式版，多台机器共享QPS配额

### Q4: 如何临时关闭QPS限制？

**A:** 设置 `DOMAIN_RATE_LIMIT_ENABLE=False` 即可

## 9. 最佳实践

### 9.1 推荐的QPS配置

根据目标网站类型，推荐以下QPS配置：

| 网站类型 | 推荐QPS | 说明 |
|---------|---------|------|
| 大型门户网站 | 5-10 | 如百度、新浪 |
| API接口 | 10-50 | 取决于服务商限制 |
| 小型网站 | 1-5 | 避免压力过大 |
| CDN静态资源 | 20-100 | 通常限制较宽松 |

### 9.2 配置建议

1. **优先使用简化配置**：只配置主域名（如 `baidu.com`），让www自动回退
2. **API独立配置**：API子域名通常需要更精确的QPS控制
3. **通配符兜底**：使用通配符为未知子域名设置保守的默认QPS
4. **逐步调整**：从保守的QPS开始，逐步提高直到找到最优值

### 9.3 监控与调优

```python
import time

class MonitorSpider(feapder.Spider):
    request_times = []

    def parse(self, request, response):
        # 记录请求时间
        self.request_times.append(time.time())

        # 每100个请求统计一次QPS
        if len(self.request_times) >= 100:
            duration = self.request_times[-1] - self.request_times[0]
            actual_qps = len(self.request_times) / duration
            print(f"实际QPS: {actual_qps:.2f}")
            self.request_times = []
```

## 10. 相关文档

- [Spider进阶](source_code/Spider进阶.md)
- [配置文件](source_code/配置文件.md)
- [命令行工具](command/cmdline.md)
