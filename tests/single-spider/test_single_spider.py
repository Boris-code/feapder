# -*- coding: utf-8 -*-
"""
Created on 2020/4/22 10:41 PM
---------
@summary:
---------
@author: Boris
@email: boris@bzkj.tech
"""

import feapder


class TestSingleSpider(feapder.SingleSpider):
    def start_requests(self, *args, **kws):
        yield feapder.Request("https://www.baidu.com")

    def parser(self, request, response):
        print(response.xpath("//title").extract_first())


if __name__ == "__main__":
    TestSingleSpider().start()
