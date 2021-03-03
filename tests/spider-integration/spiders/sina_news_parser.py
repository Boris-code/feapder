# -*- coding: utf-8 -*-
"""
Created on 2021-03-02 23:40:37
---------
@summary:
---------
@author: liubo
"""

import feapder


class SinaNewsParser(feapder.BaseParser):
    def start_requests(self):
        """
        注意 这里继承的是BaseParser，而不是Spider
        """
        yield feapder.Request("https://news.sina.com.cn/")

    def parse(self, request, response):
        title = response.xpath("//title/text()").extract_first()
        print(title)
