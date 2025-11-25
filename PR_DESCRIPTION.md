# feat: 域名级QPS限流功能

## 概述

本PR为feapder框架新增**域名级QPS限流**功能，支持对不同域名配置独立的请求频率限制，同时支持单机（AirSpider）和分布式（Spider/BatchSpider/TaskSpider）两种模式。

## 原始架构分析

### AirSpider 原始架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         AirSpider                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   start_requests()                                              │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────┐    put()     ┌──────────┐    get()    ┌────────┐ │
│   │ Request │ ──────────▶  │ MemoryDB │ ──────────▶ │ Parser │ │
│   │  生成   │              │  (队列)  │             │ Control│ │
│   └─────────┘              └──────────┘             └────────┘ │
│                                                         │       │
│                                                         ▼       │
│                                                    download     │
│                                                    & parse      │
└─────────────────────────────────────────────────────────────────┘

特点：
- 单进程内存队列
- 无请求频率控制
- 多线程并发消费
```

### 分布式爬虫（Spider/BatchSpider/TaskSpider）原始架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Scheduler (分布式调度器)                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   start_requests()                                                   │
│        │                                                             │
│        ▼                                                             │
│   ┌─────────┐   put()   ┌───────────┐  get()  ┌───────────────────┐ │
│   │ Request │ ────────▶ │   Redis   │ ──────▶ │    Collector      │ │
│   │  生成   │           │  (队列)   │         │ (批量获取+去重)   │ │
│   └─────────┘           └───────────┘         └───────────────────┘ │
│                                                        │             │
│                                                        ▼             │
│                                               ┌───────────────────┐  │
│                                               │   ParserControl   │  │
│                                               │  (多线程消费)     │  │
│                                               └───────────────────┘  │
│                                                        │             │
│                                                        ▼             │
│                                                  download & parse    │
└──────────────────────────────────────────────────────────────────────┘

特点：
- Redis分布式队列
- 支持多进程/多机器部署
- Collector负责批量获取和去重
- 无请求频率控制
```

## 新增QPS限流后的架构

### AirSpider QPS架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AirSpider (QPS模式)                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   start_requests()                                                      │
│        │                                                                │
│        ▼                                                                │
│   ┌─────────┐   put()   ┌──────────┐  get_nowait()  ┌───────────────┐  │
│   │ Request │ ────────▶ │ MemoryDB │ ─────────────▶ │ QPSScheduler  │  │
│   │  生成   │           │  (队列)  │    (批量)      │               │  │
│   └─────────┘           └──────────┘                │ ┌───────────┐ │  │
│                                                     │ │DomainRate │ │  │
│                                                     │ │ Limiter   │ │  │
│   ┌──────────────┐   get_ready_request()           │ ├───────────┤ │  │
│   │ParserControl │ ◀────────────────────────────── │ │DelayHeap  │ │  │
│   │ (多线程)     │                                  │ ├───────────┤ │  │
│   └──────────────┘                                  │ │ReadyQueue │ │  │
│         │                                           │ └───────────┘ │  │
│         ▼                                           └───────────────┘  │
│   download & parse                                                      │
└─────────────────────────────────────────────────────────────────────────┘

QPS控制流程：
1. Request 进入 MemoryDB
2. QPSScheduler 批量获取请求
3. DomainRateLimiter 根据域名获取令牌
   - 有令牌：直接进入 ReadyQueue
   - 无令牌：计算等待时间，进入 DelayHeap
4. 调度线程定时检查 DelayHeap，到期请求移入 ReadyQueue
5. ParserControl 从 ReadyQueue 获取请求处理
```

### 分布式爬虫 QPS架构

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    Scheduler (分布式QPS模式)                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   start_requests()                                                       │
│        │                                                                 │
│        ▼                                                                 │
│   ┌─────────┐  put()  ┌───────────┐ get() ┌───────────┐                 │
│   │ Request │ ──────▶ │   Redis   │ ────▶ │ Collector │                 │
│   │  生成   │         │  (队列)   │       └─────┬─────┘                 │
│   └─────────┘         └───────────┘             │                        │
│                                                 ▼                        │
│                                        ┌───────────────┐                 │
│                                        │ QPSScheduler  │                 │
│                                        │               │                 │
│    ┌──────────────┐                    │ ┌───────────┐ │                 │
│    │ParserControl │ ◀─────────────────│ │DomainRate │ │                 │
│    │ (多线程)     │  get_ready_request │ │ Limiter   │ │                 │
│    └──────────────┘                    │ │ (Redis)   │ │  ◀── 多进程共享 │
│          │                             │ ├───────────┤ │                 │
│          ▼                             │ │DelayHeap  │ │                 │
│    download & parse                    │ ├───────────┤ │                 │
│                                        │ │ReadyQueue │ │                 │
│                                        │ └───────────┘ │                 │
│                                        └───────────────┘                 │
└──────────────────────────────────────────────────────────────────────────┘

进程A ─┐
       ├──▶ RedisTokenBucket ──▶ 统一QPS配额
进程B ─┘

分布式特性：
- 令牌桶存储在Redis中（Lua脚本保证原子性）
- 多进程/多机器共享同一QPS配额
- 支持跨进程的精确QPS控制
```

