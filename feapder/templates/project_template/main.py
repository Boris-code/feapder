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
    普通爬虫
    """
    spider = xxx.XXXSpider(redis_key="xxx:xxx")
    spider.start()


def crawl_xxx(args):
    """
    批次爬虫
    @param args: 1 / 2 / init
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
    elif args == "init":
        spider.init_task()


if __name__ == "__main__":
    parser = ArgumentParser(description="xxx爬虫")

    parser.add_argument(
        "--crawl_xxx", action="store_true", help="xxx", function=crawl_xxx
    )
    parser.add_argument(
        "--crawl_xxx", type=int, nargs=1, help="xxx(1|2）", function=crawl_xxx
    )

    parser.start()
