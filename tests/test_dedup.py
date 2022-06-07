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


def test_BloomFilter():
    dedup = Dedup(Dedup.BloomFilter, redis_url="redis://@localhost:6379/0")

    # 逐条去重
    assert dedup.add(data) == 1
    assert dedup.get(data) == 1

    # 批量去重
    assert dedup.add(datas) == [1, 1]
    assert dedup.get(datas) == [1, 1]


def test_filter():
    dedup = Dedup(Dedup.BloomFilter, redis_url="redis://@localhost:6379/0")

    # 制造已存在数据
    datas = ["xxx", "bbb"]
    dedup.add(datas)

    # 过滤掉已存在数据 "xxx", "bbb"
    datas = ["xxx", "bbb", "ccc"]
    dedup.filter_exist_data(datas)
    assert datas == ["ccc"]

def test_ScalableBloomFilter():
    dedup = Dedup(Dedup.BloomFilter, redis_url="redis://@localhost:6379/0", initial_capacity=10)
    for i in range(1000):
        print(dedup.add(i))

test_ScalableBloomFilter()