## 核心组件

### 1. 令牌桶算法 (`feapder/utils/rate_limiter.py`)

| 类名 | 说明 | 适用场景 |
|-----|------|---------|
| `LocalTokenBucket` | 本地内存令牌桶，线程安全 | AirSpider / 单进程 |
| `RedisTokenBucket` | Redis分布式令牌桶，Lua脚本保证原子性 | Spider / 多进程分布式 |
| `DomainRateLimiter` | 域名级限流管理器，自动路由到对应令牌桶 | 统一接口 |

**令牌桶特性：**
- 预扣模式：请求到达时立即预扣令牌，返回等待时间
- 支持令牌为负数，确保后续请求正确排队
- 初始令牌数为1（而非桶容量），避免启动时突发

### 2. QPS调度器 (`feapder/core/schedulers/qps_scheduler.py`)

```python
class QPSScheduler:
    """
    单线程调度器，负责：
    1. 接收请求，通过DomainRateLimiter获取令牌
    2. 立即可执行的请求进入ReadyQueue
    3. 需等待的请求进入DelayHeap（按到期时间排序）
    4. 调度线程定时将到期请求从DelayHeap移入ReadyQueue
    """
```

### 3. 配置项 (`feapder/setting.py`)

```python
# 域名级QPS限流配置
DOMAIN_RATE_LIMIT_ENABLE = False          # 是否启用
DOMAIN_RATE_LIMIT_DEFAULT = 0             # 默认QPS，0表示不限制
DOMAIN_RATE_LIMIT_RULES = {}              # 域名规则 {"www.baidu.com": 2, "*.taobao.com": 5}
DOMAIN_RATE_LIMIT_MAX_PREFETCH = 100      # 最大预取数
DOMAIN_RATE_LIMIT_STORAGE = "local"       # 存储模式：local/redis
```

## 文件变更清单

### 新增文件

| 文件 | 行数 | 说明 |
|-----|-----|------|
| `feapder/utils/rate_limiter.py` | 282 | 令牌桶算法实现 |
| `feapder/core/schedulers/__init__.py` | 12 | 调度模块入口 |
| `feapder/core/schedulers/qps_scheduler.py` | 339 | QPS调度器 |
| `tests/qps-scheduler/*.py` | ~1000 | 单元测试和集成测试 |

### 修改文件

| 文件 | 改动 | 说明 |
|-----|-----|------|
| `feapder/setting.py` | +15 | 新增QPS配置项 |
| `feapder/db/memorydb.py` | +24 | 新增 `get_nowait()` 非阻塞方法 |
| `feapder/core/spiders/air_spider.py` | +29 | AirSpider QPS集成 |
| `feapder/core/parser_control.py` | +68 | ParserControl QPS集成 |
| `feapder/core/scheduler.py` | +30 | 分布式爬虫 QPS集成 |
| `feapder/templates/project_template/setting.py` | +15 | 模板配置更新 |

## 设计原则

### 1. 零侵入性
- **QPS关闭时**：代码流程与原始完全一致，无任何性能损耗
- **QPS开启时**：仅在获取请求环节增加调度逻辑

### 2. 向后兼容
- 所有配置项默认关闭
- 不影响现有爬虫的任何行为

### 3. 精确控制
- 令牌桶预扣机制确保QPS精度
- 测试验证：配置2 QPS，实际误差 < 2%

### 4. 分布式支持
- Redis令牌桶 + Lua脚本保证原子性
- 多进程共享QPS配额

## 测试验证

### 测试1：单机QPS精度测试

**测试场景**：32线程，baidu.com 配置 2 QPS，每域名20个请求

**测试命令**：
```bash
PYTHONPATH=. python tests/qps-scheduler/test_mixed_qps_comparison.py
```

**测试结果**：
```
======================================================================
测试①：QPS开启，混合限制（baidu=2QPS，sogou=不限制）
======================================================================
配置: 32线程, 每域名20请求
  - www.baidu.com: 限制 2 QPS
  - www.sogou.com: 不限制 (default=0)
  - 模拟处理时间: 10ms

总耗时: 10.01秒
调度器统计: {'submitted': 40, 'immediate': 21, 'delayed': 19, 'ready': 40}

baidu.com:
  处理请求: 20
  时间跨度: 9.501秒
  实际QPS: 2.00

sogou.com:
  处理请求: 20
  时间跨度: 0.000秒
  实际QPS: 334839.39 (不限制，瞬间完成)

✅ baidu.com QPS控制精确 (配置2, 实际2.00)
```

**验证结论**：

| 指标 | 配置值 | 实际值 | 误差 |
|-----|-------|-------|-----|
| baidu.com QPS | 2 | 2.00 | **0.0%** |
| 时间跨度 | 9.5秒 | 9.50秒 | **0.0%** |

