---
name: feapder-crawler
description: 当用户要使用、生成、维护、审查或排查基于 feapder 框架的 Python 爬虫时使用；如果用户正在做 feapder 项目、要求用 feapder、安装/配置 feapder，或当前工作区代码/依赖已显示在使用 feapder，即使用户没再次说 feapder，只要在讨论分布式爬虫、断点续爬、批次采集、任务表消费、自动入库、Request/Response、Item/Pipeline、浏览器渲染、代理/去重、CLI 项目模板、运行时配置或 feapder.utils.tools 小工具，也要使用。若用户明确指定 Scrapy、requests-only、Playwright-only、FastAPI、Celery 等非 feapder 技术栈，则不要使用，除非任务是迁移到 feapder、对比 feapder，或用户明确要求改用这些技术。
metadata:
  short-description: Build and debug feapder crawlers
---

# Feapder Crawler

这个 Skill 用于处理 feapder 爬虫相关工作：创建爬虫、选择爬虫类型、接入任务队列、解析响应、保存数据、配置运行环境，或诊断现有 feapder 项目。

## 第一轮判断

1. 先判断用户是在创建新爬虫、修改现有爬虫、排查运行问题、设计采集架构，还是配置入库/渲染/部署。
2. 如果是现有项目，先读真实入口，不要只按印象判断：
   - `setting.py`
   - `main.py`
   - `spiders/`
   - `items/`
   - 自定义 pipeline 模块
   - tests 或示例爬虫
3. 如果当前目录不确定或不在项目根，先通过 `main.py`、`setting.py`、`spiders/`、`items/`、`requirements.txt` / `pyproject.toml` 中的 feapder 依赖定位项目根；确认项目根后再编辑配置或运行生成命令。
4. 确认实际运行方式：
   - 直接运行爬虫脚本
   - `main.py` + `ArgumentParser`
   - TaskSpider 或 BatchSpider 的 master/worker 分离
   - feaplat 托管部署
5. 配置优先级按这个顺序判断：爬虫类 `__custom_setting__` > 项目 `setting.py` > 环境变量 > `feapder/setting.py` 默认值。
6. “feapder 项目上下文”不等于必须在 feapder 源码仓库里；用户可能在新文件夹、业务项目或空目录里创建 feapder 爬虫。只要用户要求用 feapder，或项目依赖/代码形态显示正在使用 feapder，就按 feapder 工作流处理。

## 爬虫类型选择

- 小型、单机、无需 Redis、无需分布式和断点续爬：用 `AirSpider`。
- Redis 分布式、断点续爬、自动 item 缓冲、失败状态和大任务队列：用 `Spider`。
- 种子任务来自 Redis/MySQL 或其他任务源，且需要区分任务下发与 worker 消费：用 `TaskSpider`。
- 周期性批次采集，任务状态和批次记录必须落 MySQL：用 `BatchSpider`。
- 多数据源共用一个 Spider 调度：用 `BaseParser` + `Spider.add_parser()`。
- 多数据源共用一个 BatchSpider 批次调度：用 `BatchParser` + `BatchSpider.add_parser()`，任务行里要能标识 parser。

详细取舍和示例见 `references/spider-selection.md`。

## 按场景读取

- 新项目、CLI、项目结构和启动入口：读 `references/project-workflow.md`。
- Request callback、中间件、校验、Response 提取：读 `references/request-response.md`。
- Item、UpdateItem、数据库写入、CSV/MySQL/Mongo/custom pipeline：读 `references/item-pipeline.md`。
- settings、Redis/MySQL/Mongo、重试、日志、报警、任务丢失、缓存：读 `references/settings-runtime.md`。
- TaskSpider 和 BatchSpider 的 master/worker 流程：读 `references/batch-task-spider.md`。
- 多 parser 集成：读 `references/parser-integration.md`。
- feaplat 部署/平台运行定位：读 `references/feaplat-deploy.md`。
- 浏览器渲染、Playwright/Selenium、代理、UA、去重：读 `references/rendering-proxy-dedup.md`。
- feapder 自带小工具，如 cookies、URL、HTML、JSON、时间、hash、SQL、报警、CLI shell、文件工具：读 `references/utilities.md`。
- 需要对源码做定位或验证时：读 `references/source-map.md`。

