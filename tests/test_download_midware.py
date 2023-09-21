# -*- coding: utf-8 -*-
"""
Created on 2023/9/21 13:59
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import feapder


def download_midware(request):
    print("outter download_midware")
    return request


class TestAirSpider(feapder.AirSpider):
    def start_requests(self):
        yield feapder.Request(
            "https://www.baidu.com", download_midware=download_midware
        )

    def parse(self, request, response):
        print(request, response)


class TestSpiderSpider(feapder.Spider):
    def start_requests(self):
        yield feapder.Request(
            "https://www.baidu.com", download_midware=[download_midware, self.download_midware]
        )

    def download_midware(self, request):
        print("class download_midware")
        return request

    def parse(self, request, response):
        print(request, response)


if __name__ == "__main__":
    # TestAirSpider().start()
    TestSpiderSpider(redis_key="test").start()
