# -*- coding: utf-8 -*-
"""
Created on 2022-06-10 14:30:54
---------
@summary:
---------
@author: Boris
"""

import feapder
from feapder import ArgumentParser


class TestTaskSpider(feapder.TaskSpider):
    def start_requests(self, task):
        task_id, url = task
        yield feapder.Request(url, task_id=task_id)

    def parse(self, request, response):
        # 提取网站title
        print(response.xpath("//title/text()").extract_first())
        # 提取网站描述
        print(response.xpath("//meta[@name='description']/@content").extract_first())
        print("网站地址: ", response.url)
        yield self.update_task_batch(request.task_id)


def start(args):
    spider = TestTaskSpider(
        task_table="spider_task",
        task_keys=["id", "url"],
        redis_key="test:task_spider",
        keep_alive=True,
    )
    if args == 1:
        spider.start_monitor_task()
    else:
        spider.start()


if __name__ == "__main__":
    parser = ArgumentParser(description="测试TaskSpider")

    parser.add_argument("--start", type=int, nargs=1, help="(1|2）", function=start)

    parser.start()

    # 下发任务  python3 test_task_spider.py --start 1
    # 采集  python3 test_task_spider.py --start 2
