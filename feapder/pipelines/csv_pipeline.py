# -*- coding: utf-8 -*-
"""
Created on 2025-10-16
---------
@summary: CSV 数据导出Pipeline
---------
@author: 道长
@email: ctrlf4@yeah.net
"""

import csv
import os
import threading
from typing import Dict, List, Tuple

from feapder.pipelines import BasePipeline
from feapder.utils.log import log


class CsvPipeline(BasePipeline):
    """
    CSV 数据导出Pipeline

    将爬虫数据保存为CSV文件。支持批量保存、并发写入控制、断点续爬等功能。

    特点：
    - 单表单锁设计，避免全局锁带来的性能问题
    - 自动创建导出目录
    - 支持追加模式，便于断点续爬
    - 通过fsync确保数据落盘
    - 表级别的字段名缓存，确保跨批字段顺序一致
    """

    # 用于保护每个表的文件写入操作（Per-Table Lock）
    _file_locks = {}

    # 用于缓存每个表的字段名顺序（Per-Table Fieldnames Cache）
    # 确保跨批次、跨线程的字段顺序一致
    _table_fieldnames = {}

    def __init__(self, csv_dir=None):
        """
        初始化CSV Pipeline

        Args:
            csv_dir: CSV文件保存目录
                    - 如果不传，从 setting.CSV_EXPORT_PATH 读取
                    - 支持相对路径（如 "data/csv"）
                    - 支持绝对路径（如 "/Users/xxx/exports/csv"）
        """
        super().__init__()

        # 如果未传入参数，从配置文件读取
        if csv_dir is None:
            import feapder.setting as setting
            csv_dir = setting.CSV_EXPORT_PATH

        # 支持绝对路径和相对路径，统一转换为绝对路径
        self.csv_dir = os.path.abspath(csv_dir)
        self._ensure_csv_dir_exists()

    def _ensure_csv_dir_exists(self):
        """确保CSV保存目录存在"""
        if not os.path.exists(self.csv_dir):
            try:
                os.makedirs(self.csv_dir, exist_ok=True)
                log.info(f"创建CSV保存目录: {self.csv_dir}")
            except Exception as e:
                log.error(f"创建CSV目录失败: {e}")
                raise

    @staticmethod
    def _get_lock(table):
        """
        获取表对应的文件锁

        采用Per-Table Lock设计，每个表都有独立的锁，避免锁竞争。
        这样设计既能保证单表的文件写入安全，又能充分利用多表并行写入的优势。

        Args:
            table: 表名

        Returns:
            threading.Lock: 该表对应的锁对象
        """
        if table not in CsvPipeline._file_locks:
            CsvPipeline._file_locks[table] = threading.Lock()
        return CsvPipeline._file_locks[table]

    @staticmethod
    def _get_and_cache_fieldnames(table, items):
        """
        获取并缓存表对应的字段名顺序

        第一次调用时从items[0]提取字段名并缓存，后续调用直接返回缓存的字段名。
        这样设计确保：
        1. 跨批次的字段顺序保持一致（解决数据列错位问题）
        2. 多线程并发时字段顺序不被污染
        3. 避免重复提取，性能更优

        Args:
            table: 表名
            items: 数据列表 [{}，{}，...]

        Returns:
            list: 字段名列表
        """
        # 如果该表已经缓存了字段名，直接返回缓存的
        if table in CsvPipeline._table_fieldnames:
            return CsvPipeline._table_fieldnames[table]

        # 第一次调用，从items提取字段名并缓存
        if not items:
            return []

        first_item = items[0]
        fieldnames = list(first_item.keys()) if isinstance(first_item, dict) else []

        if fieldnames:
            # 缓存字段名（使用静态变量，跨实例共享）
            CsvPipeline._table_fieldnames[table] = fieldnames
            log.info(f"表 {table} 的字段名已缓存: {fieldnames}")

        return fieldnames

    def _get_csv_file_path(self, table):
        """
        获取表对应的CSV文件路径

        Args:
            table: 表名

        Returns:
            str: CSV文件的完整路径
        """
        return os.path.join(self.csv_dir, f"{table}.csv")


    def _file_exists_and_has_content(self, csv_file):
        """
        检查CSV文件是否存在且有内容

        Args:
            csv_file: CSV文件路径

        Returns:
            bool: 文件存在且有内容返回True
        """
        return os.path.exists(csv_file) and os.path.getsize(csv_file) > 0

    def save_items(self, table, items: List[Dict]) -> bool:
        """
        保存数据到CSV文件

        采用追加模式打开文件，支持断点续爬。第一次写入时会自动添加表头。
        使用Per-Table Lock确保多线程写入时的数据一致性。
        使用缓存的字段名确保跨批次字段顺序一致，避免数据列错位。

        Args:
            table: 表名（对应CSV文件名）
            items: 数据列表，[{}, {}, ...]

        Returns:
            bool: 保存成功返回True，失败返回False
                 失败时ItemBuffer会自动重试（最多10次）
        """
        if not items:
            return True

        csv_file = self._get_csv_file_path(table)

        # 使用缓存机制获取字段名（关键！确保跨批字段顺序一致）
        fieldnames = self._get_and_cache_fieldnames(table, items)

        if not fieldnames:
            log.warning(f"无法提取字段名，items: {items}")
            return False

        try:
            # 获取表级别的锁（关键！保证文件写入安全）
            lock = self._get_lock(table)
            with lock:
                # 检查文件是否已存在且有内容
                file_exists = self._file_exists_and_has_content(csv_file)

                # 以追加模式打开文件
                with open(
                    csv_file,
                    "a",
                    encoding="utf-8",
                    newline=""
                ) as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)

                    # 如果文件不存在或为空，写入表头
                    if not file_exists:
                        writer.writeheader()

                    # 批量写入数据行
                    # 使用缓存的fieldnames确保列顺序一致，避免跨批数据错位
                    writer.writerows(items)

                    # 刷新缓冲区到磁盘，确保数据不丢失
                    f.flush()
                    os.fsync(f.fileno())

            # 记录导出日志
            log.info(
                f"共导出 {len(items)} 条数据 到 {table}.csv (文件路径: {csv_file})"
            )
            return True

        except Exception as e:
            log.error(
                f"CSV写入失败. table: {table}, csv_file: {csv_file}, error: {e}"
            )
            return False

    def update_items(self, table, items: List[Dict], update_keys=Tuple) -> bool:
        """
        更新数据

        注意：CSV文件本身不支持真正的"更新"操作（需要查询后替换）。
        目前的实现是直接追加写入，相当于INSERT操作。

        如果需要真正的UPDATE操作，建议：
        1. 定期重新生成CSV文件
        2. 使用数据库（MySQL/MongoDB）来处理UPDATE
        3. 或在应用层进行去重和更新

        Args:
            table: 表名
            items: 数据列表，[{}, {}, ...]
            update_keys: 更新的字段（此实现中未使用）

        Returns:
            bool: 操作成功返回True
        """
        # 对于CSV，update操作实现为追加写入
        # 若需要真正的UPDATE操作，建议在应用层处理
        return self.save_items(table, items)

    def close(self):
        """
        关闭Pipeline，释放资源

        在爬虫结束时由ItemBuffer自动调用。
        """
        try:
            # 清理文件锁字典（可选，用于释放内存）
            # 在长期运行的场景下，可能需要定期清理
            pass
        except Exception as e:
            log.error(f"关闭CSV Pipeline时出错: {e}")
