# -*- coding: utf-8 -*-
"""
Created on 2021-03-07 21:27:00
---------
@summary:
---------
@author: Boris
"""

import feapder


class TestSpiderParams(feapder.Spider):
    # 自定义数据库，若项目中有setting.py文件，此自定义可删除
    __custom_setting__ = dict(
        REDISDB_IP_PORTS="localhost:6379", REDISDB_USER_PASS="", REDISDB_DB=0
    )

    def start_requests(self):
        for i in range(100):
            print(f"下发任务 {i}")
            yield feapder.Request(f"https://www.baidu.com?p={i}")

    def parse(self, request, response):
        print(request.url)


if __name__ == "__main__":
    spider = TestSpiderParams(redis_key="feapder:test_spider_params", min_task_count=10)
    spider.start_monitor_task()
    # spider.start()
