# -*- coding: utf-8 -*-
"""
Created on 2018-06-19 17:17
---------
@summary: item 管理器， 负责缓冲添加到数据库中的item， 由该manager统一添加。防止多线程同时访问数据库
---------
@author: Boris
@email: boris@bzkj.tech
"""

import importlib
import threading
from queue import Queue

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.db.redisdb import RedisDB
from feapder.dedup import Dedup
from feapder.network.item import Item, UpdateItem
from feapder.pipelines import BasePipeline
from feapder.pipelines.mysql_pipeline import MysqlPipeline
from feapder.utils.log import log

MAX_ITEM_COUNT = 5000  # 缓存中最大item数
UPLOAD_BATCH_MAX_SIZE = 1000

MYSQL_PIPELINE_PATH = "feapder.pipelines.mysql_pipeline.MysqlPipeline"


class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_inst"):
            cls._inst = super(Singleton, cls).__new__(cls)

        return cls._inst


class ItemBuffer(threading.Thread, Singleton):
    dedup = None

    def __init__(self, redis_key, task_table=None):
        if not hasattr(self, "_table_item"):
            super(ItemBuffer, self).__init__()

            self._thread_stop = False
            self._is_adding_to_db = False
            self._redis_key = redis_key
            self._task_table = task_table

            self._items_queue = Queue(maxsize=MAX_ITEM_COUNT)
            self._db = RedisDB()

            self._table_item = setting.TAB_ITEM
            self._table_request = setting.TAB_REQUSETS.format(redis_key=redis_key)

            self._item_tables = {
                # 'xxx_item': {'tab_item': 'xxx:xxx_item'} # 记录item名与redis中item名对应关系
            }

            self._item_update_keys = {
                # 'xxx:xxx_item': ['id', 'name'...] # 记录redis中item名与需要更新的key对应关系
            }

            self._pipelines = self.load_pipelines()

            self._have_mysql_pipeline = MYSQL_PIPELINE_PATH in setting.ITEM_PIPELINES
            self._mysql_pipeline = None

            if setting.ITEM_FILTER_ENABLE and not self.__class__.dedup:
                self.__class__.dedup = Dedup(to_md5=False)

    def load_pipelines(self):
        pipelines = []
        for pipeline_path in setting.ITEM_PIPELINES:
            module, class_name = pipeline_path.rsplit(".", 1)
            pipeline_cls = importlib.import_module(module).__getattribute__(class_name)
            pipeline = pipeline_cls()
            if not isinstance(pipeline, BasePipeline):
                raise ValueError(f"{pipeline_path} 需继承 feapder.pipelines.BasePipeline")
            pipelines.append(pipeline)

        return pipelines

    @property
    def mysql_pipeline(self):
        if not self._mysql_pipeline:
            module, class_name = MYSQL_PIPELINE_PATH.rsplit(".", 1)
            pipeline_cls = importlib.import_module(module).__getattribute__(class_name)
            self._mysql_pipeline = pipeline_cls()

        return self._mysql_pipeline

    def run(self):
        while not self._thread_stop:
            self.flush()
            tools.delay_time(0.5)

        self.close()

    def stop(self):
        self._thread_stop = True

    def put_item(self, item):
        self._items_queue.put(item)

    def flush(self):
        try:
            items = []
            update_items = []
            requests = []
            callbacks = []
            items_fingerprints = []
            data_count = 0

            while not self._items_queue.empty():
                data = self._items_queue.get_nowait()
                data_count += 1

                # data 分类
                if callable(data):
                    callbacks.append(data)

                elif isinstance(data, UpdateItem):
                    update_items.append(data)

                elif isinstance(data, Item):
                    items.append(data)
                    if setting.ITEM_FILTER_ENABLE:
                        items_fingerprints.append(data.fingerprint)

                else:  # request-redis
                    requests.append(data)

                if data_count >= UPLOAD_BATCH_MAX_SIZE:
                    self.__add_item_to_db(
                        items, update_items, requests, callbacks, items_fingerprints
                    )

                    items = []
                    update_items = []
                    requests = []
                    callbacks = []
                    items_fingerprints = []
                    data_count = 0

            if data_count:
                self.__add_item_to_db(
                    items, update_items, requests, callbacks, items_fingerprints
                )

        except Exception as e:
            log.exception(e)

    def get_items_count(self):
        return self._items_queue.qsize()

    def is_adding_to_db(self):
        return self._is_adding_to_db

    def __dedup_items(self, items, items_fingerprints):
        """
        去重
        @param items:
        @param items_fingerprints:
        @return: 返回去重后的items, items_fingerprints
        """
        if not items:
            return items, items_fingerprints

        is_exists = self.__class__.dedup.get(items_fingerprints)
        is_exists = is_exists if isinstance(is_exists, list) else [is_exists]

        dedup_items = []
        dedup_items_fingerprints = []
        items_count = dedup_items_count = dup_items_count = 0

        while is_exists:
            item = items.pop(0)
            items_fingerprint = items_fingerprints.pop(0)
            is_exist = is_exists.pop(0)

            items_count += 1

            if not is_exist:
                dedup_items.append(item)
                dedup_items_fingerprints.append(items_fingerprint)
                dedup_items_count += 1
            else:
                dup_items_count += 1

        log.info(
            "待入库数据 {} 条， 重复 {} 条，实际待入库数据 {} 条".format(
                items_count, dup_items_count, dedup_items_count
            )
        )

        return dedup_items, dedup_items_fingerprints

    def __pick_items(self, items, is_update_item=False):
        """
        将每个表之间的数据分开 拆分后 原items为空
        @param items:
        @param is_update_item:
        @return:
        """
        datas_dict = {
            # 'xxx:xxx_item': [{}, {}] redis 中的item名与对应的数据
        }

        while items:
            item = items.pop(0)
            # 取item下划线格式的名
            # 下划线类的名先从dict中取，没有则现取，然后存入dict。加快下次取的速度
            item_name = item.item_name
            item_table = self._item_tables.get(item_name)
            if not item_table:
                item_name_underline = item.name_underline
                tab_item = self._table_item.format(
                    redis_key=self._redis_key, item_name=item_name_underline
                )

                item_table = {}
                item_table["tab_item"] = tab_item

                self._item_tables[item_name] = item_table

            else:
                tab_item = item_table.get("tab_item")

            # # 入库前的回调
            # item.pre_to_db()

            if tab_item not in datas_dict:
                datas_dict[tab_item] = []

            datas_dict[tab_item].append(item.to_dict)

            if is_update_item and tab_item not in self._item_update_keys:
                self._item_update_keys[tab_item] = item.update_key

        return datas_dict

    def __export_to_db(self, tab_item, datas, is_update=False, update_keys=()):
        to_table = tools.get_info(tab_item, ":s_(.*?)_item$", fetch_one=True)

        # 打点 校验
        self.check_datas(table=to_table, datas=datas)

        for pipeline in self._pipelines:
            if is_update:
                if to_table == self._task_table and not isinstance(
                    pipeline, MysqlPipeline
                ):
                    continue

                if not pipeline.update_items(to_table, datas, update_keys=update_keys):
                    log.error(
                        f"{pipeline.__class__.__name__} 更新数据失败. table: {to_table}  items: {datas}"
                    )
                    return False

            else:
                if not pipeline.save_items(to_table, datas):
                    log.error(
                        f"{pipeline.__class__.__name__} 保存数据失败. table: {to_table}  items: {datas}"
                    )
                    return False

        # 若是任务表, 且上面的pipeline里没mysql，则需调用mysql更新任务
        if not self._have_mysql_pipeline and is_update and to_table == self._task_table:
            self.mysql_pipeline.update_items(to_table, datas, update_keys=update_keys)

    def __add_item_to_db(
        self, items, update_items, requests, callbacks, items_fingerprints
    ):
        export_success = False
        self._is_adding_to_db = True

        # 去重
        if setting.ITEM_FILTER_ENABLE:
            items, items_fingerprints = self.__dedup_items(items, items_fingerprints)

        # 分捡
        items_dict = self.__pick_items(items)
        update_items_dict = self.__pick_items(update_items, is_update_item=True)

        # item批量入库
        while items_dict:
            tab_item, datas = items_dict.popitem()

            log.debug(
                """
                -------------- item 批量入库 --------------
                表名: %s
                datas: %s
                    """
                % (tab_item, tools.dumps_json(datas, indent=16))
            )

            export_success = self.__export_to_db(tab_item, datas)

        # 执行批量update
        while update_items_dict:
            tab_item, datas = update_items_dict.popitem()
            log.debug(
                """
                -------------- item 批量更新 --------------
                表名: %s
                datas: %s
                    """
                % (tab_item, tools.dumps_json(datas, indent=16))
            )

            update_keys = self._item_update_keys.get(tab_item)
            export_success = self.__export_to_db(
                tab_item, datas, is_update=True, update_keys=update_keys
            )

        # 执行回调
        while callbacks:
            try:
                callback = callbacks.pop(0)
                callback()
            except Exception as e:
                log.exception(e)

        # 删除做过的request
        if requests:
            self._db.zrem(self._table_request, requests)

        # 去重入库
        if export_success and setting.ITEM_FILTER_ENABLE:
            if items_fingerprints:
                self.__class__.dedup.add(items_fingerprints, skip_check=True)

        self._is_adding_to_db = False

    def check_datas(self, table, datas):
        """
        打点 记录总条数及每个key情况
        @param table: 表名
        @param datas: 数据 列表
        @return:
        """
        pass

    def close(self):
        pass
