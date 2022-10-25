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
    __custom_setting__ = dict(
        REQUEST_FILTER_ENABLE=True,  # request 去重
        # REQUEST_FILTER_SETTING=dict(
        #     filter_type=3,  # 永久去重（BloomFilter） = 1 、内存去重（MemoryFilter） = 2、 临时去重（ExpireFilter）= 3、 轻量去重（LiteFilter）= 4
        #     expire_time=2592000,  # 过期时间1个月
        # ),
        REQUEST_FILTER_SETTING=dict(
            filter_type=4,  # 永久去重（BloomFilter） = 1 、内存去重（MemoryFilter） = 2、 临时去重（ExpireFilter）= 3、 轻量去重（LiteFilter）= 4
        ),
    )

    def start_requests(self, *args, **kws):
        for i in range(200):
            yield feapder.Request("https://www.baidu.com")

    def parse(self, request, response):
        print(response.bs4().title)


if __name__ == "__main__":
    TestAirSpider(thread_count=1).start()
