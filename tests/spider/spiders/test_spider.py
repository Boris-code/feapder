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
        yield feapder.Request("https://www.baidu.com", callback=self.parse)

    def validate(self, request, response):
        print(request.callback_name)
        if response.status_code != 200:
            raise Exception("response code not 200")  # 重试

        # if "哈哈" not in response.text:
        #     return False # 抛弃当前请求

    def parse(self, request, response):
        title = response.xpath("//title/text()").extract_first()  # 取标题
        item = spider_data_item.SpiderDataItem()  # 声明一个item
        item.title = title  # 给item属性赋值
        yield item  # 返回item， item会自动批量入库
