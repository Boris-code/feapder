import unittest

from feapder.db.mongodb import MongoDB


class TestMongoDB(unittest.TestCase):
    coll_name = "test"

    def setUp(self) -> None:
        # self.db = MongoDB(ip="localhost", port=27017, db="feapder")
        self.db = MongoDB.from_url("mongodb://localhost:27017/feapder")

    def test_create_index(self):
        self.db.drop_collection(coll_name=self.coll_name)
        self.db.create_index(self.coll_name, ["a", "b"])

    def test_get_indexx(self):
        index = self.db.get_index(self.coll_name)
        print(index)

    def test_find(self):
        """
        查询数据
        @return:
        """
        r = self.db.find(
            coll_name=self.coll_name, limit=2, condition={"a": 1}, projection={"_id": 0}
        )
        print(r)

    def test_insert(self):
        """
        插入单条数据
        """
        r = self.db.add(coll_name=self.coll_name, data={"a": 1, "b": "你好", "c": "哈哈"})
        print(r)
        self.assertEqual(r, 1)

    def test_insert_replace(self):
        """
        插入单条数据，冲突时自动更新，即将重复数据替换为最新数据
        """
        r = self.db.add(
            coll_name=self.coll_name, data={"a": 1, "b": "你好", "c": "啦啦"}, replace=True
        )
        self.assertEqual(r, 1)

    def test_insert_columns(self):
        """
        插入单条数据，发生冲突时，更新指定字段
        """
        r = self.db.add(
            coll_name=self.coll_name,
            data={"a": 1, "b": "你好", "c": "666"},
            update_columns=("c",),
        )
        self.assertEqual(r, 1)

    def test_insert_update_columns_value(self):
        """
        插入单条数据，发生冲突时，用指定的值更新指定字段
        """
        r = self.db.add(
            coll_name=self.coll_name,
            data={"a": 1, "b": "你好", "c": "666"},
            update_columns=("c",),
            update_columns_value=("888",),
        )
        self.assertEqual(r, 1)

    def test_batch_insert(self):
        """
        测试批量数据插入，冲突时忽略
        @return:
        """
        items = [{"a": 1, "b": "你好", "c": "666"}, {"a": 2, "b": "他好", "c": "888"}]
        add_count = self.db.add_batch(self.coll_name, items)
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, "test", datas_size - add_count))

    def test_batch_insert_replace(self):
        """
        测试批量插入重复数据，重复时覆盖
        @return:
        """
        items = [{"a": 1, "b": "你好", "c": "xixixi"}, {"a": 2, "b": "他好", "c": "777"}]
        add_count = self.db.add_batch(self.coll_name, items, replace=True)
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, "test", datas_size - add_count))
        self.assertEqual(add_count, 0)

    def test_batch_insert_update_columns(self):
        """
        当数据冲突时，更新指定字段
        """
        items = [{"a": 1, "b": "你好", "c": "88"}, {"a": 2, "b": "他好", "c": "888"}]
        add_count = self.db.add_batch(self.coll_name, items, update_columns=("c",))
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, "test", datas_size - add_count))
        self.assertEqual(add_count, 0)

    def test_batch_insert_update_columns_value(self):
        """
        指定columns及columns_value
        当数据重复时, 用指定的值更新指定字段
        """
        items = [{"a": 1, "b": "你好", "c": "88"}, {"a": 2, "b": "他好", "c": "888"}]
        add_count = self.db.add_batch(
            self.coll_name, items, update_columns=("c",), update_columns_value=("haha",)
        )
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, "test", datas_size - add_count))
        self.assertEqual(add_count, 0)

    def test_update(self):
        """
        测试单条数据更新
        """
        data = {"a": 1, "b": "你好", "c": "666"}
        r = self.db.update(self.coll_name, data, {"a": 1})
        self.assertEqual(r, True)

    def test_delete(self):
        r = self.db.delete(self.coll_name, {"a": 1})
        self.assertEqual(r, True)

    def test_run_command(self):
        """
        测试运行指令
        @return:
        """
        r = self.db.run_command({"find": self.coll_name, "filter": {}})
        print(r)

    def test_drop_collection(self):
        r = self.db.drop_collection(self.coll_name)
        print(r)


if __name__ == "__main__":
    unittest.main()
