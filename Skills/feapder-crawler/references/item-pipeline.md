# Item 和 Pipeline

`Item` / `UpdateItem` 是 parser `yield` 给 feapder 的数据对象，后续由 `ItemBuffer` 交给 `ITEM_PIPELINES` 处理。

## 标准项目默认写法

在标准 feapder 项目里，优先把数据模型放到 `items/`，不要把表名、字段和更新逻辑散落在 spider 的 `_build_xxx_item()` 私有方法里。

如果 MySQL 表已存在，进入项目的 `items/` 目录生成 item：

```bash
cd <project_root>/items
feapder create -i app_info
feapder create -i app_relations
```

字段很多或接口 JSON 与表字段基本一致时，可用支持 dict 赋值的模板：

```bash
feapder create -i app_info 1
```

生成后按需要改成 `UpdateItem`，并把表名、更新字段、去重字段放在 item 类上：

```python
from feapder import UpdateItem


class AppInfoItem(UpdateItem):
    __table_name__ = "app_info"
    __update_key__ = ["app_name", "app_type", "app_media", "app_icp", "app_company", "privacy_url", "source"]
    __unique_key__ = ["pkg_name"]

    def __init__(self, *args, **kwargs):
        self.pkg_name = None
        self.app_name = None
        self.app_type = None
        self.app_media = None
        self.app_icp = None
        self.app_company = None
        self.privacy_url = None
        self.source = None

    def pre_to_db(self):
        self.pkg_name = (self.pkg_name or "").strip()
        self.app_name = (self.app_name or "").strip()
```

spider 中只负责解析和赋值：

```python
from items.app_info_item import AppInfoItem
from items.app_relations_item import AppRelationsItem


def parse_yyb(self, request, response):
    info = self.extract_app_info(response)

    item = AppInfoItem()
    item.pkg_name = info.get("pkg_name")
    item.app_name = info.get("app_name")
    item.app_type = info.get("app_type")
    item.app_media = info.get("app_media")
    item.app_icp = info.get("app_icp")
    item.app_company = info.get("app_company")
    item.privacy_url = info.get("privacy_url")
    item.source = "yyb"
    yield item
```

关系表也应有自己的 item 类，不要在 spider 内动态拼：

```python
from feapder import Item


class AppRelationsItem(Item):
    __table_name__ = "app_relations"
    __unique_key__ = ["source_pkg", "target_pkg", "source_store"]

    def __init__(self, *args, **kwargs):
        self.source_pkg = None
        self.target_pkg = None
        self.source_store = None
```

使用：

```python
rel = AppRelationsItem()
rel.source_pkg = source_pkg
rel.target_pkg = target_pkg
rel.source_store = "yyb"
yield rel
```

## UpdateItem 和唯一索引

更新已有数据时使用 `UpdateItem`。MySQL 更新语义依赖表上的主键或唯一索引；仅在 item 上写 `__update_key__`，但数据库没有唯一索引，不能实现按业务键更新。

推荐把更新字段写在类上：

```python
from feapder import UpdateItem


class ProductItem(UpdateItem):
    __table_name__ = "product"
    __unique_key__ = ["product_id"]
    __update_key__ = ["name", "price", "shop_id"]

    def __init__(self, *args, **kwargs):
        self.product_id = None
        self.name = None
        self.price = None
        self.shop_id = None
```

对应表需要类似：

```sql
UNIQUE KEY uk_product_id (product_id)
```

已有 `Item` 也可以通过 `to_UpdateItem()` 转成更新对象，但标准项目里优先直接定义 `UpdateItem` 类。

## Item 去重指纹

Item 指纹默认由排序后的字段值计算 MD5。遇到采集时间、更新时间这类不应参与去重的字段时，要显式指定：

```python
class ProductItem(feapder.Item):
    __table_name__ = "product"
    __unique_key__ = ["product_id"]
```

也可运行时指定：

```python
item.unique_key = ["product_id"]
```

或者重写：

```python
@property
def fingerprint(self):
    return self.product_id
```

## Pipeline

CSV/MySQL/Mongo 保存的主路径是 `yield Item` 或 `yield UpdateItem` 进入 `ITEM_PIPELINES`。AI 不允许把主要方案写成 parser 里直接 `open()` / `csv.writer` 写 CSV 或直接拼 SQL；这些只适合临时脚本或自定义 pipeline 内部实现。若判断确实要绕过 `ITEM_PIPELINES`，必须先向用户说明原因、影响和替代方案，并明确请求用户授权。

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

## 只在轻量场景允许动态 Item

`feapder.Item()` / `feapder.UpdateItem()` 动态赋字段是官方允许的临时写法，但不要作为标准项目默认输出。

允许场景：

- 单文件 `AirSpider`。
- 临时验证字段或下载解析。
- 用户明确要求快速 demo，不创建标准项目结构。

动态写法示例：

```python
item = feapder.Item()
item.table_name = "spider_data"
item.title = title
yield item
```

反例，标准项目里不要默认这样写：

```python
def _build_app_info_item(pkg, info, source=""):
    item = feapder.UpdateItem()
    item.table_name = "app_info"
    item.update_key = "pkg_name"
    item.pkg_name = pkg
    item.app_name = info.get("app_name", "")
    return item
```

更好的写法是把 `AppInfoItem` 放到 `items/app_info_item.py`，spider 里只实例化和赋值。
