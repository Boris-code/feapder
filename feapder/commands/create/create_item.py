# -*- coding: utf-8 -*-
"""
Created on 2018-08-28 17:38:43
---------
@summary: 创建item
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import getpass
import os

import feapder.utils.tools as tools
from feapder.db.mysqldb import MysqlDB
from .create_init import CreateInit


def deal_file_info(file):
    file = file.replace("{DATE}", tools.get_current_date())
    file = file.replace("{USER}", getpass.getuser())

    return file


class CreateItem:
    def __init__(self):
        self._db = MysqlDB()
        self._create_init = CreateInit()

    def select_columns(self, table_name):
        # sql = 'SHOW COLUMNS FROM ' + table_name
        sql = "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA, COLUMN_KEY, COLUMN_COMMENT FROM INFORMATION_SCHEMA.Columns WHERE table_name = '{}'".format(
            table_name
        )
        columns = self._db.find(sql)

        return columns

    def select_tables_name(self, tables_name):
        """
        @summary:
        ---------
        @param tables_name: 一类tables 如 qidian*
        ---------
        @result:
        """
        sql = (
            "select table_name from information_schema.tables where table_name like '%s'"
            % tables_name
        )
        tables_name = self._db.find(sql)

        return tables_name

    def convert_table_name_to_hump(self, table_name):
        """
        @summary: 格式化表明为驼峰格式
        ---------
        @param table:
        ---------
        @result:
        """
        table_hump_format = ""

        words = table_name.split("_")
        for word in words:
            table_hump_format += word.capitalize()  # 首字母大写

        return table_hump_format

    def get_item_template(self):
        templete_path = os.path.abspath(
            os.path.join(__file__, "../../../templates/item_template.tmpl")
        )
        with open(templete_path, "r", encoding="utf-8") as file:
            item_template = file.read()

        return item_template

    def create_item(self, item_template, columns, table_name, support_dict):
        table_name_hump_format = self.convert_table_name_to_hump(table_name)
        # 组装 类名
        item_template = item_template.replace("${item_name}", table_name_hump_format)
        if support_dict:
            item_template = item_template.replace("${table_name}", table_name + " 1")
        else:
            item_template = item_template.replace("${table_name}", table_name)

        # 组装 属性
        propertys = ""
        for column in columns:
            column_name = column[0]
            column_type = column[1]
            is_nullable = column[2]
            column_default = column[3]
            column_extra = column[4]
            column_key = column[5]
            column_comment = column[6]

            try:
                value = (
                    "kwargs.get('{column_name}')".format(column_name=column_name)
                    if support_dict
                    else (
                        column_default != "CURRENT_TIMESTAMP" and column_default or None
                    )
                    and eval(column_default)
                )
            except:
                value = (
                    "kwargs.get('{column_name}')".format(column_name=column_name)
                    if support_dict
                    else (
                        column_default != "CURRENT_TIMESTAMP" and column_default or None
                    )
                    and column_default
                )

            if column_extra == "auto_increment" or column_default is not None:
                propertys += (
                    "# self.{column_name} = {value}  # type : {column_type} | allow_null : {is_nullable} | key : {column_key} | default_value : {column_default} | extra : {column_extra} | column_comment : {column_comment}".format(
                        column_name=column_name,
                        value=value,
                        column_type=column_type,
                        is_nullable=is_nullable,
                        column_key=column_key,
                        column_default=column_default,
                        column_extra=column_extra,
                        column_comment=column_comment,
                    )
                    + "\n"
                    + " " * 8
                )

            else:
                if value is None or isinstance(value, (float, int)) or support_dict:
                    propertys += (
                        "self.{column_name} = {value}  # type : {column_type} | allow_null : {is_nullable} | key : {column_key} | default_value : {column_default} | extra : {column_extra}| column_comment : {column_comment}".format(
                            column_name=column_name,
                            value=value,
                            column_type=column_type,
                            is_nullable=is_nullable,
                            column_key=column_key,
                            column_default=column_default,
                            column_extra=column_extra,
                            column_comment=column_comment,
                        )
                        + "\n"
                        + " " * 8
                    )
                else:
                    propertys += (
                        "self.{column_name} = '{value}'  # type : {column_type} | allow_null : {is_nullable} | key : {column_key} | default_value : {column_default} | extra : {column_extra}| column_comment : {column_comment}".format(
                            column_name=column_name,
                            value=value,
                            column_type=column_type,
                            is_nullable=is_nullable,
                            column_key=column_key,
                            column_default=column_default,
                            column_extra=column_extra,
                            column_comment=column_comment,
                        )
                        + "\n"
                        + " " * 8
                    )

        item_template = item_template.replace("${propertys}", propertys.strip())
        item_template = deal_file_info(item_template)

        return item_template

    def save_template_to_file(self, item_template, table_name):
        item_file = table_name + "_item.py"
        if os.path.exists(item_file):
            confirm = input("%s 文件已存在 是否覆盖 (y/n).  " % item_file)
            if confirm != "y":
                print("取消覆盖  退出")
                return

        with open(item_file, "w", encoding="utf-8") as file:
            file.write(item_template)
            print("\n%s 生成成功" % item_file)

        self._create_init.create()

    def create(self, tables_name, support_dict):
        input_tables_name = tables_name

        tables_name = self.select_tables_name(tables_name)
        if not tables_name:
            print(tables_name)
            tip = "mysql数据库中无 %s 表 " % input_tables_name
            raise KeyError(tip)

        for table_name in tables_name:
            table_name = table_name[0]

            columns = self.select_columns(table_name)
            item_template = self.get_item_template()
            item_template = self.create_item(
                item_template, columns, table_name, support_dict
            )
            self.save_template_to_file(item_template, table_name)
