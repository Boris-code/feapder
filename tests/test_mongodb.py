import unittest

from feapder.db.mongodb import MongoDB

db = MongoDB(
    ip="localhost",
    port=27017,
    db="feapder"
)


class TestMongoDB(unittest.TestCase):
    coll_name = 'test'
    
    def test_find(self):
        """
        查询数据
        @return:
        """
        r = db.find(coll_name=self.coll_name, limit=2, condition={'a': 1}, projection={'_id': 0})
        print(r)
    
    def test_insert(self):
        # 插入单条数据
        r = db.add(coll_name=self.coll_name, data={'_id': '607c25761b698fa5b385f3b2', 'feapder': 123})
        print(r)
        self.assertEqual(r, 1)
    
    def test_insert_auto_update(self):
        """
        插入单条数据，冲突时自动更新，即将重复数据替换为最新数据
        """
        r = db.add(coll_name=self.coll_name, data={'_id': '607c25761b698fa5b385f3b2', 'feapder': 899, 'a': 1, 'b': 2},
                   auto_update=True)
        self.assertEqual(r, 1)
    
    def test_insert_columns(self):
        """
        插入单条数据，发生冲突时，更新指定字段
        """
        r = db.add(coll_name=self.coll_name, data={'_id': '607c25761b698fa5b385f3b2', 'a': 0}, update_columns=('a',))
        self.assertEqual(r, 1)
    
    def test_batch_insert(self):
        """
        测试批量数据插入
        @return:
        """
        items = [
            {
                'a': 1
            },
            {
                'b': 2
            },
            {
                'c': 3
            }
        ]
        add_count = db.add_batch(self.coll_name, items)
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, 'test', datas_size - add_count))
    
    def test_batch_insert_repeat(self):
        """
        测试批量插入重复数据，重复时不做任何处理
        @return:
        """
        items = [
            {
                '_id': '607c271885832edde1a805d2',
                'a': 1
            },
            {
                '_id': '607c25761b698fa5b385f3b2',
                'a': 9
            }
        ]
        add_count = db.add_batch(self.coll_name, items)
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, 'test', datas_size - add_count))
        self.assertEqual(add_count, 0)
    
    def test_batch_insert_auto_update(self):
        """
        当数据冲突时，替换这条数据
        """
        items = [
            {
                '_id': '607c25761b698fa5b385f3b2',
                'a': 3,
                'b': 2,
                'c': 1,
                'd': 0
            }
        ]
        add_count = db.add_batch(self.coll_name, items, auto_update=True)
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, 'test', datas_size - add_count))
        self.assertEqual(add_count, 1)
    
    def test_batch_insert_columns(self):
        """
        指定columns及columns_value
        当数据重复时插入指定字段
        """
        items = [
            {
                "_id": "614411b4e7ecea419dfc7b37",
                'a': 3,
                'b': 2,
                'c': 1
            },
            {
                "_id": "614411b4e7ecea419dfc7b38",
                'a': 4,
                'b': 5,
                'c': 6
            },
            {
                "_id": "614411b4e7ecea419dfc7b37",
                'a': 3,
                'b': 2,
                'c': 1
            },
            {
                "_id": "614411b4e7ecea419dfc7b38",
                'a': 4,
                'b': 5,
                'c': 6
            }
        ]
        add_count = db.add_batch(self.coll_name, items, update_columns=('b', 'c'), update_columns_value=('-1', '-2'))
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, 'test', datas_size - add_count))
        self.assertEqual(add_count, 2)
    
    def test_update(self):
        """
        测试单条数据更新
        """
        data = {
            '_id': '607c271885832edde1a805d2',
            'a': 3,
            'b': 3,
            'c': 3
        }
        r = db.update(self.coll_name, data, {'_id': '607c271885832edde1a805d2'})
        self.assertEqual(r, True)
    
    def test_delete(self):
        r = db.delete(self.coll_name, {'_id': '607c271885832edde1a805d2'})
        self.assertEqual(r, True)
    
    def test_run_command(self):
        """
        测试运行指令
        @return:
        """
        r = db.run_command({
            'find': self.coll_name,
            'filter': {}
        })
        print(r)


if __name__ == '__main__':
    unittest.main()