---

### 测试2：混合限制测试（有限制 + 无限制）

**测试场景**：验证有限制域名被控制，无限制域名不受影响

**测试结果**：
```
======================================================================
对比分析结果
======================================================================

【1】QPS限制精度验证（baidu.com, 配置2QPS）
--------------------------------------------------
  配置QPS: 2
  实际QPS: 2.00
  误差: 0.0%
  ✅ QPS限制精确控制

【2】不限制域名性能对比（sogou.com）
--------------------------------------------------
  QPS开启(不限制域名):
      时间跨度: 0.000秒
      实际QPS: 334839.39
  QPS关闭:
      时间跨度: 0.002秒
      实际QPS: 249817.48

  ✅ 两种模式时间跨度都接近0，说明请求几乎瞬间被处理（不限制情况下）
```

**验证结论**：
- ✅ 有限制域名(baidu)：QPS被精确控制在 2.00
- ✅ 无限制域名(sogou)：不受QPS架构影响，瞬间完成

---

### 测试3：分布式多进程QPS共享测试

**测试场景**：2个进程共享 baidu.com = 2 QPS 配额，使用Redis令牌桶

**测试命令**：
```bash
PYTHONPATH=. python tests/qps-scheduler/test_distributed_qps.py
```

**测试结果**：
```
======================================================================
分布式QPS测试 - 多进程共享QPS配额
======================================================================

配置:
  - 进程数: 2
  - 每进程请求数: 10
  - 总请求数: 20
  - 目标共享QPS: 2
  - 预期总耗时: 9.5秒

启动 2 个进程...
[进程0] 获取请求 1/10: https://www.baidu.com/process0/page0
[进程0] 获取请求 2/10: https://www.baidu.com/process0/page1
...
[进程0] 完成，共处理 10 个请求
[进程1] 获取请求 1/10: https://www.baidu.com/process1/page0
...
[进程1] 完成，共处理 10 个请求

======================================================================
测试结果
======================================================================

总耗时: 10.01秒

进程0:
  请求数: 10
  时间跨度: 8.31秒
  单进程QPS: 1.08

进程1:
  请求数: 10
  时间跨度: 9.32秒
  单进程QPS: 0.97

--------------------------------------------------
【合并统计 - 所有进程】
--------------------------------------------------
  总请求数: 20
  总时间跨度: 9.34秒
  实际共享QPS: 2.03
  配置QPS: 2
  误差: 1.7%

✅ 分布式QPS共享控制精确！
   2个进程共享 2 QPS 配额，实际 2.03 QPS

时间跨度验证:
  预期: 9.5秒
  实际: 9.3秒
```

**验证结论**：

| 指标 | 预期值 | 实际值 | 误差 |
|-----|-------|-------|-----|
| 共享QPS | 2 | 2.03 | **1.7%** |
| 总时间跨度 | 9.5秒 | 9.34秒 | **1.7%** |
| 进程0 QPS | ~1 | 1.08 | - |
| 进程1 QPS | ~1 | 0.97 | - |

- ✅ 两个进程合计QPS精确控制在配置值
- ✅ Redis令牌桶正确实现跨进程共享

---

### 测试文件清单

| 测试文件 | 说明 |
|---------|------|
| `test_rate_limiter.py` | 令牌桶单元测试（15个用例） |
| `test_qps_scheduler.py` | QPS调度器单元测试（11个用例） |
| `test_mixed_qps_comparison.py` | 混合限制对比测试 |
| `test_distributed_qps.py` | 分布式多进程测试 |
| `test_feapder_integration.py` | AirSpider集成测试 |
| `test_multi_domain_qps.py` | 多域名QPS测试 |
| `test_air_spider_qps.py` | AirSpider QPS测试 |
| `test_performance_only.py` | 性能测试 |
| `test_realistic_performance.py` | 真实场景性能测试 |

**运行所有测试**：
```bash
PYTHONPATH=. python -m pytest tests/qps-scheduler/ -v
```

**测试结果**：38个测试全部通过

## 使用示例

### AirSpider 使用

```python
class MySpider(AirSpider):
    __custom_setting__ = {
        "DOMAIN_RATE_LIMIT_ENABLE": True,
        "DOMAIN_RATE_LIMIT_RULES": {
            "www.baidu.com": 2,      # 百度限制 2 QPS
            "*.taobao.com": 5,       # 淘宝全域名限制 5 QPS
        },
        "DOMAIN_RATE_LIMIT_DEFAULT": 10,  # 其他域名默认 10 QPS
    }
```

### 分布式爬虫使用

```python
class MySpider(Spider):
    __custom_setting__ = {
        "DOMAIN_RATE_LIMIT_ENABLE": True,
        "DOMAIN_RATE_LIMIT_STORAGE": "redis",  # 使用Redis共享配额
        "DOMAIN_RATE_LIMIT_RULES": {
            "api.example.com": 10,
        },
    }
```

## 作者

- **ShellMonster**
