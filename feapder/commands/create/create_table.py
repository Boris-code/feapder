# -*- coding: utf-8 -*-
"""
Created on 2018-08-28 17:38:43
---------
@summary: 根据json生成表
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import sys
import time

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.db.mysqldb import MysqlDB
from feapder.utils.tools import key2underline


class CreateTable:
    def __init__(self):
        self._db = MysqlDB()

    def is_vaild_date(self, date):
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
            if self.is_vaild_date(value):
                if ":" in value:
                    key_type = "datetime"
                else:
                    key_type = "date"
            elif len(value) > 255:
                key_type = "text"
            else:
                key_type = "varchar(255)"

        return key_type

    def get_data(self):
        """
        @summary: 从控制台读取多行
        ---------
        ---------
        @result:
        """
        data = ""
        while True:
            line = sys.stdin.readline().strip()
            if not line:
                break
            data += line

        return tools.get_json(data)

    def create(self, table_name):
        # 输入表字段
        print('请输入表数据 json格式 如 {"name":"张三"}\n等待输入：\n')
        data = self.get_data()

        if not isinstance(data, dict):
            raise Exception("表数据格式不正确")

        # 拼接表结构
        sql = """
            CREATE TABLE `{db}`.`{table_name}` (
                `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT COMMENT 'id 自动递增',
                {other_key}
                `gtime` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
                PRIMARY KEY (`id`),
                {unique}
            ) COMMENT='';
        """

        print("请设置注释 回车跳过")
        other_key = ""
        for key, value in data.items():
            key = key2underline(key)
            key_type = self.get_key_type(value)

            comment = input("%s : %s  -> comment：" % (key, key_type))

            other_key += "`{key}` {key_type} COMMENT '{comment}',\n                ".format(
                key=key, key_type=key_type, comment=comment
            )

        print("\n")

        while True:
            is_need_batch_date = input("是否添加batch_date 字段 （y/n）:")
            if is_need_batch_date == "y":
                other_key += "`{key}` {key_type} COMMENT '{comment}',\n                ".format(
                    key="batch_date", key_type="date", comment="批次时间"
                )
                break
            elif is_need_batch_date == "n":
                break

        print("\n")

        while True:
            unique = input("请设置唯一索引, 多个逗号间隔\n等待输入：\n").replace("，", ",")
            if unique:
                break
        unique = "UNIQUE `idx` USING BTREE (`%s`) comment ''" % "`,`".join(
            unique.split(",")
        )

        sql = sql.format(
            db=setting.MYSQL_DB,
            table_name=table_name,
            other_key=other_key,
            unique=unique,
        )
        print(sql)
        self._db.execute(sql)
        print("\n%s 创建成功" % table_name)