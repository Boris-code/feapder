# 源码地图

当文档不足或需要核对真实行为时，按这个地图查源码。

## 公开 API

- `feapder/__init__.py`
  - 导出 `AirSpider`、`Spider`、`TaskSpider`、`BatchSpider`、`BaseParser`、`TaskParser`、`BatchParser`、`Request`、`Response`、`Item`、`UpdateItem`、`ArgumentParser`。
  - 当当前工作目录以 `items` 或 `spiders` 结尾时，会把项目根目录插入 `sys.path`。

## Parser 生命周期

- `feapder/core/base_parser.py`
  - `BaseParser`：`start_requests`、`download_midware`、`validate`、`parse`、`exception_request`、`failed_request`、`start_callback`、`end_callback`。
  - `TaskParser`：任务状态辅助方法，包括批量更新任务状态。
  - `BatchParser`：批次时间和批次 parser 行为。

## Spider 运行时

- `feapder/core/spiders/air_spider.py`：轻量本地调度。
- `feapder/core/spiders/spider.py`：Redis 分布式爬虫。
- `feapder/core/spiders/task_spider.py`：任务源型爬虫。
- `feapder/core/spiders/batch_spider.py`：批次调度和任务状态流转。
- `feapder/core/scheduler.py`：通用调度行为、parser 注册、生命周期、状态、心跳、失败状态。
- `feapder/core/collector.py`：从队列抓取 request 到内存。
- `feapder/core/parser_control.py`：downloader 和 parser callback 调度。
- `feapder/buffer/request_buffer.py`：批量写入 request 队列。
- `feapder/buffer/item_buffer.py`：批量处理 item、pipeline 和任务更新。

## 网络模型

- `feapder/network/request.py`：request 对象、框架参数、指纹/缓存辅助、downloader 调度。
- `feapder/network/response.py`：response 封装、编码、绝对链接、xpath/css/re/json/bs4。
- `feapder/network/selector.py`：selector 封装。
- `feapder/network/downloader/`：requests、session、Selenium、Playwright downloader。
- `feapder/network/proxy_pool/`：当前代理池。
- `feapder/network/user_pool/`：guest/normal/gold 用户池。

## 数据模型

- `feapder/network/item.py`：`Item`、`UpdateItem`、表名、`to_dict`、SQL 转换、unique keys、单 item pipelines。
- `feapder/pipelines/__init__.py`：`BasePipeline` 接口。
- `feapder/pipelines/mysql_pipeline.py`：MySQL save/update。
- `feapder/pipelines/mongo_pipeline.py`：Mongo save/update。
- `feapder/pipelines/csv_pipeline.py`：CSV save/update、字段缓存、路径处理。
- `feapder/pipelines/console_pipeline.py`：控制台输出 pipeline。

## 配置

- `feapder/setting.py`：Redis、MySQL、Mongo、pipeline、并发、重试、浏览器渲染、缓存、代理、去重、报警、日志默认值。
- `feapder/templates/project_template/setting.py`：项目生成器使用的配置模板。

## CLI

- `feapder/commands/cmdline.py`：顶层 CLI。
- `feapder/commands/create/`：project、spider、item、table、settings、cookies、params、JSON 生成器。
- `feapder/commands/shell.py`：响应调试。
- `feapder/commands/retry.py`：失败 request/item 重试辅助。
- `feapder/commands/zip.py`：项目打包。

## 测试和示例

- `tests/spider/`：标准 Spider 示例。
- `tests/air-spider/`：AirSpider 示例。
- `tests/batch-spider/`：BatchSpider 示例。
- `tests/spider-integration/`：Spider parser 集成。
- `tests/batch-spider-integration/`：BatchSpider parser 集成。
- `tests/test-pipeline/`：自定义和 CSV pipeline 示例。
- `tests/test_csv_pipeline/`：CSV pipeline 行为和性能测试。
