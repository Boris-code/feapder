# 配置和运行时

## 配置来源

优先级：

1. Spider 类里的 `__custom_setting__`
2. 项目 `setting.py`
3. 支持的环境变量
4. `feapder/setting.py` 默认值

示例：

```python
class DemoSpider(feapder.Spider):
    __custom_setting__ = {
        "REDISDB_IP_PORTS": "localhost:6379",
        "SPIDER_MAX_RETRY_TIMES": 20,
    }
```

## 已有项目改配置

已有项目新增或调整 Redis/MySQL/Mongo、代理、线程数、重试、渲染、pipeline 等配置时，先定位项目根和实际加载的 `setting.py`。

默认优先改项目 `setting.py`，因为它是项目级配置入口。只有这些情况才优先放到 spider 类的 `__custom_setting__`：

- 配置确实只属于某一个 spider。
- 项目已有模式就是在目标 spider 里维护 `__custom_setting__`。
- 用户明确要求某个 spider 覆盖全局配置。

修改前检查：

- `main.py` 是否从项目根启动。
- 当前工作目录是否会影响 `setting.py` 加载。
- 目标 spider 是否已有 `__custom_setting__`。
- 环境变量是否覆盖同名配置。
- 当前 spider 类型是否真的使用该配置。

修改时增量合并现有配置，不要覆盖用户已有 `ITEM_PIPELINES`、Redis/MySQL 参数或渲染配置。

## 关键配置

数据库：

```python
MYSQL_IP = "localhost"
MYSQL_PORT = 3306
MYSQL_DB = "feapder"
MYSQL_USER_NAME = "feapder"
MYSQL_USER_PASS = "secret"

REDISDB_IP_PORTS = "localhost:6379"
REDISDB_USER_PASS = ""
REDISDB_DB = 0
REDISDB_SERVICE_NAME = ""
REDISDB_KWARGS = {}

MONGO_IP = "localhost"
MONGO_PORT = 27017
MONGO_DB = "feapder"
MONGO_URL = None
```

爬虫运行：

```python
COLLECTOR_TASK_COUNT = 32
SPIDER_THREAD_COUNT = 1
SPIDER_SLEEP_TIME = 0
SPIDER_MAX_RETRY_TIMES = 10
SPIDER_AUTO_START_REQUESTS = True
KEEP_ALIVE = False
REQUEST_LOST_TIMEOUT = 600
REQUEST_TIMEOUT = 22
```

Item 入库：

```python
ITEM_MAX_CACHED_COUNT = 5000
ITEM_UPLOAD_BATCH_MAX_SIZE = 1000
ITEM_UPLOAD_INTERVAL = 1
EXPORT_DATA_MAX_FAILED_TIMES = 10
EXPORT_DATA_MAX_RETRY_TIMES = 10
```

缓存和失败重试：

```python
RETRY_FAILED_REQUESTS = False
RETRY_FAILED_ITEMS = False
SAVE_FAILED_REQUEST = True
RESPONSE_CACHED_ENABLE = False
RESPONSE_CACHED_EXPIRE_TIME = 3600
RESPONSE_CACHED_USED = False
DELETE_KEYS = []
```

日志：

```python
LOG_LEVEL = "DEBUG"
LOG_PATH = "log/%s.log" % LOG_NAME
LOG_IS_WRITE_TO_CONSOLE = True
LOG_IS_WRITE_TO_FILE = False
```

## 配置不生效排查

1. 先检查 spider 类里是否有 `__custom_setting__` 覆盖。
2. 确认进程工作目录和实际加载的 `setting.py`。
3. 检查环境变量是否也设置了同名值。
4. 确认当前 spider 类型是否支持该配置。例如 `AirSpider` 不像 `Spider` 那样使用 Redis 请求队列。
5. 确认入口在正确项目路径下 import `feapder`。

## Redis Key

多数队列 key 都来自 `redis_key`：

- 请求队列：`{redis_key}:z_requests`
- 失败请求：`{redis_key}:z_failed_requests`
- 失败 item：`{redis_key}:s_failed_items`
- 爬虫状态：`{redis_key}:h_spider_status`

排查遗留任务、失败请求、重复消费时优先看这些 key。
