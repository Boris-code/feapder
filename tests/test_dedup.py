import unittest

from redis import Redis

from feapder.dedup import Dedup


class TestDedup(unittest.TestCase):
    def clear(self):
        self.absolute_name = "test_dedup"
        redis = Redis.from_url("redis://@localhost:6379/0", decode_responses=True)
        keys = redis.keys(self.absolute_name + "*")
        if keys:
            redis.delete(*keys)

    def setUp(self) -> None:
        self.clear()
        self.mock_data()

    def tearDown(self) -> None:
        self.clear()

    def mock_data(self):
        self.data = {"xxx": 123, "xxxx": "xxxx"}
        self.datas = ["xxx", "bbb"]

    def test_MemoryFilter(self):
        dedup = Dedup(
            Dedup.MemoryFilter, absolute_name=self.absolute_name
        )  # 表名为test 历史数据3秒有效期

        # 逐条去重
        self.assertEqual(dedup.add(self.data), 1)
        self.assertEqual(dedup.get(self.data), 1)

        # 批量去重
        self.assertEqual(dedup.add(self.datas), [1, 1])
        self.assertEqual(dedup.get(self.datas), [1, 1])

    def test_ExpireFilter(self):
        dedup = Dedup(
            Dedup.ExpireFilter,
            expire_time=10,
            redis_url="redis://@localhost:6379/0",
            absolute_name=self.absolute_name,
        )

        # 逐条去重
        self.assertEqual(dedup.add(self.data), 1)
        self.assertEqual(dedup.get(self.data), 1)

        # 批量去重
        self.assertEqual(dedup.add(self.datas), [1, 1])
        self.assertEqual(dedup.get(self.datas), [1, 1])

    def test_BloomFilter(self):
        dedup = Dedup(
            Dedup.BloomFilter,
            redis_url="redis://@localhost:6379/0",
            absolute_name=self.absolute_name,
        )

        # 逐条去重
        self.assertEqual(dedup.add(self.data), 1)
        self.assertEqual(dedup.get(self.data), 1)

        # 批量去重
        self.assertEqual(dedup.add(self.datas), [1, 1])
        self.assertEqual(dedup.get(self.datas), [1, 1])

    def test_LiteFilter(self):
        dedup = Dedup(
            Dedup.LiteFilter,
        )

        # 逐条去重
        self.assertEqual(dedup.add(self.data), 1)
        self.assertEqual(dedup.get(self.data), 1)

        # 批量去重
        self.assertEqual(dedup.add(self.datas), [1, 1])
        self.assertEqual(dedup.get(self.datas), [1, 1])

    def test_filter(self):
        dedup = Dedup(
            Dedup.BloomFilter,
            redis_url="redis://@localhost:6379/0",
            to_md5=True,
            absolute_name=self.absolute_name,
        )

        # 制造已存在数据
        self.datas = ["xxx", "bbb"]
        result = dedup.add(self.datas)
        self.assertEqual(result, [1, 1])

        # 过滤掉已存在数据 "xxx", "bbb"
        self.datas = ["xxx", "bbb", "ccc"]
        dedup.filter_exist_data(self.datas)
        self.assertEqual(self.datas, ["ccc"])
