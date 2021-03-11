# Dedup

Dedup是feapder大数据去重模块，内置3种去重机制，使用方式一致，可容纳的去重数据量与内存有关。不同于BloomFilter，去重受槽位数量影响，Dedup使用了弹性的去重机制，可容纳海量的数据去重。


## 去重方式

### 临时去重

> 基于redis，支持批量，去重有时效性。去重一万条数据约0.26秒，一亿条数据占用内存约1.43G

```
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

```
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

    from feapder.dedup import Dedup

    datas = {
        "xxx": xxx,
        "xxxx": "xxxx",
    }

    dedup = Dedup()

    print(dedup) # <ScalableBloomFilter: RedisBitArray: dedup:bloomfilter:bloomfilter>
    print(dedup.add(datas)) # 0 不存在
    print(dedup.get(datas)) # 1 存在
    
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


