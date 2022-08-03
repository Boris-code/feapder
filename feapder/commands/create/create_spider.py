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
    file = file.replace("{USER}", os.getenv("FEAPDER_USER") or getpass.getuser())

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
        if spider_type == "AirSpider":
            template_path = "air_spider_template.tmpl"
        elif spider_type == "Spider":
            template_path = "spider_template.tmpl"
        elif spider_type == "TaskSpider":
            template_path = "task_spider_template.tmpl"
        elif spider_type == "BatchSpider":
            template_path = "batch_spider_template.tmpl"
        else:
            raise ValueError("spider type error, only support AirSpider、 Spider、TaskSpider、BatchSpider")

        template_path = os.path.abspath(
            os.path.join(__file__, "../../../templates", template_path)
        )
        with open(template_path, "r", encoding="utf-8") as file:
            spider_template = file.read()

        return spider_template

    def create_spider(self, spider_template, spider_name, file_name):
        spider_template = spider_template.replace("${spider_name}", spider_name)
        spider_template = spider_template.replace("${file_name}", file_name)
        spider_template = deal_file_info(spider_template)
        return spider_template

    def save_spider_to_file(self, spider, spider_name, file_name):
        if os.path.exists(file_name):
            confirm = input("%s 文件已存在 是否覆盖 (y/n).  " % file_name)
            if confirm != "y":
                print("取消覆盖  退出")
                return

        with open(file_name, "w", encoding="utf-8") as file:
            file.write(spider)
            print("\n%s 生成成功" % spider_name)

        if os.path.basename(os.path.dirname(os.path.abspath(file_name))) == "spiders":
            self._create_init.create()

    def create(self, spider_name, spider_type):
        # 检查spider_name
        if not re.search("^[a-zA-Z][a-zA-Z0-9_]*$", spider_name):
            print("爬虫命名不符合规范，请用蛇形或驼峰命名方式")
            return

        underline_format = self.cover_to_underline(spider_name)
        spider_name = tools.key2hump(underline_format)
        file_name = underline_format + ".py"

        print(spider_name, file_name)

        spider_template = self.get_spider_template(spider_type)
        spider = self.create_spider(spider_template, spider_name, file_name)
        self.save_spider_to_file(spider, spider_name, file_name)
