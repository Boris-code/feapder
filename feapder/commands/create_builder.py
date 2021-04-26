# -*- coding: utf-8 -*-
"""
Created on 2021/2/8 11:21 上午
---------
@summary: 生成器
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import argparse
import feapder.setting as setting
from feapder.commands.create import *


def main():
    spider = argparse.ArgumentParser(description="生成器")

    spider.add_argument(
        "-p", "--project", help="创建项目 如 feapder create -p <project_name>", metavar=""
    )
    spider.add_argument(
        "-s",
        "--spider",
        nargs="+",
        help="创建爬虫\n"
        "如 feapder create -s <spider_name> <spider_type> "
        "spider_type=1  AirSpider; "
        "spider_type=2  Spider; "
        "spider_type=3  BatchSpider;",
        metavar="",
    )
    spider.add_argument(
        "-i",
        "--item",
        nargs="+",
        help="创建item 如 feapder create -i test 则生成test表对应的item。 "
        "支持like语法模糊匹配所要生产的表。 "
        "若想生成支持字典方式赋值的item，则create -item test 1",
        metavar="",
    )
    spider.add_argument(
        "-t", "--table", help="根据json创建表 如 feapder create -t <table_name>", metavar=""
    )
    spider.add_argument(
        "-init", help="创建__init__.py 如 feapder create -init", action="store_true"
    )
    spider.add_argument("-j", "--json", help="创建json", action="store_true")
    spider.add_argument("-sj", "--sort_json", help="创建有序json", action="store_true")
    
    # 创建setting文件
    spider.add_argument(
        "--setting",
        help="创建全局配置文件\n"
        "feapder create -setting",
        action="store_true",
    )
    
    # 指定数据库
    spider.add_argument("--host", type=str, help="mysql 连接地址", metavar="")
    spider.add_argument("--port", type=str, help="mysql 端口", metavar="")
    spider.add_argument("--username", type=str, help="mysql 用户名", metavar="")
    spider.add_argument("--password", type=str, help="mysql 密码", metavar="")
    spider.add_argument("--db", type=str, help="mysql 数据库名", metavar="")
    args = spider.parse_args()

    if args.host:
        setting.MYSQL_IP = args.host
    if args.port:
        setting.MYSQL_PORT = int(args.port)
    if args.username:
        setting.MYSQL_USER_NAME = args.username
    if args.password:
        setting.MYSQL_USER_PASS = args.password
    if args.db:
        setting.MYSQL_DB = args.db

    if args.item:
        item_name, *support_dict = args.item
        support_dict = bool(support_dict)
        CreateItem().create(item_name, support_dict)

    elif args.spider:
        spider_name, *spider_type = args.spider
        if not spider_type:
            spider_type = 1
        else:
            spider_type = spider_type[0]
        try:
            spider_type = int(spider_type)
        except:
            raise ValueError("spider_type error, support 1, 2, 3")
        CreateSpider().create(spider_name, spider_type)

    elif args.project:
        CreateProject().create(args.project)

    elif args.table:
        CreateTable().create(args.table)

    elif args.init:
        CreateInit().create()

    elif args.json:
        CreateJson().create()

    elif args.sort_json:
        CreateJson().create(sort_keys=True)

    elif args.setting:
        CreateSetting().create()
    
if __name__ == "__main__":
    main()
