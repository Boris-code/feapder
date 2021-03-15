# UpdateItem

UpdateItem用于更新数据，继承至Item，所以使用方式基本与Item一致，下载只说不同之处

## 更新逻辑

更新逻辑借助了数据库的唯一索引，即插入数据时发现数据已存在，则更新。因此要求数据表必须存在唯一索引，才能使用UpdateItem

比如将title设置唯一，要求每条数据的title都不能重复

![-w781](media/16158245077159.jpg)

或联合索引，要求title与url不能同时重复

![-w761](media/16158245648750.jpg)


## 指定更新的字段

方式1：指定`__update_key__`

```python
from feapder import UpdateItem


class SpiderDataItem(UpdateItem):
    
    __update_key__ = ["title"] # 更新title字段

    def __init__(self, *args, **kwargs):
        # self.id = None
        self.title = None
        self.url = None
```

方式二：赋值`update_key`

```python
from feapder import UpdateItem


class SpiderDataItem(UpdateItem):


    def __init__(self, *args, **kwargs):
        # self.id = None
        self.title = None
        self.url = None

item = SpiderDataItem()
item.update_key = "title" # 支持列表、元组、字符串
```

方式三：将普通的item转为UpdateItem，然后再指定更新的key

```python
from feapder import Item


class SpiderDataItem(Item):


    def __init__(self, *args, **kwargs):
        # self.id = None
        self.title = None
        self.url = None

item = SpiderDataItem.to_UpdateItem()
item.update_key = "title"
```