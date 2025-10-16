# -*- coding: utf-8 -*-
"""
CSV Pipeline 功能测试

测试内容：
1. 基础功能测试
2. 异常处理测试
3. 边界条件测试
4. 兼容性测试

Created on 2025-10-16
@author: 道长
@email: ctrlf4@yeah.net
"""

import csv
import os
import sys
import shutil
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from feapder.pipelines.csv_pipeline import CsvPipeline


class FunctionalityTester:
    """CSV Pipeline 功能测试器"""

    def __init__(self, test_dir="test_output"):
        """初始化测试器"""
        self.test_dir = test_dir
        self.pipeline = None
        self.passed = 0
        self.failed = 0

    def setup(self):
        """测试前准备"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

        os.makedirs(self.test_dir, exist_ok=True)

        csv_dir = os.path.join(self.test_dir, "csv")
        self.pipeline = CsvPipeline(csv_dir=csv_dir)

        print(f"✅ 测试环境准备完成")

    def teardown(self):
        """测试后清理"""
        if self.pipeline:
            self.pipeline.close()

    def assert_true(self, condition, message):
        """断言真"""
        if condition:
            print(f"   ✅ {message}")
            self.passed += 1
        else:
            print(f"   ❌ {message}")
            self.failed += 1

    def assert_false(self, condition, message):
        """断言假"""
        self.assert_true(not condition, message)

    def assert_equal(self, actual, expected, message):
        """断言相等"""
        if actual == expected:
            print(f"   ✅ {message}")
            self.passed += 1
        else:
            print(f"   ❌ {message} (期望: {expected}, 实际: {actual})")
            self.failed += 1

    def test_basic_save(self):
        """测试基础保存功能"""
        print("\n" + "=" * 80)
        print("测试 1: 基础保存功能")
        print("=" * 80)

        # 测试保存单条数据
        item = {"id": 1, "name": "Test Product", "price": 99.99}
        result = self.pipeline.save_items("product", [item])
        self.assert_true(result, "保存单条数据")

        # 检查文件是否创建
        csv_file = os.path.join(self.pipeline.csv_dir, "product.csv")
        self.assert_true(os.path.exists(csv_file), "CSV 文件已创建")

        # 检查数据是否正确
        with open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assert_equal(len(rows), 1, "文件中有 1 条数据")
            if rows:
                self.assert_equal(rows[0]["id"], "1", "数据 ID 正确")
                self.assert_equal(rows[0]["name"], "Test Product", "数据名称正确")

    def test_batch_save(self):
        """测试批量保存"""
        print("\n" + "=" * 80)
        print("测试 2: 批量保存功能")
        print("=" * 80)

        # 生成测试数据
        items = []
        for i in range(10):
            items.append({
                "id": i + 1,
                "name": f"Product_{i + 1}",
                "price": 100 + i,
            })

        result = self.pipeline.save_items("batch_test", items)
        self.assert_true(result, "批量保存 10 条数据")

        # 检查数据行数
        csv_file = os.path.join(self.pipeline.csv_dir, "batch_test.csv")
        with open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assert_equal(len(rows), 10, "批量保存数据行数正确")

    def test_empty_items(self):
        """测试空数据处理"""
        print("\n" + "=" * 80)
        print("测试 3: 空数据处理")
        print("=" * 80)

        result = self.pipeline.save_items("empty_test", [])
        self.assert_true(result, "空数据列表返回 True")

    def test_special_characters(self):
        """测试特殊字符处理"""
        print("\n" + "=" * 80)
        print("测试 4: 特殊字符处理")
        print("=" * 80)

        items = [
            {
                "id": 1,
                "name": "产品名称",
                "description": 'Contains "quotes" and, commas',
                "emoji": "😀🎉🚀",
                "newline": "Line1\nLine2",
            }
        ]

        result = self.pipeline.save_items("special_chars", items)
        self.assert_true(result, "保存包含特殊字符的数据")

        # 读取并检查
        csv_file = os.path.join(self.pipeline.csv_dir, "special_chars.csv")
        with open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                self.assert_equal(rows[0]["name"], "产品名称", "中文字符正确")
                self.assert_equal(
                    rows[0].get("emoji", ""),
                    "😀🎉🚀",
                    "Emoji 正确"
                )

    def test_multiple_tables(self):
        """测试多表存储"""
        print("\n" + "=" * 80)
        print("测试 5: 多表存储")
        print("=" * 80)

        tables = ["product", "user", "order"]
        for table in tables:
            item = {"id": 1, "name": f"Test {table}"}
            result = self.pipeline.save_items(table, [item])
            self.assert_true(result, f"保存到表 {table}")

        # 检查所有文件
        for table in tables:
            csv_file = os.path.join(self.pipeline.csv_dir, f"{table}.csv")
            self.assert_true(os.path.exists(csv_file), f"表 {table} 的 CSV 文件存在")

    def test_header_only_once(self):
        """测试表头只写一次"""
        print("\n" + "=" * 80)
        print("测试 6: 表头只写一次")
        print("=" * 80)

        table = "header_test"

        # 第一次写入
        items1 = [{"id": 1, "name": "Product 1"}]
        self.pipeline.save_items(table, items1)

        # 第二次写入
        items2 = [{"id": 2, "name": "Product 2"}]
        self.pipeline.save_items(table, items2)

        # 检查表头行数
        csv_file = os.path.join(self.pipeline.csv_dir, f"{table}.csv")
        with open(csv_file, 'r', encoding='utf-8', newline='') as f:
            lines = f.readlines()
            # 应该是：1 个表头 + 2 条数据
            self.assert_equal(len(lines), 3, "文件中只有 1 行表头和 2 行数据")

    def test_numeric_values(self):
        """测试数值类型"""
        print("\n" + "=" * 80)
        print("测试 7: 数值类型处理")
        print("=" * 80)

        items = [
            {
                "id": 1,
                "price": 99.99,
                "stock": 100,
                "rating": 4.5,
                "active": True,
            }
        ]

        result = self.pipeline.save_items("numeric_test", items)
        self.assert_true(result, "保存包含各类数值的数据")

        # 读取并检查
        csv_file = os.path.join(self.pipeline.csv_dir, "numeric_test.csv")
        with open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                self.assert_equal(rows[0]["price"], "99.99", "浮点数正确")
                self.assert_equal(rows[0]["stock"], "100", "整数正确")
                self.assert_equal(rows[0]["rating"], "4.5", "小数正确")

    def test_large_values(self):
        """测试大值处理"""
        print("\n" + "=" * 80)
        print("测试 8: 大值处理")
        print("=" * 80)

        large_text = "x" * 10000  # 10KB 的文本
        items = [
            {
                "id": 1,
                "name": "Large Content",
                "content": large_text,
            }
        ]

        result = self.pipeline.save_items("large_test", items)
        self.assert_true(result, "保存大内容数据")

        # 检查数据完整性
        csv_file = os.path.join(self.pipeline.csv_dir, "large_test.csv")
        with open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                self.assert_equal(
                    len(rows[0]["content"]),
                    len(large_text),
                    "大内容数据完整"
                )

    def test_update_items_fallback(self):
        """测试 update_items 降级为 save"""
        print("\n" + "=" * 80)
        print("测试 9: update_items 降级为 save")
        print("=" * 80)

        items = [{"id": 1, "name": "Product 1", "price": 100}]
        result = self.pipeline.update_items("update_test", items, ("price",))
        self.assert_true(result, "update_items 返回 True")

        # 检查数据是否存在
        csv_file = os.path.join(self.pipeline.csv_dir, "update_test.csv")
        self.assert_true(os.path.exists(csv_file), "update_items 创建了 CSV 文件")

    def test_file_operations(self):
        """测试文件操作"""
        print("\n" + "=" * 80)
        print("测试 10: 文件操作")
        print("=" * 80)

        items = [{"id": 1, "name": "Test"}]
        table = "file_test"

        result = self.pipeline.save_items(table, items)
        self.assert_true(result, "保存数据")

        csv_file = os.path.join(self.pipeline.csv_dir, f"{table}.csv")

        # 检查文件是否可读
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                f.read()
            self.assert_true(True, "CSV 文件可读")
        except Exception as e:
            self.assert_true(False, f"CSV 文件可读 ({e})")

        # 检查文件大小
        file_size = os.path.getsize(csv_file)
        self.assert_true(file_size > 0, f"CSV 文件大小 > 0 ({file_size} 字节)")

    def test_concurrent_same_table(self):
        """测试同表并发写入"""
        print("\n" + "=" * 80)
        print("测试 11: 同表并发写入（Per-Table Lock）")
        print("=" * 80)

        import threading

        table = "concurrent_same_table"
        errors = []

        def write_data(thread_id):
            try:
                items = [{"id": thread_id, "name": f"Item_{thread_id}"}]
                result = self.pipeline.save_items(table, items)
                if not result:
                    errors.append(f"线程{thread_id}写入失败")
            except Exception as e:
                errors.append(f"线程{thread_id}异常: {e}")

        # 创建多个线程
        threads = []
        for i in range(5):
            t = threading.Thread(target=write_data, args=(i,))
            t.start()
            threads.append(t)

        # 等待所有线程完成
        for t in threads:
            t.join()

        self.assert_equal(len(errors), 0, "并发写入无错误")

        # 检查数据完整性
        csv_file = os.path.join(self.pipeline.csv_dir, f"{table}.csv")
        with open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assert_true(len(rows) > 0, "并发写入产生了数据")

    def test_directory_creation(self):
        """测试目录自动创建"""
        print("\n" + "=" * 80)
        print("测试 12: 目录自动创建")
        print("=" * 80)

        # 创建新的 pipeline 实例，指定不存在的目录
        new_csv_dir = os.path.join(self.test_dir, "new_csv_dir")
        self.assert_false(os.path.exists(new_csv_dir), "新目录不存在")

        new_pipeline = CsvPipeline(csv_dir=new_csv_dir)
        self.assert_true(os.path.exists(new_csv_dir), "目录自动创建")

        new_pipeline.close()

    def test_none_values(self):
        """测试 None 值处理"""
        print("\n" + "=" * 80)
        print("测试 13: None 值处理")
        print("=" * 80)

        items = [
            {
                "id": 1,
                "name": "Product",
                "description": None,
                "optional_field": "",
            }
        ]

        result = self.pipeline.save_items("none_test", items)
        self.assert_true(result, "保存包含 None 值的数据")

        # 检查文件
        csv_file = os.path.join(self.pipeline.csv_dir, "none_test.csv")
        with open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                # None 会被转换为字符串 "None"
                self.assert_true("None" in rows[0]["description"],
                               "None 值被正确处理")

    def run_all_tests(self):
        """运行所有测试"""
        print("\n")
        print("╔" + "═" * 78 + "╗")
        print("║" + " CSV Pipeline 功能测试 ".center(78) + "║")
        print("║" + " 作者: 道长 | 日期: 2025-10-16 ".center(78) + "║")
        print("╚" + "═" * 78 + "╝")

        try:
            self.setup()

            # 运行所有测试
            self.test_basic_save()
            self.test_batch_save()
            self.test_empty_items()
            self.test_special_characters()
            self.test_multiple_tables()
            self.test_header_only_once()
            self.test_numeric_values()
            self.test_large_values()
            self.test_update_items_fallback()
            self.test_file_operations()
            self.test_concurrent_same_table()
            self.test_directory_creation()
            self.test_none_values()

            # 打印总结
            self.print_summary()

            return self.failed == 0

        except Exception as e:
            print(f"\n❌ 测试过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            self.teardown()

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("测试总结")
        print("=" * 80)
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"总计: {self.passed + self.failed}")

        if self.failed == 0:
            print("\n🎉 所有测试通过！")
        else:
            print(f"\n⚠️  有 {self.failed} 个测试失败")

        print("=" * 80)


def main():
    """主函数"""
    tester = FunctionalityTester(test_dir="tests/test_csv_pipeline/test_output_func")
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
