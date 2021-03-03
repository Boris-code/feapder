# -*- coding: utf-8 -*-
"""
Created on 2021-03-02 23:42:40
---------
@summary:
---------
@author: liubo
"""

import feapder


class TencentNewsParser(feapder.BatchParser):
    """
    注意 这里继承的是BatchParser，而不是BatchSpider
    """
    def start_requests(self, task):
        task_id = task[0]
        url = task[1]
        yield feapder.Request(url, task_id=task_id)

    def init_task(self):
        print("21321312132132131312")

    def parse(self, request, response):
        title = response.xpath("//title/text()").extract_first()
        print(self.name, title)
        yield self.update_task_batch(request.task_id, 1)
