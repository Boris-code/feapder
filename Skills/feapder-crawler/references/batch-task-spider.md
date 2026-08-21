# TaskSpider 和 BatchSpider

## TaskSpider

`TaskSpider` 把种子任务下发和 worker 采集分开。

常见构造参数：

```python
spider = TaskSpiderTest(
    task_table="spider_task",
    task_keys=["id", "url"],
    redis_key="test:task_spider",
    keep_alive=True,
)
```

Redis 任务源：

```python
spider = TaskSpiderTest(
    task_table="spider_task2",
    task_table_type="redis",
    redis_key="test:task_spider",
    keep_alive=True,
    use_mysql=False,
)
```

最小完整结构：

```python
import feapder
from items.seed_result_item import SeedResultItem


class SeedTaskSpider(feapder.TaskSpider):
    def add_task(self):
        self._redisdb.zadd(self._task_table, {"id": 1, "url": "https://example.com"})

    def start_requests(self, task):
        task_id, url = task
        yield feapder.Request(url, task_id=task_id)

    def parse(self, request, response):
        item = SeedResultItem()
        item.url = request.url
        item.title = response.xpath("//title/text()").extract_first()
        yield item


def create_mysql_task_spider():
    return SeedTaskSpider(
        task_table="spider_task",
        task_keys=["id", "url"],
        redis_key="feapder:task_spider",
        keep_alive=True,
    )


def create_redis_task_spider():
    return SeedTaskSpider(
        task_table="spider_task_redis",
        task_table_type="redis",
        redis_key="feapder:task_spider",
        keep_alive=True,
        use_mysql=False,
    )
```

运行模式：

```python
spider.start_monitor_task()  # 下发和监控任务
spider.start()               # worker 采集
```

`add_task()` 可在 `start_monitor_task()` 阶段塞种子任务。不要把它写成死循环。

`start_requests(self, task)` 接收一行任务。常见读取方式：

```python
task_id, url = task
task_id = task.id
url = task["url"]
url = task.get("url")
```

## BatchSpider

`BatchSpider` 用于周期性批次采集。它用 Redis 做请求调度，用 MySQL 维护任务和批次状态。
不要把 BatchSpider 写成单入口普通脚本。它通常需要区分 master 下发/监控和 worker 采集，并在 request 上携带 `task_id`，解析完成后用 `update_task_batch()` 更新状态。

典型构造：

```python
spider = ProductSpider(
    redis_key="feapder:product",
    task_table="product_task",
    task_keys=["id", "url"],
    task_state="state",
    batch_record_table="product_batch_record",
    batch_name="product daily crawl",
    batch_interval=1,
)
```

最小完整结构：

```python
import feapder
from items.product_price_item import ProductPriceItem


class ProductBatchSpider(feapder.BatchSpider):
    def start_requests(self, task):
        task_id, url = task
        yield feapder.Request(url, task_id=task_id)

    def parse(self, request, response):
        item = ProductPriceItem()
        item.url = request.url
        item.title = response.xpath("//title/text()").extract_first()
        yield item

        yield self.update_task_batch(request.task_id, 1)

    def failed_request(self, request, response, e):
        yield self.update_task_batch(request.task_id, -1)


def create_spider():
    return ProductBatchSpider(
        redis_key="feapder:product_price",
        task_table="product_task",
        task_keys=["id", "url"],
        task_state="state",
        batch_record_table="product_batch_record",
        batch_name="product price daily",
        batch_interval=1,
    )


if __name__ == "__main__":
    spider = create_spider()
    # spider.start_monitor_task()  # master: 下发和监控任务
    spider.start()                 # worker: 采集
```

任务状态约定：

- `0`：待抓取
- `1`：已完成
- `2`：抓取中或已下发
- `-1`：无效或永久失败

每个批次默认会把非 `-1` 任务重置为 `0`。如果是增量采集，已完成任务不应重置，可以重写 `init_task()` 并置空。

## 任务完成状态

请求中携带 `task_id`：

```python
def start_requests(self, task):
    task_id, url = task
    yield feapder.Request(url, task_id=task_id)
```

标记完成：

```python
yield self.update_task_batch(request.task_id, 1)
```

超过最大重试后标记无效：

```python
def failed_request(self, request, response, e):
    yield self.update_task_batch(request.task_id, -1)
```

普通 `Spider` 失败处理通常不需要更新任务表，但可以记录失败、切换 cookie/proxy 或返回新请求：

```python
def exception_request(self, request, response, e):
    # 单次异常，可调整 request 后重试
    request.headers = {"User-Agent": "Mozilla/5.0"}
    yield request


def failed_request(self, request, response, e):
    # 超过最大重试次数后的最终失败
    self.logger.error(f"failed url={request.url}, error={e}")
```

不要在 `parse()` 里手写主重试循环；优先使用 `SPIDER_MAX_RETRY_TIMES`、`validate()`、`exception_request()` 和 `failed_request()`。

## Debug 模式

Spider：

```python
debug_spider = SpiderTest.to_DebugSpider(
    redis_key="feapder:spider",
    request=feapder.Request("https://example.com"),
)
debug_spider.start()
```

BatchSpider：

```python
debug_spider = BatchSpiderTest.to_DebugBatchSpider(
    task_id=1,
    redis_key="feapder:batch",
    task_table="batch_task",
    task_keys=["id", "url"],
    task_state="state",
    batch_record_table="batch_record",
    batch_name="batch test",
    batch_interval=1,
)
debug_spider.start()
```

Debug 模式默认通常不入库、不更新任务状态，除非显式配置。
Debug 模式适合调单个 request、`parse`、`validate`、`download_midware` 或单个批次任务；它不是生产全链路验证，不能替代 master/worker、队列、pipeline 和部署环境检查。
