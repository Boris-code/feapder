# -*- coding: utf-8 -*-
"""
Created on 2021-04-18 14:12:21
---------
@summary: 操作mongo数据库
---------
@author: Mkdir700
@email:  mkdir700@gmail.com
"""
from typing import List, Dict
from urllib import parse

import pymongo.errors
from pymongo import MongoClient
from pymongo.collection import Collection

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
        self.db = self.client.get_database(db)

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

    def get_collection(self, collection_name) -> Collection:
        return self.db.get_collection(collection_name)

    def find(self, table, condition=None, limit=0) -> List[Dict]:
        """
        @summary:
        无数据： 返回[]
        有数据： [{'_id': 'xx', ...}, ...]
        ---------
        @param filter:
        @param limit:
        ---------
        @result:
        """
        condition = {} if condition is None else condition
        collection = self.db.get_collection(table)
        cursor = collection.find(condition)
        result = list(cursor.limit(limit))
        cursor.close()
        return result

    def add(self, table, data: Dict, **kwargs):
        """

        Args:
            table:
            data:
            kwargs:
                auto_update: 覆盖更新，将替换唯一索引重复的数据，默认False
                update_columns: 更新指定的列（如果数据的唯一索引存在，则更新指定字段，如 update_columns = ["name", "title"]
                insert_ignore: 唯一索引冲突时是否忽略，默认为False
                condition_fields: 用于条件查找的字段，默认以`_id`作为查找条件，默认：['_id']
                exception_callfunc: 异常回调

        Returns: 添加行数

        """
        affect_count = 1
        auto_update = kwargs.get("auto_update", False)
        update_columns = kwargs.get("update_columns", ())
        insert_ignore = kwargs.get("insert_ignore", False)
        condition_fields = kwargs.get("condition_fields", ["_id"])
        exception_callfunc = kwargs.get("exception_callfunc", None)
        try:
            collection = self.get_collection(table)

            # 存在则更新
            if update_columns:
                if not isinstance(update_columns, (tuple, list)):
                    update_columns = [update_columns]

                try:
                    collection.insert_one(data)
                except pymongo.errors.DuplicateKeyError:
                    condition = {
                        condition_field: data[condition_field]
                        for condition_field in condition_fields
                    }
                    doc = {key: data[key] for key in update_columns}
                    collection.update_one(condition, {"$set": doc})

            # 覆盖更新
            elif auto_update:
                condition = {
                    condition_field: data[condition_field]
                    for condition_field in condition_fields
                }
                # 替换已存在的数据
                collection.replace_one(condition, data)

            else:
                try:
                    collection.insert_one(data)
                except pymongo.errors.DuplicateKeyError as e:
                    if not insert_ignore:
                        raise e
                    else:
                        affect_count = 0

        except Exception as e:
            log.error("error: {}".format(e))
            if exception_callfunc:
                exception_callfunc(e)

            affect_count = 0

        return affect_count

    def add_batch(self, table: str, datas: List[Dict], **kwargs):
        """
        @summary: 批量添加数据
        ---------
        @param command: 字典
        @param datas: 列表 [[..], [...]]
        @param **kwargs:
            auto_update: 覆盖更新，将替换唯一索引重复的数据，默认False
            update_columns: 更新指定的列（如果数据的唯一索引存在，则更新指定字段，如 update_columns = ["name", "title"]
            update_columns_value: 指定更新的字段对应的值
            condition_fields: 用于条件查找的字段，默认以`_id`作为查找条件，默认：['_id']
        ---------
        @result: 添加行数
        """
        if not datas:
            return

        affect_count = None
        auto_update = kwargs.get("auto_update", False)
        update_columns = kwargs.get("update_columns", ())
        update_columns_value = kwargs.get("update_columns_value", ())
        condition_fields = kwargs.get("condition_fields", ["_id"])

        try:
            collection = self.get_collection(table)
            affect_count = 0

            if update_columns:
                if not isinstance(update_columns, (tuple, list)):
                    update_columns = [update_columns]

                for data in datas:
                    try:
                        collection.insert_one(data)
                    except pymongo.errors.DuplicateKeyError:
                        # 数据冲突，只更新指定字段
                        condition = {
                            condition_field: data[condition_field]
                            for condition_field in condition_fields
                        }
                        doc = {
                            key: value
                            for key, value in zip(update_columns, update_columns_value)
                        }
                        collection.update_one(condition, {"$set": doc})
                    affect_count += 1

            elif auto_update:
                for data in datas:
                    condition = {
                        condition_field: data[condition_field]
                        for condition_field in condition_fields
                    }
                    # 如果找到就替换，否则插入
                    result = collection.find_one_and_replace(
                        condition, data, upsert=True
                    )
                    affect_count += 1

            else:
                for data in datas:
                    try:
                        collection.insert_one(data)  # TODO 实现真正的批量插入
                    except pymongo.errors.DuplicateKeyError:
                        # 忽略冲突
                        continue
                    affect_count += 1

        except Exception as e:
            log.error("error:{}".format(e))

        return affect_count

    def update(self, table, data: Dict, condition: Dict):
        """
        更新
        Args:
            table: 表名
            data: 数据 {"xxx":"xxx"}
            condition: 更新条件 {"_id": "xxxx"}

        Returns: True / False
        """
        try:
            collection = self.get_collection(table)
            collection.update_one(condition, {"$set": data})
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

    def delete(self, table, condition: Dict):
        """
        删除
        Args:
            table:
            condition: 查找条件
        Returns: True / False

        """
        try:
            collection = self.get_collection(table)
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
