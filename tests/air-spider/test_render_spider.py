# -*- coding: utf-8 -*-
"""
Created on 2020/4/22 10:41 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import feapder


class TestAirSpider(feapder.AirSpider):
    def start_requests(self, *args, **kws):
        yield feapder.Request("https://www.baidu.com", render=True)

    def download_midware(self, request):
        request.proxies = {
            "http": "http://xxx.xxx.xxx.xxx:8888",
            "https": "http://xxx.xxx.xxx.xxx:8888",
        }

    def parse(self, request, response):
        print(response.bs4().title)


if __name__ == "__main__":
    TestAirSpider(thread_count=1).start()
