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


class TestAirSpider(feapder.AirSpider):
    def start_requests(self, *args, **kws):
        yield feapder.Request("https://www.baidu.com")

    def download_midware(self, request):
        # request.headers = {'User-Agent': ""}
        # request.proxies = {"https":"https://12.12.12.12:6666"}
        # request.cookies = {}
        return request

    def parse(self, request, response):
        print(response.xpath("//title").extract_first())


if __name__ == "__main__":
    TestAirSpider().start()
