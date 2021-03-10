# -*- coding: utf-8 -*-
"""
Created on 2021-03-09 20:45:36
---------
@summary:
---------
@author: liubo
"""

import feapder
from feapder import Item
from feapder.utils import tools


class JdSpider(feapder.BatchSpider):
    # 自定义数据库，若项目中有setting.py文件，此自定义可删除
    __custom_setting__ = dict(
        REDISDB_IP_PORTS="localhost:6379",
        REDISDB_DB=0,
        MYSQL_IP="localhost",
        MYSQL_PORT=3306,
        MYSQL_DB="feapder",
        MYSQL_USER_NAME="feapder",
        MYSQL_USER_PASS="feapder123",
    )

    def start_requests(self, task):
        task_id, item_id = task
        url = "https://item.jd.com/{}.html".format(item_id)
        yield feapder.Request(url, task_id=task_id)  # 携带task_id字段

    def parse(self, request, response):
        title = response.xpath("string(//div[@class='sku-name'])").extract_first(default="").strip()

        item = Item()
        item.table_name = "jd_item"  # 指定入库的表名
        item.title = title
        item.batch_date = self.batch_date  # 获取批次信息，批次信息框架自己维护
        item.crawl_time = tools.get_current_date()  # 获取当前时间
        yield item  # 自动批量入库
        yield self.update_task_batch(request.task_id, 1)  # 更新任务状态


if __name__ == "__main__":
    spider = JdSpider(
        redis_key="feapder:jd_item",  # redis中存放任务等信息key前缀
        task_table="jd_item_task",  # mysql中的任务表
        task_keys=["id", "item_id"],  # 需要获取任务表里的字段名，可添加多个
        task_state="state",  # mysql中任务状态字段
        batch_record_table="jd_item_batch_record",  # mysql中的批次记录表，自动生成
        batch_name="京东商品爬虫(周度全量)",  # 批次名字
        batch_interval=7,  # 批次周期 天为单位 若为小时 可写 1 / 24
    )

    # 下面两个启动函数 相当于 master、worker。需要分开运行
    # spider.start_monitor_task() # maser: 下发及监控任务
    spider.start()  # worker: 采集
