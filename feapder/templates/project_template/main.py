# -*- coding: utf-8 -*-
"""
Created on {DATE}
---------
@summary: 爬虫入口
---------
@author: {USER}
"""

from feapder import ArgumentParser

from spiders import *

def crawl_xxx():
    """
    AirSpider爬虫
    """
    spider = xxx.XXXSpider()
    spider.start()

def crawl_xxx():
    """
    Spider爬虫
    """
    spider = xxx.XXXSpider(redis_key="xxx:xxx")
    spider.start()


def crawl_xxx(args):
    """
    BatchSpider爬虫
    """
    spider = xxx_spider.XXXSpider(
        task_table="",  # mysql中的任务表
        batch_record_table="",  # mysql中的批次记录表
        batch_name="xxx(周全)",  # 批次名字
        batch_interval=7,  # 批次时间 天为单位 若为小时 可写 1 / 24
        task_keys=["id", "xxx"],  # 需要获取任务表里的字段名，可添加多个
        redis_key="xxx:xxxx",  # redis中存放request等信息的根key
        task_state="state",  # mysql中任务状态字段
    )

    if args == 1:
        spider.start_monitor_task()
    elif args == 2:
        spider.start()
    elif args == 3:
        spider.init_task()


if __name__ == "__main__":
    parser = ArgumentParser(description="xxx爬虫")

    parser.add_argument(
        "--crawl_xxx", action="store_true", help="xxx爬虫", function=crawl_xxx
    )
    parser.add_argument(
        "--crawl_xxx", action="store_true", help="xxx爬虫", function=crawl_xxx
    )
    parser.add_argument(
        "--crawl_xxx",
        type=int,
        nargs=1,
        help="xxx爬虫",
        choices=[1, 2, 3],
        function=crawl_xxx,
    )

    parser.start()

    # main.py作为爬虫启动的统一入口，提供命令行的方式启动多个爬虫，若只有一个爬虫，可不编写main.py
    # 将上面的xxx修改为自己实际的爬虫名
    # 查看运行命令 python main.py --help
    # AirSpider与Spider爬虫运行方式 python main.py --crawl_xxx
    # BatchSpider运行方式
    # 1. 下发任务：python main.py --crawl_xxx 1
    # 2. 采集：python main.py --crawl_xxx 2
    # 3. 重置任务：python main.py --crawl_xxx 3

