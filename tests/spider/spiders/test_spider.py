# -*- coding: utf-8 -*-
"""
Created on 2021-02-08 16:06:12
---------
@summary:
---------
@author: Boris
"""

import feapder
from items import *


class TestSpider(feapder.Spider):
    def start_requests(self):
        for i in range(1):
            yield feapder.Request(f"https://www.baidu.com#{i}", callback=self.parse)

    def validate(self, request, response):
        if response.status_code != 200:
            raise Exception("response code not 200")  # 重试

        # if "哈哈" not in response.text:
        #     return False # 抛弃当前请求

    def parse(self, request, response):
        title = response.xpath("//title/text()").extract_first()  # 取标题
        item = spider_data_item.SpiderDataItem()  # 声明一个item
        item.title = title  # 给item属性赋值
        yield item  # 返回item， item会自动批量入库


if __name__ == '__main__':
    spider = TestSpider(redis_key="feapder3:test_spider", thread_count=100)
    spider.start()