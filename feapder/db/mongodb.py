# -*- coding: utf-8 -*-
"""
Created on 2021-04-18 14:12:21
---------
@summary: 操作mongo数据库
---------
@author: Mkdir700
@email:  mkdir700@gmail.com
"""
from urllib import parse
from typing import List, Dict, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

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
    
    def get_collection(self, coll_name) -> Collection:
        """
        根据集合名获取集合对象
        @param coll_name: 集合名
        @return:
        """
        return self.db.get_collection(coll_name)
    
    def find(self,
             coll_name: str,
             condition: Optional[Dict] = None,
             limit: int = 0,
             **kwargs) -> List[Dict]:
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
        command = {
            'find': coll_name,
            'filter': condition,
            'limit': limit,
            'singleBatch': True
        }
        command.update(kwargs)
        result = self.run_command(command)
        cursor = result['cursor']
        dataset = cursor['firstBatch']
        return dataset
    
    def add(self, coll_name, data: Dict, **kwargs):
        """
        添加单条数据
        Args:
        @param coll_name: 集合名
        @param data: 单条数据
        @param kwargs:
            update_columns: 更新指定的列（如果数据的唯一索引存在，则更新指定字段，如 update_columns = ["name", "title"]
            insert_ignore: 唯一索引冲突时是否忽略，默认为False
            condition_fields: 用于条件查找的字段，默认以`_id`作为查找条件，默认：['_id']
            exception_callfunc: 异常回调
        @return: 插入成功的行数
        """
        affect_count = 1
        auto_update = kwargs.pop("auto_update", False)
        update_columns = kwargs.pop("update_columns", ())
        insert_ignore = kwargs.pop("insert_ignore", False)
        condition_fields = kwargs.pop("condition_fields", ["_id"])
        exception_callfunc = kwargs.pop("exception_callfunc", None)
        
        try:
            collection = self.get_collection(coll_name)
            
            # 存在则更新
            if update_columns:
                if not isinstance(update_columns, (tuple, list)):
                    update_columns = [update_columns]
                
                try:
                    collection.insert_one(data)
                except DuplicateKeyError:
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
                except DuplicateKeyError as e:
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
    
    def add_batch(self, coll_name: str, datas: List[Dict], **kwargs):
        """
        @summary: 批量添加数据
        ---------
        @param coll_name: 集合名
        @param datas: 列表 [{'_id': 'xx'}, ... ]
        @param kwargs:
            auto_update: 覆盖更新，将替换唯一索引重复的数据，默认False
            update_columns: 更新指定的列（如果数据的唯一索引存在，则更新指定字段，如 update_columns = ["name", "title"]
            update_columns_value: 指定更新的字段对应的值
            condition_fields: 用于条件查找的字段，默认以`_id`作为查找条件，默认：['_id']
        ---------
        @return: 添加行数
        """
        if not datas:
            return
        
        affect_count = None
        auto_update = kwargs.pop("auto_update", False)
        update_columns = kwargs.pop("update_columns", ())
        update_columns_value = kwargs.pop("update_columns_value", ())
        condition_fields = kwargs.pop("condition_fields", ["_id"])
        
        try:
            collection = self.get_collection(coll_name)
            affect_count = 0
            
            if update_columns:
                if not isinstance(update_columns, (tuple, list)):
                    update_columns = [update_columns]
                
                for data in datas:
                    try:
                        collection.insert_one(data)
                    except DuplicateKeyError:
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
                # 覆盖更新
                updates = []
                command = {
                    'update': coll_name,
                    'updates': updates,
                    'ordered': False
                }
                
                for data in datas:
                    condition = {
                        condition_field: data[condition_field]
                        for condition_field in condition_fields
                    }
                    updates.append({
                        'q': condition,
                        'u': data,
                        'upsert': True
                    })
                
                write_result = self.run_command(command)
                affect_count += write_result['n']
            
            else:
                command = {
                    'insert': coll_name,
                    'documents': datas,
                    'ordered': False
                }
                write_result = self.run_command(command)
                affect_count += write_result['n']
                write_errors = write_result.get('writeErrors', None)
                if write_errors:
                    log.error("error:{}".format(write_errors))
        
        except Exception as e:
            log.error("error:{}".format(e))
        
        return affect_count
    
    def update(self, coll_name, data: Dict, condition: Dict, upsert: bool = False):
        """
        更新
        Args:
            coll_name: 集合名
            data: 单条数据 {"xxx":"xxx"}
            condition: 更新条件 {"_id": "xxxx"}
            upsert: 数据不存在则更新,默认为 False

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
