# -*- coding: utf-8 -*-
"""
Created on 2021/2/8 11:21 上午
---------
@summary: 生成器
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import click
from terminal_layout import Fore
from terminal_layout.extensions.choice import Choice, StringStyle

import feapder.setting as setting
from feapder.commands.create import *


@click.command(name="create", short_help="create project、spider、item and so on", context_settings=dict(help_option_names=['-h', '--help']), no_args_is_help=True)
@click.option("-p", "--project", help="创建项目 如 feapder create -p <project_name>", metavar="")
@click.option("-s", "--spider", help="创建爬虫 如 feapder create -s <spider_name>", metavar="")
@click.option("-i", "--item", help=r"创建item 如 feapder create -i <table_name> 支持模糊匹配 如 feapder create -i %%table_name%%",
              metavar="")
@click.option("-t", "--table", help="根据json创建表 如 feapder create -t <table_name>", metavar="")
@click.option("-init", help="创建__init__.py 如 feapder create -init", is_flag=True)
@click.option("-j", "--json", help="创建json", is_flag=True)
@click.option("-sj", "--sort_json", help="创建有序json", is_flag=True)
@click.option("--params", help="解析地址中的参数", is_flag=True)
@click.option("--setting", help="创建全局配置文件", is_flag=True)
# 指定数据库
@click.option("--host", help="mysql 连接地址", type=str, metavar="")
@click.option("--port", help="mysql 端口", type=str, metavar="")
@click.option("--username", help="mysql 用户名", type=str, metavar="")
@click.option("--password", help="mysql 密码", type=str, metavar="")
@click.option("--db", help="mysql 数据库名", type=str, metavar="")
def main(**kwargs):
    """
    生成器
    """

    if kwargs.get("host", ""):
        setting.MYSQL_IP = kwargs["host"]
    if kwargs.get("port", ""):
        setting.MYSQL_PORT = int(kwargs["port"])
    if kwargs.get("username", ""):
        setting.MYSQL_USER_NAME = kwargs["username"]
    if kwargs.get("password", ""):
        setting.MYSQL_USER_PASS = kwargs["password"]
    if kwargs.get("db", ""):
        setting.MYSQL_DB = kwargs["db"]

    if kwargs.get("item", ""):
        c = Choice(
            "请选择Item类型",
            ["Item", "Item 支持字典赋值", "UpdateItem", "UpdateItem 支持字典赋值"],
            icon_style=StringStyle(fore=Fore.green),
            selected_style=StringStyle(fore=Fore.green),
        )

        choice = c.get_choice()
        if choice:
            index, value = choice
            item_name = kwargs["item"]
            item_type = "Item" if index <= 1 else "UpdateItem"
            support_dict = index in (1, 3)

            CreateItem().create(item_name, item_type, support_dict)

    elif kwargs.get("spider", ""):
        c = Choice(
            "请选择爬虫模板",
            ["AirSpider", "Spider", "TaskSpider", "BatchSpider"],
            icon_style=StringStyle(fore=Fore.green),
            selected_style=StringStyle(fore=Fore.green),
        )

        choice = c.get_choice()
        if choice:
            index, spider_type = choice
            spider_name = kwargs["spider"]
            CreateSpider().create(spider_name, spider_type)

    elif kwargs.get("project", ""):
        CreateProject().create(kwargs["project"])

    elif kwargs.get("table", ""):
        CreateTable().create(kwargs["table"])

    elif kwargs.get("init", ""):
        CreateInit().create()

    elif kwargs.get("json", ""):
        CreateJson().create()

    elif kwargs.get("sort_json", ""):
        CreateJson().create(sort_keys=True)

    elif kwargs.get("cookies", ""):
        CreateCookies().create()

    elif kwargs.get("setting", ""):
        CreateSetting().create()

    elif kwargs.get("params", ""):
        CreateParams().create()


if __name__ == "__main__":
    main()
