# MongoDB

## 数据自动入Mongo库使用须知

- 使用`MongoDb`存储数据，需要使用`MongoPipeline`

示例:

```python
import feapder
from feapder import Item


class TestMongo(feapder.AirSpider):
    __custom_setting__ = dict(
        ITEM_PIPELINES=["feapder.pipelines.mongo_pipeline.MongoPipeline"],
        MONGO_IP="localhost",
        MONGO_PORT=27017,
        MONGO_DB="feapder",
        MONGO_USER_NAME="",
        MONGO_USER_PASS="",
    )

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com")

    def parse(self, request, response):
        title = response.xpath("//title/text()").extract_first()  # 取标题
        item = Item()  # 声明一个item
        item.table_name = "test_mongo" # 指定存储的表名
        item.title = title  # 给item属性赋值
        yield item  # 返回item， item会自动批量入库


if __name__ == "__main__":
    TestMongo().start()
```


## 直接使用

### 连接

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
    
### 方法

> MongoDB封装了增删改查等方法，方便使用

#### 查

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
    

#### 增

```python
def add(self, table, data, **kwargs):
    """

    Args:
        table:
        data:
        kwargs:
            auto_update: 覆盖更新，将替换唯一索引重复的数据，默认False
            update_columns: 更新指定的列（如果数据的唯一索引存在，则更新指定字段，如 update_columns = ["name", "title"]
            insert_ignore: 唯一索引冲突时是否忽略，默认为False
            condition_fields: 用于条件查找的字段，默认以`_id`作为查找条件，默认：['_id']
            exception_callfunc: 异常回调

    Returns: 添加行数

    """
```

```python
def add_batch(self, table: str, datas: List[Dict], **kwargs):
    """
    @summary: 批量添加数据
    ---------
    @param command: 字典
    @param datas: 列表 [[..], [...]]
    @param **kwargs:
        auto_update: 覆盖更新，将替换唯一索引重复的数据，默认False
        update_columns: 更新指定的列（如果数据的唯一索引存在，则更新指定字段，如 update_columns = ["name", "title"]
        update_columns_value: 指定更新的字段对应的值
        condition_fields: 用于条件查找的字段，默认以`_id`作为查找条件，默认：['_id']
    ---------
    @result: 添加行数
    """
```

#### 更新

```python
def update(self, coll_name, data: Dict, condition: Dict, upsert: bool = False):
    """
    更新
    Args:
        coll_name: 集合名
        data: 单条数据 {"xxx":"xxx"}
        condition: 更新条件 {"_id": "xxxx"}
        upsert: 数据不存在则更新,默认为 False

    Returns: True / False
    """
```

#### 删除

```python
def delete(self, table, condition: Dict):
    """
    删除
    Args:
        table:
        condition: 查找条件
    Returns: True / False
    """
```
