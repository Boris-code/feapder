# Parser 集成

当多个站点或多个解析器共享一个调度器时，用 feapder 的 parser 集成。不要为每个站点都复制一套完整 Spider，除非它们的运行周期、队列、配置和部署都确实独立。

## Spider + BaseParser

解析器继承 `feapder.BaseParser`，调度器使用 `Spider.add_parser()` 注册。

```python
import feapder


class SinaNewsParser(feapder.BaseParser):
    def start_requests(self):
        yield feapder.Request("https://news.sina.com.cn/")

    def parse(self, request, response):
        item = feapder.Item()
        item.table_name = "news"
        item.source = "sina"
        item.title = response.xpath("//title/text()").extract_first()
        yield item


class TencentNewsParser(feapder.BaseParser):
    def start_requests(self):
        yield feapder.Request("https://news.qq.com/")

    def parse(self, request, response):
        item = feapder.Item()
        item.table_name = "news"
        item.source = "tencent"
        item.title = response.xpath("//title/text()").extract_first()
        yield item


if __name__ == "__main__":
    spider = feapder.Spider(redis_key="feapder:news")
    spider.add_parser(SinaNewsParser)
    spider.add_parser(TencentNewsParser)
    spider.start()
```

跨 parser 指定回调时，`Request` 可以带 `parser_name` 和 callback 名称：

```python
yield feapder.Request(
    detail_url,
    parser_name="TencentNewsParser",
    callback="parse_detail",
)
```

## BatchSpider + BatchParser

批次集成时，解析器继承 `feapder.BatchParser`。任务表需要有一个字段标识这条任务应该分发到哪个 parser，常见字段名是 `parser_name`。

```python
import feapder


class SinaBatchParser(feapder.BatchParser):
    def start_requests(self, task):
        task_id, url, parser_name = task
        yield feapder.Request(url, task_id=task_id)

    def parse(self, request, response):
        item = feapder.Item()
        item.table_name = "news"
        item.source = "sina"
        item.title = response.xpath("//title/text()").extract_first()
        yield item
        yield self.update_task_batch(request.task_id, 1)


class TencentBatchParser(feapder.BatchParser):
    def start_requests(self, task):
        task_id, url, parser_name = task
        yield feapder.Request(url, task_id=task_id)

    def parse(self, request, response):
        item = feapder.Item()
        item.table_name = "news"
        item.source = "tencent"
        item.title = response.xpath("//title/text()").extract_first()
        yield item
        yield self.update_task_batch(request.task_id, 1)


def create_spider():
    spider = feapder.BatchSpider(
        task_table="news_task",
        task_keys=["id", "url", "parser_name"],
        task_state="state",
        batch_record_table="news_batch_record",
        batch_name="news batch",
        batch_interval=1,
        redis_key="feapder:news_batch",
    )
    spider.add_parser(SinaBatchParser)
    spider.add_parser(TencentBatchParser)
    return spider
```

## 排查要点

- 确认 parser 类继承的是 `BaseParser` 或 `BatchParser`，不是完整 `Spider` / `BatchSpider`。
- 确认 `add_parser()` 注册了所有 parser 类。
- Batch 集成必须确认任务表字段能标识 parser。
- 跨 parser 回调时检查 `parser_name` 和 callback 名称是否匹配。
- `AirSpider` 不支持这种 parser 集成方式。
