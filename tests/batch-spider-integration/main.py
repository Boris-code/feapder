# -*- coding: utf-8 -*-
"""
Created on 2021-03-02 23:38:24
---------
@summary: 爬虫入口
---------
@author: Boris
"""

from feapder import ArgumentParser
from feapder import BatchSpider

from spiders import *


def batch_spider_integration_test(args):
    """
    BatchSpider集成测试
    """

    spider = BatchSpider(
        task_table="batch_spider_integration_task",  # mysql中的任务表
        batch_record_table="batch_spider_integration_batch_record",  # mysql中的批次记录表
        batch_name="批次爬虫集成测试",  # 批次名字
        batch_interval=7,  # 批次时间 天为单位 若为小时 可写 1 / 24
        task_keys=["id", "url", "parser_name"],  # 集成批次爬虫，需要将批次爬虫的名字取出来，任务分发时才知道分发到哪个模板上
        redis_key="feapder:test_batch_spider_integration",  # redis中存放request等信息的根key
        task_state="state",  # mysql中任务状态字段
    )

    # 集成
    spider.add_parser(sina_news_parser.SinaNewsParser)
    spider.add_parser(tencent_news_parser.TencentNewsParser)

    if args == 1:
        spider.start_monitor_task()
    elif args == 2:
        spider.start()


if __name__ == "__main__":
    parser = ArgumentParser(description="批次爬虫集成测试")

    parser.add_argument(
        "--batch_spider_integration_test",
        type=int,
        nargs=1,
        help="批次爬虫集成测试(1|2）",
        function=batch_spider_integration_test,
    )

    parser.start()

    # 运行
    # 下发任务及监控进度 python3 main.py --batch_spider_integration_test 1
    # 采集 python3 main.py --batch_spider_integration_test 2
