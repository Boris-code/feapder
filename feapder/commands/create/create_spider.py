# -*- coding: utf-8 -*-
"""
Created on 2018-08-28 17:38:43
---------
@summary: 创建spider
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import getpass
import os
import re

import feapder.utils.tools as tools
from .create_init import CreateInit


def deal_file_info(file):
    file = file.replace("{DATE}", tools.get_current_date())
    file = file.replace("{USER}", getpass.getuser())

    return file


class CreateSpider:
    def __init__(self):
        self._create_init = CreateInit()

    def cover_to_underline(self, key):
        regex = "[A-Z]*"
        capitals = re.findall(regex, key)

        if capitals:
            for pos, capital in enumerate(capitals):
                if not capital:
                    continue
                if pos == 0:
                    if len(capital) > 1:
                        key = key.replace(capital, capital.lower() + "_", 1)
                    else:
                        key = key.replace(capital, capital.lower(), 1)
                else:
                    if len(capital) > 1:
                        key = key.replace(capital, "_" + capital.lower() + "_", 1)
                    else:
                        key = key.replace(capital, "_" + capital.lower(), 1)

        return key

    def get_spider_template(self, spider_type):
        if spider_type == 1:
            template_path = "air_spider_template.tmpl"
        elif spider_type == 2:
            template_path = "spider_template.tmpl"
        elif spider_type == 3:
            template_path = "batch_spider_template.tmpl"
        else:
            raise ValueError("spider type error, support 1 2 3")

        template_path = os.path.abspath(
            os.path.join(__file__, "../../../templates", template_path)
        )
        with open(template_path, "r", encoding="utf-8") as file:
            spider_template = file.read()

        return spider_template

    def create_spider(self, spider_template, spider_name):
        spider_template = spider_template.replace("${spider_name}", spider_name)
        spider_template = deal_file_info(spider_template)
        return spider_template

    def save_spider_to_file(self, spider, spider_name):
        spider_underline = self.cover_to_underline(spider_name)
        spider_file = spider_underline + ".py"

        if os.path.exists(spider_file):
            confirm = input("%s 文件已存在 是否覆盖 (y/n).  " % spider_file)
            if confirm != "y":
                print("取消覆盖  退出")
                return

        with open(spider_file, "w", encoding="utf-8") as file:
            file.write(spider)
            print("\n%s 生成成功" % spider_name)

        self._create_init.create()

    def create(self, spider_name, spider_type):
        # 检查spider_name
        if not re.search("^[a-zA-Z][a-zA-Z0-9_]*$", spider_name):
            print("爬虫命名不符合规范，请用蛇形或驼峰命名方式")
            return

        if spider_name.islower():
            spider_name = tools.key2hump(spider_name)
        spider_template = self.get_spider_template(spider_type)
        spider = self.create_spider(spider_template, spider_name)
        self.save_spider_to_file(spider, spider_name)
