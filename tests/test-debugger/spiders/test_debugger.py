# -*- coding: utf-8 -*-
"""
Created on 2023-06-09 20:26:47
---------
@summary:
---------
@author: Boris
"""

import feapder


class TestDebugger(feapder.Spider):
    def start_requests(self):
        yield feapder.Request("https://spidertools.cn", render=True)

    def parse(self, request, response):
        # 提取网站title
        print(response.xpath("//title/text()").extract_first())
        # 提取网站描述
        print(response.xpath("//meta[@name='description']/@content").extract_first())
        print("网站地址: ", response.url)


if __name__ == "__main__":
    TestDebugger.to_DebugSpider(
        request=feapder.Request("https://spidertools.cn", render=True), redis_key="test:xxx"
    ).start()
