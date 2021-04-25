# MongoDB



## 使用须知

- 使用`MongoDb`存储数据，需要使用`MongoPipeline`
- 暂不支持批次爬虫


## 连接

```python
from feapder.db.mongodb import MongoDB


db = MongoDB(
    ip="localhost", port=27017, db="feapder", user_name="feapder", user_pass="feapder123"
)
```

若环境变量中配置了数据库连接方式或者setting中已配置，则可不传参 

```python
db = MongoDB()
```
    
或者可以根据url连接

```python
db = MongoDB.from_url("mongodb://username:password@ip:port/db")
```
    
## 方法

> MysqlDB封装了增删改查等方法，方便使用

### 查

```python
def find(self, table, limit=0) -> List[Dict]:
    """
    @summary:
    无数据： 返回()
    有数据： 若limit == 1 则返回 (data1, data2)
            否则返回 ((data1, data2),)
    ---------
    @param table:
    @param limit:
    ---------
    @result:
    """
```
    

### 增

```python
def add(self, table, data, **kwargs):
    """

    Args:
        table:
        data:
        kwargs:
            auto_update: 自动更新，将替换替换重复数据，默认False
            update_columns: 如果数据存在，更新指定字段，否则插入整条数据
            insert_ignore: 如果数据存在，则跳过，默认为False，即不跳过
            condition_fields: 用于条件查找的字段，默认以`_id`作为查找条件，默认：['_id']
            exception_callfunc: 异常回调

    Returns: 添加行数

    """
```

```python
def add_smart(self, table, data: Dict, **kwargs):
    """
    添加数据, 直接传递json格式的数据，不用拼sql
    Args:
        table: 表名
        data: 字典 {"xxx":"xxx"}
        **kwargs:

    Returns: 添加行数

    """
    return self.add(table, data, **kwargs)
```


```python
def add_batch(self, table: str, datas: List[Dict], **kwargs):
    """
    @summary: 批量添加数据
    ---------
    @param command: 字典
    @param datas: 列表 [[..], [...]]
    @param **kwargs:
        auto_update: 自动更新，将替换替换重复数据，默认False
        update_columns: 如果数据存在，更新指定字段，否则插入整条数据
        update_columns_value: 指定字段对应的值
        condition_fields: 用于条件查找的字段，默认以`_id`作为查找条件，默认：['_id']
    ---------
    @result: 添加行数
    """
```

```python
def add_batch_smart(self, table, datas: List[Dict], **kwargs):
    """
    批量添加数据, 直接传递list格式的数据，不用拼sql
    Args:
        table: 表名
        datas: 列表 [[..], [...]]
        **kwargs:
            auto_update: 自动更新，将替换替换重复数据，默认False
            update_columns: 如果数据存在，更新指定字段，否则插入整条数据
            update_columns_value: 指定字段对应的值
            condition_fields: 用于条件查找的字段，默认以`_id`作为查找条件，默认：['_id']
    Returns: 添加行数

    """
    if not datas:
        return
    return self.add_batch(table, datas, **kwargs)
```

### 更新

```python
def update(self, table, data: Dict, condition: Dict):
    try:
        collection = self.get_collection(table)
        collection.update_one(condition, {'$set': data})
    except Exception as e:
        log.error(
            """
            error:{}
            condition: {}
        """.format(e, condition)
        )
        return False
    else:
        return True
```

```python
def update_smart(self, table, data: Dict, condition: Dict):
    """
    更新
    Args:
        table: 表名
        data: 数据 {"xxx":"xxx"}
        condition: 更新条件 {"_id": "xxxx"}

    Returns: True / False
    """
    return self.update(table, data, condition)
```

### 删除

```python
def delete(self, table, condition: Dict):
    """
    删除
    Args:
        table:
        condition: 查找条件
    Returns: True / False

    """
    try:
        collection = self.get_collection(table)
        collection.delete_one(condition)
    except Exception as e:
        log.error(
            """
            error:{}
            condition: {}
        """.format(e, condition)
        )
        return False
    else:
        return True
```
