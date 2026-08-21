# 爬虫类型选择

feapder 的几类爬虫共用一套解析模型：`start_requests`、`parse`、`Request`、`Response`、`Item` 和 parser 钩子整体一致。真正的差异在运行状态、任务来源和是否需要批次管理。

## 选择 AirSpider

适合这些情况：

- 爬虫是小脚本或本地工具。
- 不需要 Redis 任务队列。
- 不需要分布式、断点续爬或强状态任务恢复。
- 用户要最快上手。

如果用户只要一个单文件、本地运行的轻量 `AirSpider`，可以不创建完整 `feapder create -p` 项目；直接写单文件，或在目标目录执行 `feapder create -s <spider_name>` 生成单 spider 模板。要说明这种方式不包含标准项目的 `setting.py/main.py/items/spiders` 结构。

典型结构：

```python
import feapder


class DemoSpider(feapder.AirSpider):
    def start_requests(self):
        yield feapder.Request("https://example.com")

    def parse(self, request, response):
        print(response.xpath("//title/text()").extract_first())


if __name__ == "__main__":
    DemoSpider(thread_count=5).start()
```

## 选择 Spider

适合这些情况：

- 有 Redis，任务需要在重启后继续。
- 多进程或多机器消费同一个队列。
- item 需要经过 `ItemBuffer` 自动批量入库。
- 失败请求、重试状态、任务防丢比较重要。

典型结构（标准项目里优先使用 `items/` 下的生成式 Item 类）：

```python
from items.news_item import NewsItem


class NewsSpider(feapder.Spider):
    __custom_setting__ = {
        "REDISDB_IP_PORTS": "localhost:6379",
        "REDISDB_DB": 0,
    }

    def start_requests(self):
        yield feapder.Request("https://news.example.com")

    def parse(self, request, response):
        yield feapder.Request("https://news.example.com/detail", callback=self.parse_detail)

    def parse_detail(self, request, response):
        item = NewsItem()
        item.title = response.xpath("//h1/text()").extract_first()
        yield item


NewsSpider(redis_key="feapder:news").start()
```

## 选择 TaskSpider

当种子任务由任务源管理，而不是只靠代码里的 `start_requests` 生产时，用 `TaskSpider`。

- `start_monitor_task()` 负责下发和监控种子任务。
- `start()` 负责 worker 消费请求。
- `add_task()` 可在 master 阶段塞种子任务。
- 任务行可来自 MySQL 或 Redis。

适合长驻任务消费、外部种子源、任务下发与 worker 分离的系统。

## 选择 BatchSpider

当每次采集都属于某个周期批次，且任务完成状态必须记录在 MySQL 时，用 `BatchSpider`。

核心概念：

- `task_table`：MySQL 任务种子表。
- `task_keys`：从任务表读取并传给 `start_requests(self, task)` 的字段。
- `task_state`：任务状态字段，常见约定是 `0` 待抓取、`1` 完成、`2` 抓取中、`-1` 无效或失败。
- `batch_record_table`：批次记录表，由框架创建或维护。
- `batch_interval`：批次周期，单位是天；小时级可写成 `1 / 24`。

运行方式：

- master：`spider.start_monitor_task()`
- worker：`spider.start()`
- 可选重置/初始化：`spider.init_task()`

## Parser 集成

当一个调度器需要管理多个数据源时，使用 parser 集成。

- `Spider` 集成时，解析器继承 `feapder.BaseParser`，再通过 `spider.add_parser(ParserClass)` 注册。
- `BatchSpider` 集成时，解析器继承 `feapder.BatchParser`，任务行中要包含 parser 类名/名称字段，再通过 `add_parser` 注册。
- `AirSpider` 不支持这种集成方式。

## 反例

- 需要 Redis 分布式、断点续爬或多机器消费时，不要选 `AirSpider`。
- 需要周期批次、MySQL 任务状态和批次记录时，不要用普通 `Spider` 代替 `BatchSpider`。
- 用户明确说 feapder 时，不要把“小爬虫”自动写成 `requests + BeautifulSoup`；如果 AI 判断必须这么做，先说明原因、影响、替代方案，并明确请求用户授权。
- 用户只是询问“脱离 feapder 是否更好”时，只做方案评估，不要直接写非 feapder 代码；等用户明确确认后再实现。
- 页面需要 JS 渲染且仍在 feapder 方案内时，不要直接跳到独立 Playwright；先用 `Request(render=True)` 和渲染配置。AI 要脱离 feapder 时必须先请求用户授权。
- 要 CSV/MySQL/Mongo 入库时，不要绕过 `Item` / `ITEM_PIPELINES` 写手动保存逻辑。AI 要绕过时必须先请求用户授权。