## 实施规则

- 优先使用 feapder 生成器和项目现有模式，不要手写一套不一致的脚手架。
- 用户要新建标准 feapder 项目时，默认使用 `feapder create -p <project_name>` 生成项目结构，不要手写目录和模板；只有用户明确要求单文件脚本或自定义结构时才例外。
- 在已有 feapder 标准项目里新增 spider 时，先定位项目根，再进入 `<project_root>/spiders/` 执行 `feapder create -s <spider_name>`；不要在项目根直接执行 `-s`，也不要手写模板替代生成器，除非用户明确要求。
- 已有项目新增或调整 Redis/MySQL/代理/线程/重试/渲染/pipeline 配置时，优先修改项目实际加载的 `setting.py`；只有配置确实只属于单个 spider，或项目已有模式使用 `__custom_setting__`，才放进 spider 类的 `__custom_setting__`。修改时增量合并用户已有配置，不要覆盖。
- 用户明确要求 feapder 或当前项目使用 feapder 时，示例代码默认必须继承 feapder 的 Spider 类，并使用 `feapder.Request`、`feapder.Response`、`Item` / `UpdateItem`、`ITEM_PIPELINES` 等框架路径；AI 不允许自行退化成纯 `requests`、`Scrapy`、独立 Playwright、手写 CSV 或直接 SQL。若你判断确实需要脱离 feapder 路径，必须先向用户说明原因、影响和替代方案，并明确请求用户授权；用户确认前不要写非 feapder 实现。
- 用户询问“要不要脱离 feapder”“改成 requests 怎么样”这类方案判断时，只能先做风险/收益评估和替代方案说明；这不等于授权实现。只有用户明确确认“就改成非 feapder 实现”后，才可以写非 feapder 代码。
- 不要假设 `AirSpider` 的配置行为等同于 Redis 分布式爬虫；先确认基类和启动参数。
- 对 `BatchSpider` / `TaskSpider`，必须区分任务下发 `start_monitor_task()` 和 worker 采集 `start()`。
- 排查入库问题时，沿着 `yield Item` 或 `yield UpdateItem` 追到 `ITEM_PIPELINES`，再看具体 pipeline 和配置。
- 排查解析问题时，先看 `Request.callback`、`parser_name`、`download_midware`、`validate`、`exception_request`、`failed_request`，不要急着改 scheduler。
- 遇到 import/path 问题时，记住 feapder 从 `items/` 或 `spiders/` 启动时会把项目根目录插入 `sys.path`。
- 做 PR 级别改动时，用最小相关测试或可运行示例验证，避免无关重构。

## 高信号源码

- `feapder/__init__.py`：公开 API 导出和导入路径行为。
- `feapder/core/base_parser.py`：parser 生命周期钩子。
- `feapder/core/spiders/`：AirSpider、Spider、TaskSpider、BatchSpider。
- `feapder/network/request.py`：Request 参数、重试、渲染标记、缓存辅助。
- `feapder/network/response.py`：xpath/css/re/json/bs4 提取和编码处理。
- `feapder/network/item.py`：Item、UpdateItem、表名、指纹、单 item pipeline。
- `feapder/pipelines/`：内置 pipeline 行为。
- `feapder/utils/tools.py`：cookies、URL、JSON、日期、SQL、hash、文件、JS、报警和常见转换工具。
- `feapder/commands/shell.py`：基于 `Request` 的 cURL/URL 响应调试器。
- `feapder/setting.py`：默认运行时配置全集。
- `feapder/commands/`：CLI 生成器。
