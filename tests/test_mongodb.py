import unittest

from feapder.db.mongodb import MongoDB


db = MongoDB(
    ip="192.168.20.241", port=27017, db="feapder"
)


class TestMongoDB(unittest.TestCase):
    
    def test_insert(self):
        # 插入单条数据
        r = db.add_smart(table="test", data={'_id': '607c25761b698fa5b385f3b7', 'feapder': 123})
        self.assertEqual(r, 1)
    
    def test_insert_auto_update(self):
        """
        插入单条数据，冲突时自动更新，即将重复数据替换为最新数据
        """
        r = db.add_smart(table="test", data={'_id': '607c25761b698fa5b385f3b7', 'feapder': 899, 'a': 1, 'b': 2},
                         auto_update=True)
        self.assertEqual(r, 1)
    
    def test_insert_columns(self):
        """
        插入单条数据，发生冲突时，更新指定字段
        """
        r = db.add_smart(table="test", data={'_id': '607c25761b698fa5b385f3b7', 'a': 0}, update_columns=('a',))
        self.assertEqual(r, 1)
    
    def test_batch_insert(self):
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
        add_count = db.add_batch_smart('test', items)
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, 'test', datas_size - add_count))
    
    def test_batch_insert_repeat(self):
        items = [
            {
                '_id': '607c271885832edde1a805d2',
                'a': 1
            }
        ]
        add_count = db.add_batch_smart('test', items)
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, 'test', datas_size - add_count))
        self.assertEqual(datas_size, 1)
        self.assertEqual(add_count, 0)
    
    def test_batch_insert_auto_update(self):
        """
        当数据冲突时，替换这条数据
        """
        items = [
            {
                '_id': '607c271885832edde1a805d2',
                'a': 3,
                'b': 2,
                'c': 1,
                'd': 0
            }
        ]
        add_count = db.add_batch_smart('test', items, auto_update=True)
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, 'test', datas_size - add_count))
        self.assertEqual(datas_size, 1)
        self.assertEqual(add_count, 1)
    
    def test_batch_insert_columns(self):
        """
        指定columns及columns_value
        当数据重复时插入指定字段
        """
        items = [
            {
                '_id': '607c271885832edde1a805d2',
                'a': 3,
                'b': 2,
                'c': 1
            }
        ]
        add_count = db.add_batch_smart('test', items, update_columns=('b', 'c'), update_columns_value=('5', '6'))
        datas_size = len(items)
        print("共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, 'test', datas_size - add_count))
        self.assertEqual(datas_size, 1)
        self.assertEqual(add_count, 1)
    
    def test_update(self):
        """
        测试数据更新
        """
        data = {
            '_id': '607c271885832edde1a805d2',
            'a': 3,
            'b': 2,
            'c': 1
        }
        r = db.update_smart('test', data, {'_id': '607c271885832edde1a805d2'})
        self.assertEqual(r, True)
    
    def test_delete(self):
        r = db.delete('test', {'_id': '607c271885832edde1a805d2'})
        self.assertEqual(r, True)


if __name__ == '__main__':
    unittest.main()
