# -*- coding: utf-8 -*-
"""
    	*************************** 
    	--------description-------- 
 	 @Date : 2021-12-04
 	 @Author: 沈瑞祥
     @contact: ruixiang.shen@outlook.com
 	 @LastEditTime: 2021-12-04 23:24
 	 @FilePath: tests/test_postgresql_spider.py
     @Project: feapder

    	***************************
"""
import feapder
from feapder import Item, UpdateItem


class TestPostgreSQL(feapder.AirSpider):
    __custom_setting__ = dict(
        ITEM_PIPELINES=["feapder.pipelines.pgsql_pipeline.PgsqlPipeline"],
        PGSQL_IP="localhost",
        PGSQL_PORT=5432,
        PGSQL_DB="feapder",
        PGSQL_USER_NAME="postgres",
        PGSQL_USER_PASS="Srx20130126.",
    )

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com")

    def parse(self, request, response):
        title = response.xpath("//title/text()").extract_first()  # 取标题
        for i in range(10):
            item = Item()  # 声明一个item
            item.table_name = "test_postgresql"
            item.title = title + str(666)  # 给item属性赋值
            item.index = i + 5
            item.id = i
            item.c = "777"
            yield item  # 返回item， item会自动批量入库


if __name__ == "__main__":
    TestPostgreSQL().start()
