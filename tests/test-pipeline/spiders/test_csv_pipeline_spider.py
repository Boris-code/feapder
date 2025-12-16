# -*- coding: utf-8 -*-
"""
Created on 2025-12-16 14:52:29
---------
@summary:
---------
@author: Boris
"""

import feapder
from items import *


class TestCsvPipelineSpider(feapder.AirSpider):
    def start_requests(self):
        for i in range(100):
            yield feapder.Request("https://baidu.com", page=i)

    def parse(self, request, response):
        # 提取网站title
        title = response.xpath("//title/text()").extract_first()
        item = spider_data_item.SpiderDataItem()  # 声明一个item
        item.title = title  # 给item属性赋值
        yield item  # 返回item， item会自动批量入库


if __name__ == "__main__":
    TestCsvPipelineSpider().start()
