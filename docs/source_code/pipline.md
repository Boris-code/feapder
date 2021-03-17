# Pipline

Pipline是数据入库时流经的管道，默认为使用mysql入库，用户可自定义。

注：AirSpider不支持

## 使用方式

### 1. 编写pipline

```python
from feapder.piplines import BasePipline
from typing import Dict, List, Tuple


class Pipline(BasePipline):
    """
    pipline 是单线程的，批量保存数据的操作，不建议在这里写网络请求代码，如下载图片等
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

        print("自定义pipline， 保存数据 >>>>", table, items)

        return True

    def update_items(self, table, items: List[Dict], update_keys=Tuple) -> bool:
        """
        更新数据
        Args:
            table: 表名
            items: 数据，[{},{},...]
            update_keys: 更新的字段字段, 如 ("title", "publish_time")

        Returns: 是否更新成功 True / False
                 若False，不会将本批数据入到去重库，以便再次入库

        """

        print("自定义pipline， 更新数据 >>>>", table, items, update_keys)

        return True
```

`Pipline`需继承`BasePipline`，类名和存放位置随意，需要实现`save_items`、`update_items`两个接口。一定要有返回值，返回`False`表示数据没保存成功，数据不入去重库，以便再次入库

### 2. 编写配置文件

```python
# 数据入库的pipline，可自定义，默认MysqlPipline
ITEM_PIPLINES = [
    "pipline.Pipline"
]
``` 

将编写好的pipline配置进来，值为类的模块路径，需要指定到具体的类名

## 示例

地址：