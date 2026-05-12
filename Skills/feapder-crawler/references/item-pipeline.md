# Item 和 Pipeline

## Item

`Item` 是 parser `yield` 给框架的数据对象，后续由 `ItemBuffer` 交给 pipeline 处理。

临时构造 item：

```python
item = feapder.Item()
item.table_name = "spider_data"
item.title = title
yield item
```

生成式 item：

```python
from feapder import Item


class SpiderDataItem(Item):
    def __init__(self, *args, **kwargs):
        self.title = None
```

使用：

```python
item = SpiderDataItem()
item.title = response.xpath("//title/text()").extract_first()
yield item
```

## Item 去重指纹

Item 指纹默认由排序后的字段值计算 MD5。遇到采集时间这类不应参与去重的字段时，要显式指定。

```python
class SpiderDataItem(feapder.Item):
    __unique_key__ = ["title", "url"]
```

也可运行时指定：

```python
item.unique_key = ["title", "url"]
```

或者重写：

```python
@property
def fingerprint(self):
    return self.url
```

## 入库前清洗

```python
def pre_to_db(self):
    self.title = self.title.strip()
```

## UpdateItem

更新已有数据时使用 `UpdateItem`。

```python
from feapder import UpdateItem


class SpiderDataItem(UpdateItem):
    def __init__(self, *args, **kwargs):
        self.id = None
        self.title = None


item = SpiderDataItem()
item.update_key = "id"
yield item
```

已有 `Item` 也可以通过 `to_UpdateItem()` 转成更新对象。

## Pipeline

在 `setting.py` 中配置 pipeline：
在 feapder 代码里，CSV/MySQL/Mongo 保存的主路径是 `yield Item` 或 `yield UpdateItem` 进入 `ITEM_PIPELINES`。AI 不允许把主要方案写成 parser 里直接 `open()` / `csv.writer` 写 CSV 或直接拼 SQL；这些只适合临时脚本或自定义 pipeline 内部实现。若判断确实要绕过 `ITEM_PIPELINES`，必须先向用户说明原因、影响和替代方案，并明确请求用户授权。
已有项目启用 CSV/MySQL/Mongo pipeline 时，先定位项目根和实际加载的 `setting.py`，在现有 `ITEM_PIPELINES` 中增量加入对应 pipeline，并补 `CSV_EXPORT_PATH` 等相关配置。不要只给孤立配置代码，也不要覆盖用户已有 pipeline。

```python
ITEM_PIPELINES = [
    "feapder.pipelines.mysql_pipeline.MysqlPipeline",
    # "feapder.pipelines.mongo_pipeline.MongoPipeline",
    # "feapder.pipelines.csv_pipeline.CsvPipeline",
    # "feapder.pipelines.console_pipeline.ConsolePipeline",
]
CSV_EXPORT_PATH = "data/csv"
```

单个 item 可以指定自己的 pipeline，覆盖全局流向：

```python
from feapder.pipelines.csv_pipeline import CsvPipeline


class SpiderDataItem(feapder.Item):
    __pipelines__ = [CsvPipeline()]
```

## 自定义 Pipeline

```python
from typing import Dict, List, Tuple
from feapder.pipelines import BasePipeline


class Pipeline(BasePipeline):
    def save_items(self, table, items: List[Dict]) -> bool:
        return True

    def update_items(self, table, items: List[Dict], update_keys=Tuple) -> bool:
        return True
```

保存失败时返回 `False`，这样 feapder 会重试，并且不会把这批数据标记为已成功去重。

pipeline 在配置里写模块路径，例如：

```python
ITEM_PIPELINES = ["pipeline.Pipeline"]
```
