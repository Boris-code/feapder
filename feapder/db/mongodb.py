# -*- coding: utf-8 -*-
"""
Created on 2021-04-18 14:12:21
---------
@summary: 操作mongo数据库
---------
@author: Mkdir700
@email:  mkdir700@gmail.com
"""
import re
from typing import List, Dict, Optional
from urllib import parse

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, BulkWriteError

import feapder.setting as setting
from feapder.utils.log import log


class MongoDB:
    def __init__(
        self, ip=None, port=None, db=None, user_name=None, user_pass=None, **kwargs
    ):
        if not ip:
            ip = setting.MONGO_IP
        if not port:
            port = setting.MONGO_PORT
        if not db:
            db = setting.MONGO_DB
        if not user_name:
            user_name = setting.MONGO_USER_NAME
        if not user_pass:
            user_pass = setting.MONGO_USER_PASS

        self.client = MongoClient(
            host=ip, port=port, username=user_name, password=user_pass
        )
        self.db = self.get_database(db)

    @classmethod
    def from_url(cls, url, **kwargs):
        # mongodb://username:password@ip:port/db
        url_parsed = parse.urlparse(url)

        db_type = url_parsed.scheme.strip()
        if db_type != "mongodb":
            raise Exception(
                "url error, expect mongodb://username:password@ip:port/db, but get {}".format(
                    url
                )
            )

        connect_params = {}
        connect_params["ip"] = url_parsed.hostname.strip()
        connect_params["port"] = url_parsed.port
        connect_params["user_name"] = url_parsed.username.strip()
        connect_params["user_pass"] = url_parsed.password.strip()
        connect_params["db"] = url_parsed.path.strip("/").strip()

        connect_params.update(kwargs)
        return cls(**connect_params)

    def get_database(self, database, **kwargs) -> Database:
        """
        获取数据库对象
        @param database: 数据库名
        @return:
        """
        return self.client.get_database(database, **kwargs)

    def get_collection(self, coll_name, **kwargs) -> Collection:
        """
        根据集合名获取集合对象
        @param coll_name: 集合名
        @return:
        """
        return self.db.get_collection(coll_name, **kwargs)

    def find(
        self, coll_name: str, condition: Optional[Dict] = None, limit: int = 0, **kwargs
    ) -> List[Dict]:
        """
        @summary:
        无数据： 返回[]
        有数据： [{'_id': 'xx', ...}, ...]
        ---------
        @param coll_name: 集合名(表名)
        @param condition: 查询条件
        @param limit: 结果数量
        @param kwargs:
            更多参数 https://docs.mongodb.com/manual/reference/command/find/#command-fields

        ---------
        @result:
        """
        condition = {} if condition is None else condition
        command = {"find": coll_name, "filter": condition, "limit": limit}
        command.update(kwargs)
        result = self.run_command(command)
        cursor = result["cursor"]
        cursor_id = cursor["id"]
        dataset = cursor["firstBatch"]
        while True:
            if cursor_id == 0:
                break
            result = self.run_command(
                {
                    "getMore": cursor_id,
                    "collection": coll_name,
                    "batchSize": kwargs.get("batchSize", 100),
                }
            )
            cursor = result["cursor"]
            cursor_id = cursor["id"]
            dataset.extend(cursor["nextBatch"])
        return dataset

    def add(
        self,
        coll_name,
        data: Dict,
        replace=False,
        update_columns=(),
        update_columns_value=(),
        insert_ignore=False,
    ):
        """
        添加单条数据
        Args:
            coll_name: 集合名
            data: 单条数据
            replace: 唯一索引冲突时直接覆盖旧数据，默认为False
            update_columns: 更新指定的列（如果数据唯一索引冲突，则更新指定字段，如 update_columns = ["name", "title"]
            update_columns_value: 指定更新的字段对应的值, 不指定则用数据本身的值更新
            insert_ignore: 索引冲突是否忽略 默认False

        Returns: 插入成功的行数

        """
        affect_count = 1
        collection = self.get_collection(coll_name)
        try:
            collection.insert_one(data)
        except DuplicateKeyError as e:
            data.pop("_id", "")
            # 存在则更新
            if update_columns:
                if not isinstance(update_columns, (tuple, list)):
                    update_columns = [update_columns]

                condition = self.__get_update_condition(e.details.get("errmsg"), data)

                # 更新指定的列
                if update_columns_value:
                    # 使用指定的值更新
                    doc = {
                        key: value
                        for key, value in zip(update_columns, update_columns_value)
                    }
                else:
                    # 使用数据本身的值更新
                    doc = {key: data[key] for key in update_columns}

                collection.update_one(condition, {"$set": doc})

            # 覆盖更新
            elif replace:
                condition = self.__get_update_condition(e.details.get("errmsg"), data)
                # 替换已存在的数据
                collection.replace_one(condition, data)

            elif not insert_ignore:
                raise e

        return affect_count

    def add_batch(
        self,
        coll_name: str,
        datas: List[Dict],
        replace=False,
        update_columns=(),
        update_columns_value=(),
        condition_fields: dict = None,
    ):
        """
        批量添加数据
        Args:
            coll_name: 集合名
            datas: 数据 [{'_id': 'xx'}, ... ]
            replace:  唯一索引冲突时直接覆盖旧数据，默认为False
            update_columns: 更新指定的列（如果数据的唯一索引存在，则更新指定字段，如 update_columns = ["name", "title"]
            update_columns_value: 指定更新的字段对应的值, 不指定则用数据本身的值更新
            condition_fields: 用于条件查找的字段，不指定则用索引冲突中的字段查找

        Returns: 添加行数，不包含更新

        """
        add_count = 0

        if not datas:
            return add_count

        collection = self.get_collection(coll_name)
        if not isinstance(update_columns, (tuple, list)):
            update_columns = [update_columns]

        try:
            add_count = len(datas)
            collection.insert_many(datas, ordered=False)
        except BulkWriteError as e:
            write_errors = e.details.get("writeErrors")
            for error in write_errors:
                if error.get("code") == 11000:
                    # 数据重复
                    # 获取重复的数据
                    data = error.get("op")
                    data.pop("_id", "")

                    # 获取更新条件
                    if condition_fields:
                        condition = {
                            condition_field: data[condition_field]
                            for condition_field in condition_fields
                        }
                    else:
                        # 根据重复的值获取更新条件
                        condition = self.__get_update_condition(
                            error.get("errmsg"), data
                        )

                    if update_columns:
                        # 更新指定的列
                        if update_columns_value:
                            # 使用指定的值更新
                            doc = {
                                key: value
                                for key, value in zip(
                                    update_columns, update_columns_value
                                )
                            }
                        else:
                            # 使用数据本身的值更新
                            doc = {}
                            for key in update_columns:
                                doc = {key: data.get(key)}

                        collection.update_one(condition, {"$set": doc})
                        add_count -= 1

                    elif replace:
                        # 覆盖更新
                        collection.replace_one(condition, data)
                        add_count -= 1

                    else:
                        # log.error(error)
                        add_count -= 1

        return add_count

    def count(self, coll_name, condition: Optional[Dict], limit=0, **kwargs):
        """
        计数
        @param coll_name: 集合名
        @param condition: 查询条件
        @param limit: 限制数量
        @param kwargs:
        ----
        command = {
          count: <collection or view>,
          query: <document>,
          limit: <integer>,
          skip: <integer>,
          hint: <hint>,
          readConcern: <document>,
          collation: <document>,
          comment: <any>
        }
        https://docs.mongodb.com/manual/reference/command/count/#mongodb-dbcommand-dbcmd.count
        @return: 数据数量
        """
        command = {"count": coll_name, "query": condition, "limit": limit, **kwargs}
        result = self.run_command(command)
        return result["n"]

    def update(self, coll_name, data: Dict, condition: Dict, upsert: bool = False):
        """
        更新
        Args:
            coll_name: 集合名
            data: 单条数据 {"xxx":"xxx"}
            condition: 更新条件 {"_id": "xxxx"}
            upsert: 数据不存在则插入,默认为 False

        Returns: True / False
        """
        try:
            collection = self.get_collection(coll_name)
            collection.update_one(condition, {"$set": data}, upsert=upsert)
        except Exception as e:
            log.error(
                """
                error:{}
                condition: {}
            """.format(
                    e, condition
                )
            )
            return False
        else:
            return True

    def delete(self, coll_name, condition: Dict) -> bool:
        """
        删除
        Args:
            coll_name: 集合名
            condition: 查找条件
        Returns: True / False

        """
        try:
            collection = self.get_collection(coll_name)
            collection.delete_one(condition)
        except Exception as e:
            log.error(
                """
                error:{}
                condition: {}
            """.format(
                    e, condition
                )
            )
            return False
        else:
            return True

    def run_command(self, command: Dict):
        """
        运行指令
        参考文档 https://www.geek-book.com/src/docs/mongodb/mongodb/docs.mongodb.com/manual/reference/command/index.html
        @param command:
        @return:
        """
        return self.db.command(command)

    def create_index(self, coll_name, keys, unique=True):
        collection = self.get_collection(coll_name)
        _keys = [(key, pymongo.ASCENDING) for key in keys]
        collection.create_index(_keys, unique=unique)

    def drop_collection(self, coll_name):
        return self.db.drop_collection(coll_name)

    def __get_update_condition(self, duplicate_errmsg: str, data: dict) -> dict:
        """
        根据索引冲突的报错信息 获取更新条件
        Args:
            duplicate_errmsg: E11000 duplicate key error collection: feapder.test index: a_1_b_1 dup key: { : 1, : "你好" }
            data: {"a": 1, "b": "你好", "c": "嘻嘻"}

        Returns: {"a": 1, "b": "你好"}

        """
        condition = {}
        duplicate_values = re.search("dup key: \{(.*?)\}", duplicate_errmsg).group(1)
        duplicate_values = duplicate_values.strip(" :")
        duplicate_values = duplicate_values.split(", :")
        values = []
        for value in duplicate_values:
            value = value.strip()
            if value:
                if '"' in value:
                    value = value.strip('"')
                    values.append(value)
                elif "." in value:
                    values.append(float(value))
                else:
                    values.append(int(value))
        for key, val in data.items():
            for value in values:
                if val == value:
                    condition[key] = value

        return condition

    def __getattr__(self, name):
        return getattr(self.db, name)
