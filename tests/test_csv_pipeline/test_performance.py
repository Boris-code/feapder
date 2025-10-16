# -*- coding: utf-8 -*-
"""
CSV Pipeline 性能测试

测试内容：
1. 批量写入性能
2. 并发写入性能
3. 内存占用情况
4. 文件大小和数据完整性

Created on 2025-10-16
@author: 道长
@email: ctrlf4@yeah.net
"""

import csv
import os
import sys
import time
import shutil
import threading
import psutil
from pathlib import Path
from typing import List, Dict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from feapder.pipelines.csv_pipeline import CsvPipeline


class PerformanceTester:
    """CSV Pipeline 性能测试器"""

    def __init__(self, test_dir="test_output"):
        """初始化测试器"""
        self.test_dir = test_dir
        self.pipeline = None
        self.process = psutil.Process()
        self.test_results = {}

    def setup(self):
        """测试前准备"""
        # 清理历史测试目录
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

        # 创建测试输出目录
        os.makedirs(self.test_dir, exist_ok=True)

        # 初始化 Pipeline
        csv_dir = os.path.join(self.test_dir, "csv")
        self.pipeline = CsvPipeline(csv_dir=csv_dir)

        print(f"✅ 测试环境准备完成，输出目录: {self.test_dir}")

    def teardown(self):
        """测试后清理"""
        if self.pipeline:
            self.pipeline.close()

    def generate_test_data(self, count: int) -> List[Dict]:
        """生成测试数据"""
        data = []
        for i in range(count):
            data.append({
                "id": i + 1,
                "name": f"Product_{i + 1}",
                "price": 99.99 + i * 0.1,
                "category": "Electronics",
                "url": f"https://example.com/product/{i + 1}",
                "stock": 100 - (i % 50),
                "rating": 4.5 + (i % 5) * 0.1,
                "description": f"Description for product {i + 1}" * 3,
            })
        return data

    def test_single_batch_performance(self):
        """测试单批写入性能"""
        print("\n" + "=" * 80)
        print("测试 1: 单批写入性能")
        print("=" * 80)

        batch_sizes = [100, 500, 1000, 5000]
        results = {}

        for batch_size in batch_sizes:
            data = self.generate_test_data(batch_size)

            # 测试写入时间
            start_time = time.time()
            success = self.pipeline.save_items("product", data)
            elapsed = time.time() - start_time

            # 测试结果
            results[batch_size] = {
                "success": success,
                "elapsed_time": elapsed,
                "throughput": batch_size / elapsed if elapsed > 0 else 0,
            }

            print(f"批量大小: {batch_size:5d} | "
                  f"耗时: {elapsed:.4f}s | "
                  f"吞吐量: {results[batch_size]['throughput']:.0f} 条/秒 | "
                  f"状态: {'✅' if success else '❌'}")

        self.test_results["single_batch"] = results
        return results

    def test_concurrent_write_performance(self):
        """测试并发写入性能"""
        print("\n" + "=" * 80)
        print("测试 2: 并发写入性能（模拟多爬虫线程）")
        print("=" * 80)

        thread_counts = [1, 2, 4, 8]
        results = {}

        for thread_count in thread_counts:
            # 每个线程写入的数据条数
            items_per_thread = 100
            total_items = thread_count * items_per_thread

            def write_thread(thread_id):
                """线程工作函数"""
                data = self.generate_test_data(items_per_thread)
                # 为了模拟不同表，使用不同的表名
                table_name = f"product_thread_{thread_id}"
                return self.pipeline.save_items(table_name, data)

            # 记录初始内存
            mem_before = self.process.memory_info().rss / 1024 / 1024

            # 并发执行
            start_time = time.time()
            threads = []
            for i in range(thread_count):
                t = threading.Thread(target=write_thread, args=(i,))
                t.start()
                threads.append(t)

            # 等待所有线程完成
            for t in threads:
                t.join()

            elapsed = time.time() - start_time
            mem_after = self.process.memory_info().rss / 1024 / 1024
            mem_delta = mem_after - mem_before

            results[thread_count] = {
                "total_items": total_items,
                "elapsed_time": elapsed,
                "throughput": total_items / elapsed if elapsed > 0 else 0,
                "memory_delta_mb": mem_delta,
            }

            print(f"线程数: {thread_count} | "
                  f"总数据: {total_items:5d} | "
                  f"耗时: {elapsed:.4f}s | "
                  f"吞吐量: {results[thread_count]['throughput']:.0f} 条/秒 | "
                  f"内存增长: {mem_delta:.2f}MB")

        self.test_results["concurrent_write"] = results
        return results

    def test_memory_usage(self):
        """测试内存占用"""
        print("\n" + "=" * 80)
        print("测试 3: 内存占用情况")
        print("=" * 80)

        # 测试不同数量的数据对内存的影响
        test_counts = [1000, 5000, 10000, 50000]
        results = {}

        for count in test_counts:
            data = self.generate_test_data(count)

            # 记录内存
            mem_before = self.process.memory_info().rss / 1024 / 1024

            # 执行写入
            start_time = time.time()
            self.pipeline.save_items("product_memory", data)
            elapsed = time.time() - start_time

            mem_after = self.process.memory_info().rss / 1024 / 1024
            mem_used = mem_after - mem_before
            mem_per_item = mem_used / count if count > 0 else 0

            results[count] = {
                "memory_before_mb": mem_before,
                "memory_after_mb": mem_after,
                "memory_used_mb": mem_used,
                "memory_per_item_kb": mem_per_item * 1024,
                "elapsed_time": elapsed,
            }

            print(f"数据条数: {count:6d} | "
                  f"内存占用: {mem_used:6.2f}MB | "
                  f"每条数据: {mem_per_item * 1024:.2f}KB | "
                  f"耗时: {elapsed:.4f}s")

        self.test_results["memory_usage"] = results
        return results

    def test_file_integrity(self):
        """测试文件完整性"""
        print("\n" + "=" * 80)
        print("测试 4: 文件完整性检查")
        print("=" * 80)

        # 写入测试数据
        test_data = self.generate_test_data(1000)
        table_name = "product_integrity"

        success = self.pipeline.save_items(table_name, test_data)

        if not success:
            print("❌ 写入失败")
            return {"status": "failed"}

        # 检查文件是否存在
        csv_file = os.path.join(self.pipeline.csv_dir, f"{table_name}.csv")
        if not os.path.exists(csv_file):
            print("❌ CSV 文件不存在")
            return {"status": "file_not_found"}

        # 读取 CSV 文件并检查数据完整性
        read_data = []
        with open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                read_data.append(row)

        # 对比数据
        if len(read_data) != len(test_data):
            print(f"❌ 数据条数不符: 写入{len(test_data)}条，读取{len(read_data)}条")
            return {
                "status": "count_mismatch",
                "written": len(test_data),
                "read": len(read_data),
            }

        # 检查字段是否完整
        expected_fields = set(test_data[0].keys())
        actual_fields = set(read_data[0].keys())
        if expected_fields != actual_fields:
            print(f"❌ 字段不符\n期望: {expected_fields}\n实际: {actual_fields}")
            return {
                "status": "field_mismatch",
                "expected": list(expected_fields),
                "actual": list(actual_fields),
            }

        # 检查数据值是否正确（抽样检查）
        sample_indices = [0, len(test_data) // 2, len(test_data) - 1]
        for idx in sample_indices:
            original = test_data[idx]
            read = read_data[idx]

            for key in original.keys():
                if str(original[key]) != read.get(key, ""):
                    print(f"❌ 数据不符 (第{idx}行, 字段{key})\n"
                          f"期望: {original[key]}\n"
                          f"实际: {read.get(key)}")
                    return {"status": "data_mismatch", "index": idx, "field": key}

        print(f"✅ 文件完整性检查通过")
        print(f"   总条数: {len(read_data)}")
        print(f"   字段数: {len(actual_fields)}")
        print(f"   文件大小: {os.path.getsize(csv_file) / 1024:.2f}KB")

        return {
            "status": "passed",
            "total_rows": len(read_data),
            "total_fields": len(actual_fields),
            "file_size_kb": os.path.getsize(csv_file) / 1024,
        }

    def test_append_mode(self):
        """测试追加模式（断点续爬）"""
        print("\n" + "=" * 80)
        print("测试 5: 追加模式（断点续爬）")
        print("=" * 80)

        table_name = "product_append"

        # 第一次写入
        data1 = self.generate_test_data(100)
        self.pipeline.save_items(table_name, data1)

        csv_file = os.path.join(self.pipeline.csv_dir, f"{table_name}.csv")
        size_after_first = os.path.getsize(csv_file) if os.path.exists(csv_file) else 0

        # 第二次写入（追加）
        data2 = self.generate_test_data(100)
        self.pipeline.save_items(table_name, data2)

        size_after_second = os.path.getsize(csv_file) if os.path.exists(csv_file) else 0

        # 读取文件检查数据
        read_data = []
        with open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                read_data.append(row)

        # 检查是否正确追加
        if len(read_data) == len(data1) + len(data2):
            print(f"✅ 追加模式正常")
            print(f"   第一次写入: {len(data1)} 条")
            print(f"   第二次写入: {len(data2)} 条")
            print(f"   最终总数: {len(read_data)} 条")
            print(f"   第一次后大小: {size_after_first / 1024:.2f}KB")
            print(f"   第二次后大小: {size_after_second / 1024:.2f}KB")

            return {
                "status": "passed",
                "first_write": len(data1),
                "second_write": len(data2),
                "total": len(read_data),
                "size_growth_kb": (size_after_second - size_after_first) / 1024,
            }
        else:
            print(f"❌ 追加模式异常: 期望{len(data1) + len(data2)}条，实际{len(read_data)}条")
            return {
                "status": "failed",
                "expected": len(data1) + len(data2),
                "actual": len(read_data),
            }

    def test_concurrent_safety(self):
        """测试并发安全性（Per-Table Lock）"""
        print("\n" + "=" * 80)
        print("测试 6: 并发安全性（Per-Table Lock）")
        print("=" * 80)

        table_name = "product_concurrent_safety"
        thread_count = 4
        items_per_thread = 250

        errors = []
        lock = threading.Lock()

        def write_thread(thread_id):
            """线程工作函数"""
            try:
                data = self.generate_test_data(items_per_thread)
                success = self.pipeline.save_items(table_name, data)
                if not success:
                    with lock:
                        errors.append(f"线程{thread_id}写入失败")
            except Exception as e:
                with lock:
                    errors.append(f"线程{thread_id}异常: {e}")

        # 并发执行
        threads = []
        start_time = time.time()
        for i in range(thread_count):
            t = threading.Thread(target=write_thread, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        elapsed = time.time() - start_time

        # 检查文件
        csv_file = os.path.join(self.pipeline.csv_dir, f"{table_name}.csv")
        read_data = []
        with open(csv_file, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                read_data.append(row)

        expected_total = thread_count * items_per_thread

        if len(errors) == 0 and len(read_data) == expected_total:
            print(f"✅ 并发安全性测试通过")
            print(f"   线程数: {thread_count}")
            print(f"   每线程数据: {items_per_thread}")
            print(f"   期望总数: {expected_total}")
            print(f"   实际总数: {len(read_data)}")
            print(f"   耗时: {elapsed:.4f}s")
            print(f"   吞吐量: {expected_total / elapsed:.0f} 条/秒")

            return {
                "status": "passed",
                "thread_count": thread_count,
                "items_per_thread": items_per_thread,
                "expected_total": expected_total,
                "actual_total": len(read_data),
                "elapsed_time": elapsed,
                "throughput": expected_total / elapsed,
            }
        else:
            print(f"❌ 并发安全性测试失败")
            if errors:
                for error in errors:
                    print(f"   {error}")
            if len(read_data) != expected_total:
                print(f"   数据条数不符: 期望{expected_total}条，实际{len(read_data)}条")

            return {
                "status": "failed",
                "errors": errors,
                "expected_total": expected_total,
                "actual_total": len(read_data),
            }

    def test_multiple_tables(self):
        """测试多表存储"""
        print("\n" + "=" * 80)
        print("测试 7: 多表存储")
        print("=" * 80)

        tables = ["product", "user", "order"]
        rows_per_table = 500
        results = {}

        start_time = time.time()

        for table in tables:
            data = self.generate_test_data(rows_per_table)
            success = self.pipeline.save_items(table, data)

            csv_file = os.path.join(self.pipeline.csv_dir, f"{table}.csv")
            file_size = os.path.getsize(csv_file) / 1024 if os.path.exists(csv_file) else 0

            results[table] = {
                "success": success,
                "file_size_kb": file_size,
            }

            print(f"表: {table:10s} | 状态: {'✅' if success else '❌'} | "
                  f"文件大小: {file_size:.2f}KB")

        elapsed = time.time() - start_time

        # 检查所有文件
        csv_dir = self.pipeline.csv_dir
        files = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]

        print(f"\n✅ 多表存储测试完成")
        print(f"   表数: {len(tables)}")
        print(f"   每表行数: {rows_per_table}")
        print(f"   生成的 CSV 文件: {len(files)}")
        print(f"   耗时: {elapsed:.4f}s")

        return {
            "status": "passed",
            "tables": results,
            "file_count": len(files),
            "elapsed_time": elapsed,
        }

    def run_all_tests(self):
        """运行所有测试"""
        print("\n")
        print("╔" + "═" * 78 + "╗")
        print("║" + " CSV Pipeline 性能和功能测试 ".center(78) + "║")
        print("║" + " 作者: 道长 | 日期: 2025-10-16 ".center(78) + "║")
        print("╚" + "═" * 78 + "╝")

        try:
            self.setup()

            # 运行所有测试
            self.test_single_batch_performance()
            self.test_concurrent_write_performance()
            self.test_memory_usage()
            self.test_file_integrity()
            self.test_append_mode()
            self.test_concurrent_safety()
            self.test_multiple_tables()

            # 打印总结
            self.print_summary()

            return True

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

        # 单批性能总结
        if "single_batch" in self.test_results:
            print("\n1. 单批写入性能:")
            results = self.test_results["single_batch"]
            for batch_size, data in results.items():
                print(f"   {batch_size:5d} 条: {data['throughput']:.0f} 条/秒, "
                      f"耗时 {data['elapsed_time']:.4f}s")

        # 并发性能总结
        if "concurrent_write" in self.test_results:
            print("\n2. 并发写入性能:")
            results = self.test_results["concurrent_write"]
            for thread_count, data in results.items():
                print(f"   {thread_count} 线程: {data['throughput']:.0f} 条/秒, "
                      f"内存增长 {data['memory_delta_mb']:.2f}MB")

        # 内存占用总结
        if "memory_usage" in self.test_results:
            print("\n3. 内存占用情况:")
            results = self.test_results["memory_usage"]
            for count, data in results.items():
                print(f"   {count:6d} 条: {data['memory_used_mb']:.2f}MB, "
                      f"每条 {data['memory_per_item_kb']:.2f}KB")

        print("\n" + "=" * 80)
        print("✅ 所有测试完成！")
        print("=" * 80)


def main():
    """主函数"""
    tester = PerformanceTester(test_dir="tests/test_csv_pipeline/test_output")
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
