# -*- coding: utf-8 -*-
"""
Created on 2021-03-02 23:40:37
---------
@summary:
---------
@author: Boris
"""

import feapder


class SinaNewsParser(feapder.BatchParser):
    """
    注意 这里继承的是BatchParser，而不是BatchSpider
    """

    def start_requests(self, task):
        task_id = task[0]
        url = task[1]
        yield feapder.Request(url, task_id=task_id)

    def parse(self, request, response):
        title = response.xpath("//title/text()").extract_first()
        print(self.name, title)
        yield self.update_task_batch(request.task_id, 1)
