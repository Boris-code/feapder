# 项目工作流

## CLI

feapder 内置 `feapder` 命令行工具。

用户要新建标准 feapder 项目时，默认使用生成器，不要手写目录和模板：

```bash
feapder create -p <project_name>
```

在已有标准项目里新增 spider 时，先定位项目根，再进入项目的 `spiders/` 目录运行 `-s`：

```bash
cd <project_root>/spiders
feapder create -s <spider_name>
```

不要在项目根直接执行 `feapder create -s <spider_name>`，否则生成位置可能不符合标准项目结构。也不要手写 spider 模板替代生成器，除非用户明确要求。

如果用户只要一个单文件、本地运行的轻量 `AirSpider`，可以不创建完整 `-p` 项目；可直接写单文件 `AirSpider`，或在目标目录执行 `feapder create -s <spider_name>` 生成单 spider 模板，并说明它不包含标准项目的 `setting.py/main.py/items/spiders` 结构。

常用命令：

```bash
feapder create -p my-project
feapder create -s my_spider
feapder create -i table_name
feapder create -t table_name
feapder create --setting
feapder create -j
feapder create -sj
feapder shell
feapder zip
```

`feapder create -p` 生成的典型项目结构：

```text
my-project/
├── items/
├── spiders/
├── main.py
└── setting.py
```

## 启动入口

简单爬虫可以直接运行 spider 文件。复杂项目通常把启动入口收敛到 `main.py`，并用 `feapder.ArgumentParser` 管理命令行参数。

典型 `main.py`：

```python
from feapder import ArgumentParser
from spiders import *


def crawl_news():
    spider = news_spider.NewsSpider(redis_key="feapder:news")
    spider.start()


if __name__ == "__main__":
    parser = ArgumentParser(description="crawler")
    parser.add_argument("--crawl_news", action="store_true", help="crawl news", function=crawl_news)
    parser.start()
```

`BatchSpider` 常见做法是暴露数字模式：

```python
def crawl_batch(args):
    spider = product_spider.ProductSpider(...)
    if args == 1:
        spider.start_monitor_task()
    elif args == 2:
        spider.start()
    elif args == 3:
        spider.init_task()
```

## 生成 Item

`feapder create -i table_name` 会读取 MySQL 表结构并生成 `Item` 类。数据库配置可以来自 `setting.py`、环境变量或命令行参数：

```bash
feapder create -i spider_data --host localhost --db feapder --username feapder --password feapder123
```

字段很多或接口返回 JSON 较完整时，可以选择支持 dict 赋值的 Item 模板。

## 维护现有项目时的阅读顺序

1. 先读 `main.py`，确认真实命令和 spider 构造参数。
2. 再读 `setting.py`，确认 Redis、MySQL、pipeline、线程、重试、渲染、代理、去重和日志配置。
3. 读目标 `spiders/` 文件。
4. 读 `items/` 文件。
5. 读自定义 pipeline 模块。
6. 搜索同类型测试或示例。

如果当前工作目录不确定或不在项目根，先通过这些信号定位项目根：

- `main.py`
- `setting.py`
- `spiders/`
- `items/`
- `requirements.txt` / `pyproject.toml` 中的 `feapder` 依赖

确认项目根后，再编辑配置或进入 `spiders/` 执行生成命令。
