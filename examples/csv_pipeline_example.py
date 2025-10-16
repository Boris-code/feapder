# -*- coding: utf-8 -*-
"""
Created on 2025-10-16
---------
@summary: CSV Pipeline 使用示例
---------
@author: 道长
@email: ctrlf4@yeah.net

演示如何使用 CsvPipeline 将爬虫数据保存为 CSV 文件。
"""

import feapder
from feapder.network.item import Item


# 定义数据项目
class ProductItem(Item):
    """商品数据项"""

    # 指定表名，对应 CSV 文件名为 product.csv
    table_name = "product"

    def clean(self):
        """数据清洁方法（可选）"""
        pass


class CsvPipelineSpider(feapder.AirSpider):
    """
    演示使用CSV Pipeline的爬虫

    注意：要启用CsvPipeline，需要在 setting.py 中配置：
    ITEM_PIPELINES = [
        ...,
        "feapder.pipelines.csv_pipeline.CsvPipeline",
    ]
    """

    def start_requests(self):
        """生成初始请求"""
        # 这里以示例数据代替真实网络请求
        yield feapder.Request("https://example.com/products")

    def parse(self, request, response):
        """
        解析页面

        在实际应用中，你会从HTML中提取数据。
        这里我们生成示例数据来演示CSV存储功能。
        """
        # 示例：生成10条商品数据
        for i in range(10):
            item = ProductItem()
            item.id = i + 1
            item.name = f"商品_{i + 1}"
            item.price = 99.99 + i
            item.category = "电子产品"
            item.url = f"https://example.com/product/{i + 1}"

            yield item


class CsvPipelineSpiderWithMultiTables(feapder.AirSpider):
    """
    演示使用CSV Pipeline处理多表数据

    CsvPipeline支持多表存储，每个表对应一个CSV文件。
    """

    def start_requests(self):
        """生成初始请求"""
        yield feapder.Request("https://example.com/products")
        yield feapder.Request("https://example.com/users")

    def parse(self, request, response):
        """解析页面，输出不同表的数据"""

        if "/products" in request.url:
            # 产品表数据
            for i in range(5):
                item = ProductItem()
                item.id = i + 1
                item.name = f"商品_{i + 1}"
                item.price = 99.99 + i
                item.category = "电子产品"
                item.url = request.url

                yield item

        elif "/users" in request.url:
            # 用户表数据
            user_item = Item()
            user_item.table_name = "user"

            for i in range(5):
                user_item.id = i + 1
                user_item.username = f"user_{i + 1}"
                user_item.email = f"user_{i + 1}@example.com"
                user_item.created_at = "2024-10-16"

                yield user_item


# 配置说明
"""
使用CSV Pipeline需要的配置步骤：

1. 在 feapder/setting.py 中启用 CsvPipeline：

   ITEM_PIPELINES = [
       "feapder.pipelines.mysql_pipeline.MysqlPipeline",  # 保持MySQL
       "feapder.pipelines.csv_pipeline.CsvPipeline",      # 新增CSV
   ]

2. CSV文件会自动保存到 data/csv/ 目录下：
   - product.csv: 商品表数据
   - user.csv: 用户表数据
   - 等等...

3. CSV文件会自动包含表头（首次创建时）

4. 如果爬虫中断后重新启动，CSV数据会继续追加
   （支持断点续爬）

性能特点：
- 每批数据最多1000条（由 ITEM_UPLOAD_BATCH_MAX_SIZE 控制）
- 每秒最多1000条，或等待1秒触发批处理
- 使用Per-Table Lock，确保单表写入安全
- 通过 fsync 确保数据落盘，不会丢失

注意事项：
- CSV文件本身不支持真正的UPDATE操作
- 如果有重复数据，可在应用层处理或启用 ITEM_FILTER_ENABLE
- 如果需要真正的UPDATE操作，建议配合MySQL或MongoDB使用
"""


if __name__ == "__main__":
    # 运行爬虫示例
    CsvPipelineSpider().start()

    # 或运行多表示例
    # CsvPipelineSpiderWithMultiTables().start()
