# -*- coding: utf-8 -*-
"""
Created on 2021-02-08 16:06:12
---------
@summary:
---------
@author: Boris
"""

import feapder
from feapder import Item


class TestMongo(feapder.AirSpider):
    __custom_setting__ = dict(
        ITEM_PIPELINES=["feapder.pipelines.mongo_pipeline.MongoPipeline"],
        MONGO_IP="localhost",
        MONGO_PORT=27017,
        MONGO_DB="feapder",
        MONGO_USER_NAME="",
        MONGO_USER_PASS="",
    )

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com")

    def parse(self, request, response):
        title = response.xpath("//title/text()").extract_first()  # 取标题
        for i in range(10):
            item = Item()  # 声明一个item
            item.table_name = "test_mongo"
            item.title = title + str(i)  # 给item属性赋值
            item.i = i + 95
            yield item  # 返回item， item会自动批量入库


if __name__ == "__main__":
    TestMongo().start()
