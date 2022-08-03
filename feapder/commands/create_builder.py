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

from terminal_layout import Fore
from terminal_layout.extensions.choice import Choice, StringStyle

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
        help="创建爬虫 如 feapder create -s <spider_name>",
        metavar="",
    )
    spider.add_argument(
        "-i",
        "--item",
        help="创建item 如 feapder create -i <table_name> 支持模糊匹配 如 feapder create -i %%table_name%%",
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
    spider.add_argument("-c", "--cookies", help="创建cookie", action="store_true")
    spider.add_argument("--params", help="解析地址中的参数", action="store_true")
    spider.add_argument(
        "--setting", help="创建全局配置文件" "feapder create --setting", action="store_true"
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
        c = Choice(
            "请选择Item类型",
            ["Item", "Item 支持字典赋值", "UpdateItem", "UpdateItem 支持字典赋值"],
            icon_style=StringStyle(fore=Fore.green),
            selected_style=StringStyle(fore=Fore.green),
        )

        choice = c.get_choice()
        if choice:
            index, value = choice
            item_name = args.item
            item_type = "Item" if index <= 1 else "UpdateItem"
            support_dict = index in (1, 3)

            CreateItem().create(item_name, item_type, support_dict)

    elif args.spider:
        c = Choice(
            "请选择爬虫模板",
            ["AirSpider", "Spider", "TaskSpider", "BatchSpider"],
            icon_style=StringStyle(fore=Fore.green),
            selected_style=StringStyle(fore=Fore.green),
        )

        choice = c.get_choice()
        if choice:
            index, spider_type = choice
            spider_name = args.spider
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

    elif args.cookies:
        CreateCookies().create()

    elif args.setting:
        CreateSetting().create()

    elif args.params:
        CreateParams().create()

    else:
        spider.print_help()


if __name__ == "__main__":
    main()
