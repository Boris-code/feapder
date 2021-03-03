# -*- coding: utf-8 -*-
"""
Created on 2021-03-02 23:42:40
---------
@summary:
---------
@author: liubo
"""

import feapder


class TencentNewsParser(feapder.BaseParser):
    """
    注意 这里继承的是BaseParser，而不是Spider
    """
    def start_requests(self):
        yield feapder.Request("https://news.qq.com/")

    def parse(self, request, response):
        title = response.xpath("//title/text()").extract_first()
        print(title)
