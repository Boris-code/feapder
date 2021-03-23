# Dedup

Dedup是feapder大数据去重模块，不同于BloomFilter，去重受槽位数量影响，Dedup使用了弹性的去重机制，可容纳海量的数据去重。


## 去重方式

### 临时去重

> 基于redis，支持批量，去重有时效性。去重一万条数据约0.26秒，一亿条数据占用内存约1.43G

```python
from feapder.dedup import Dedup

data = {"xxx": 123, "xxxx": "xxxx"}
datas = ["xxx", "bbb"]

def test_ExpireFilter():
    dedup = Dedup(
        Dedup.ExpireFilter, expire_time=10, redis_url="redis://@localhost:6379/0"
    )

    # 逐条去重
    assert dedup.add(data) == 1
    assert dedup.get(data) == 1

    # 批量去重
    assert dedup.add(datas) == [1, 1]
    assert dedup.get(datas) == [1, 1]
```


### 内存去重

> 基于内存，支持批量。去重一万条数据约0.5秒，一亿条数据占用内存约285MB

```python
from feapder.dedup import Dedup

data = {"xxx": 123, "xxxx": "xxxx"}
datas = ["xxx", "bbb"]

def test_MemoryFilter():
    dedup = Dedup(Dedup.MemoryFilter)  # 表名为test 历史数据3秒有效期

    # 逐条去重
    assert dedup.add(data) == 1
    assert dedup.get(data) == 1

    # 批量去重
    assert dedup.add(datas) == [1, 1]
    assert dedup.get(datas) == [1, 1]
```

### 永久去重

> 基于redis，支持批量，永久去重。 去重一万条数据约3.5秒，一亿条数据占用内存约285MB

```python
from feapder.dedup import Dedup

def test_BloomFilter():
    dedup = Dedup(Dedup.BloomFilter, redis_url="redis://@localhost:6379/0")

    # 逐条去重
    assert dedup.add(data) == 1
    assert dedup.get(data) == 1

    # 批量去重
    assert dedup.add(datas) == [1, 1]
    assert dedup.get(datas) == [1, 1]
```

## 过滤数据

Dedup可以通过如下方法，过滤掉已存在的数据


```python
from feapder.dedup import Dedup

def test_filter():
    dedup = Dedup(Dedup.BloomFilter, redis_url="redis://@localhost:6379/0")

    # 制造已存在数据
    datas = ["xxx", "bbb"]
    dedup.add(datas)

    # 过滤掉已存在数据 "xxx", "bbb"
    datas = ["xxx", "bbb", "ccc"]
    dedup.filter_exist_data(datas)
    assert datas == ["ccc"]
```

## Dedup参数

- **filter_type**：去重类型，支持BloomFilter、MemoryFilter、ExpireFilter三种
- **redis_url**不是必须传递的，若项目中存在setting.py文件，且已配置redis连接方式，则可以不传递redis_url

    ![-w294](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/03/07/16151133801599.jpg)

    ```
    import feapder
    from feapder.dedup import Dedup

    class TestSpider(feapder.Spider):
        def __init__(self, *args, **kwargs):
            self.dedup = Dedup() # 默认是永久去重
    ```

- **name**: 过滤器名称 该名称会默认以dedup作为前缀 `dedup:expire_set:[name]`或`dedup:bloomfilter:[name]`。 默认ExpireFilter name=过期时间，BloomFilter name=`dedup:bloomfilter:bloomfilter`

 ![-w499](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/03/07/16151136442498.jpg)

 若对不同数据源去重，可通过name参数来指定不同去重库

- **absolute_name**：过滤器绝对名称 不会加dedup前缀
- **expire_time**：ExpireFilter的过期时间 单位为秒，其他两种过滤器不用指定
- **error_rate**：BloomFilter/MemoryFilter的误判率 默认为0.00001
- **to_md5**：去重前是否将数据转为MD5，默认是

## 爬虫中使用

框架支持对请求和入库的数据进行去重，仅需要在[配置文件](source_code/配置文件)中进行配置即可

```python
ITEM_FILTER_ENABLE = False # item 去重
REQUEST_FILTER_ENABLE = False # request 去重
```

或者可以直接导入此去重模块使用

```python
from feapder.dedup import Dedup
```

