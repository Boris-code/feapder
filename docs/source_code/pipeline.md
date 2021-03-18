# Pipeline

Pipeline是数据入库时流经的管道，默认为使用mysql入库，用户可自定义，以便对接其他数据库。

注：AirSpider不支持

## 使用方式

### 1. 编写pipeline

```python
from feapder.pipelines import BasePipeline
from typing import Dict, List, Tuple


class Pipeline(BasePipeline):
    """
    pipeline 是单线程的，批量保存数据的操作，不建议在这里写网络请求代码，如下载图片等
    """

    def save_items(self, table, items: List[Dict]) -> bool:
        """
        保存数据
        Args:
            table: 表名
            items: 数据，[{},{},...]

        Returns: 是否保存成功 True / False
                 若False，不会将本批数据入到去重库，以便再次入库

        """

        print("自定义pipeline， 保存数据 >>>>", table, items)

        return True

    def update_items(self, table, items: List[Dict], update_keys=Tuple) -> bool:
        """
        更新数据, 与UpdateItem配合使用，若爬虫中没使用UpdateItem，则可不实现此接口
        Args:
            table: 表名
            items: 数据，[{},{},...]
            update_keys: 更新的字段, 如 ("title", "publish_time")

        Returns: 是否更新成功 True / False
                 若False，不会将本批数据入到去重库，以便再次入库

        """

        print("自定义pipeline， 更新数据 >>>>", table, items, update_keys)

        return True
```

`Pipeline`需继承`BasePipeline`，类名和存放位置随意，需要实现`save_items`接口。一定要有返回值，返回`False`表示数据没保存成功，数据不入去重库，以便再次入库

`update_items`接口与`UpdateItem`配合使用，更新数据时使用，若爬虫中没使用UpdateItem，则可不实现此接口

### 2. 编写配置文件

```python
# 数据入库的pipeline，支持多个
ITEM_PIPELINES = [
    "pipeline.Pipeline"
]
``` 

将编写好的pipeline配置进来，值为类的模块路径，需要指定到具体的类名

## 示例

地址：https://github.com/Boris-code/feapder/tree/master/tests/test-pipeline