# -*- coding: utf-8 -*-
"""
Created on 2021-02-08 16:09:47
---------
@summary:
---------
@author: Boris
"""

import feapder
from items import *


class TestSpider(feapder.BatchSpider):
    # def init_task(self):
    #     pass

    def start_requests(self, task):
        # task 为在任务表中取出的每一条任务
        id, url = task  # id， url为所取的字段，main函数中指定的
        yield feapder.Request(url, task_id=id)

    def parser(self, request, response):
        title = response.xpath('//title/text()').extract_first()  # 取标题
        item = spider_data_item.SpiderDataItem()  # 声明一个item
        item.title = title  # 给item属性赋值
        yield item  # 返回item， item会自动批量入库
        yield self.update_task_batch(request.task_id, 1) # 更新任务状态为1

    def exception_request(self, request, response):
        """
        @summary: 请求或者parser里解析出异常的request
        ---------
        @param request:
        @param response:
        ---------
        @result: request / callback / None (返回值必须可迭代)
        """

        pass

    def failed_request(self, request, response):
        """
        @summary: 超过最大重试次数的request
        ---------
        @param request:
        ---------
        @result: request / item / callback / None (返回值必须可迭代)
        """

        yield request
        yield self.update_task_batch(request.task_id, -1) # 更新任务状态为-1


