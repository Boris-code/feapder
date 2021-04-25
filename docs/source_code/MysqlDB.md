# MysqlDB

MysqlDB具有断开自动重连特性，支持多线程下操作，内置连接池，最大连接数100

## 连接

```python
from feapder.db.mysqldb import MysqlDB


db = MysqlDB(
    ip="localhost", port=3306, db="feapder", user_name="feapder", user_pass="feapder123"
)
```

若环境变量中配置了数据库连接方式或者setting中已配置，则可不传参 

```python
db = MysqlDB()
```
    
或者可以根据url连接

```python
db = MysqlDB.from_url("mysql://username:password@ip:port/db?charset=utf8mb4")
```
    
## 方法

> MysqlDB封装了增删改查等方法，方便使用

### 查

```python
def find(self, sql, limit=0, to_json=False):
    """
    @summary:
    无数据： 返回()
    有数据： 若limit == 1 则返回 (data1, data2)
            否则返回 ((data1, data2),)
    ---------
    @param sql:
    @param limit:
    @param to_json 是否将查询结果转为json
    ---------
    @result:
    """
```
    

### 增

```python
def add(self, sql, exception_callfunc=None):
    """
    Args:
        sql:
        exception_callfunc: 异常回调

    Returns:添加行数

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

    Returns:添加行数

    """
```


```python
def add_batch(self, sql, datas: List[Dict]):
    """
    @summary: 批量添加数据
    ---------
    @ param sql: insert ignore into (xxx, xxx) values (%s, %s, %s)
    @ param datas: 列表 [{}, {}, {}]
    ---------
    @result:添加行数
    """
```

```python
def add_batch_smart(self, table, datas: List[Dict], **kwargs):
    """
    批量添加数据, 直接传递list格式的数据，不用拼sql
    Args:
        table: 表名
        datas: 列表 [{}, {}, {}]
        **kwargs:

    Returns: 添加行数

    """
```

### 更新

```python
def update(self, sql):
    pass
```

```python
def update_smart(self, table, data: Dict, condition):
    """
    更新, 不用拼sql
    Args:
        table: 表名 
        data: 数据 {"xxx":"xxx"}
        condition: 更新条件 where后面的条件，如 condition='status=1'

    Returns: True / False
    
    """
```

### 删除

```python
def delete(self, sql):
    """
    删除
    Args:
        sql: 

    Returns: True / False

    """
```

### 执行其他sql

```python
def execute(self, sql):
    pass
```