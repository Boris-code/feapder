# -*- coding: utf-8 -*-
"""
Created on 2021-03-30 10:27:21
---------
@summary:
---------
@author: Boris
"""

import feapder
from feapder import Item


class TestAirSpiderItem(feapder.AirSpider):
    __custom_setting__ = dict(
        MYSQL_IP="localhost",
        MYSQL_PORT=3306,
        MYSQL_DB="feapder",
        MYSQL_USER_NAME="feapder",
        MYSQL_USER_PASS="feapder123",
        ITEM_FILTER_ENABLE=True,  # item 去重
        ITEM_FILTER_SETTING = dict(
            filter_type=4  # 永久去重（BloomFilter） = 1 、内存去重（MemoryFilter） = 2、 临时去重（ExpireFilter）= 3、轻量去重（LiteFilter）= 4
        )
    )

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com")

    def parse(self, request, response):
        title = response.xpath("string(//title)").extract_first()
        for i in range(3):
            item = Item()
            item.table_name = "spider_data"
            item.url = request.url
            item.title = title
            yield item


if __name__ == "__main__":
    TestAirSpiderItem().start()
