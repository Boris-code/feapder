# -*- coding: utf-8 -*-
"""
Created on 2018-08-28 17:38:43
---------
@summary: 根据json生成表
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import time

import pyperclip

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.db.mysqldb import MysqlDB
from feapder.utils.tools import key2underline


class CreateTable:
    def __init__(self):
        self._db = MysqlDB()

    def is_valid_date(self, date):
        try:
            if ":" in date:
                time.strptime(date, "%Y-%m-%d %H:%M:%S")
            else:
                time.strptime(date, "%Y-%m-%d")
            return True
        except:
            return False

    def get_key_type(self, value):
        try:
            value = eval(value)
        except:
            value = value

        key_type = "varchar(255)"
        if isinstance(value, int):
            key_type = "int"
        elif isinstance(value, float):
            key_type = "double"
        elif isinstance(value, str):
            if self.is_valid_date(value):
                if ":" in value:
                    key_type = "datetime"
                else:
                    key_type = "date"
            elif len(value) > 50:
                key_type = "text"
            else:
                key_type = "varchar(255)"
        elif isinstance(value, (dict, list)):
            key_type = "longtext"

        return key_type

    def get_data(self):
        """
        @summary: 从控制台读取多行
        ---------
        ---------
        @result:
        """
        input("请复制json格式数据, 复制后按任意键读取剪切板内容\n")

        text = pyperclip.paste()
        print(text + "\n")

        return tools.get_json(text)

    def create(self, table_name):
        # 输入表字段
        data = self.get_data()

        if not isinstance(data, dict):
            raise Exception("表数据格式不正确")

        # 拼接表结构
        sql = """
            CREATE TABLE `{db}`.`{table_name}` (
                `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT COMMENT 'id主键',
                {other_key}
                `crawl_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
                {unique}
                PRIMARY KEY (`id`)
            ) COMMENT='';
        """

        # print("请设置注释 回车跳过")
        other_key = ""
        for key, value in data.items():
            key = key2underline(key)
            comment = ""
            if key == "id":
                key = "data_id"
                comment = "原始数据id"

            key_type = self.get_key_type(value)

            # comment = input("%s : %s  -> comment：" % (key, key_type))

            other_key += (
                "`{key}` {key_type} COMMENT '{comment}',\n                ".format(
                    key=key, key_type=key_type, comment=comment
                )
            )

        print("\n")

        while True:
            yes = input("是否添加批次字段 batch_date（y/n）:")
            if yes == "y":
                other_key += (
                    "`{key}` {key_type} COMMENT '{comment}',\n                ".format(
                        key="batch_date", key_type="date", comment="批次时间"
                    )
                )
                break
            elif yes == "n":
                break

        print("\n")

        while True:
            yes = input("是否设置唯一索引（y/n）:")
            if yes == "y":
                unique = input("请设置唯一索引, 多个逗号间隔\n等待输入：\n").replace("，", ",")
                if unique:
                    unique = "UNIQUE `idx` USING BTREE (`%s`) comment ''," % "`,`".join(
                        unique.split(",")
                    )
                    break
            elif yes == "n":
                unique = ""
                break

        sql = sql.format(
            db=setting.MYSQL_DB,
            table_name=table_name,
            other_key=other_key.strip(),
            unique=unique,
        )
        print(sql)

        if self._db.execute(sql):
            print("\n%s 创建成功" % table_name)
            print("注意手动检查下字段类型，确保无误！！！")
        else:
            print("\n%s 创建失败" % table_name)
