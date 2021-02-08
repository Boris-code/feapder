# -*- coding: utf-8 -*-
"""
Created on 2018-06-19 17:17
---------
@summary: item 管理器， 负责缓冲添加到数据库中的item， 由该manager统一添加。防止多线程同时访问数据库
---------
@author: Boris
@email: boris@bzkj.tech
"""

import threading
from queue import Queue

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.db.redisdb import RedisDB
from feapder.dedup import Dedup
from feapder.network.item import Item, UpdateItem
from feapder.utils.export_data import ExportData
from feapder.utils.log import log

MAX_ITEM_COUNT = 5000  # 缓存中最大item数
UPLOAD_BATCH_MAX_SIZE = 1000


class Singleton(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_inst"):
            cls._inst = super(Singleton, cls).__new__(cls)

        return cls._inst


class ItemBuffer(threading.Thread, Singleton):
    dedup = None

    def __init__(self, table_folder):
        if not hasattr(self, "_table_item"):
            super(ItemBuffer, self).__init__()

            self._thread_stop = False
            self._is_adding_to_db = False
            self._table_folder = table_folder

            self._items_queue = Queue(maxsize=MAX_ITEM_COUNT)
            self._db = RedisDB()

            self._table_item = setting.TAB_ITEM
            self._table_request = setting.TAB_REQUSETS.format(table_folder=table_folder)

            self._item_tables = {
                # 'xxx_item': {'tab_item': 'xxx:xxx_item'} # 记录item名与redis中item名对应关系
            }

            self._item_update_keys = {
                # 'xxx:xxx_item': ['id', 'name'...] # 记录redis中item名与需要更新的key对应关系
            }

            self._export_data = ExportData() if setting.ADD_ITEM_TO_MYSQL else None

            self.db_tip()

            if setting.ITEM_FILTER_ENABLE and not self.__class__.dedup:
                self.__class__.dedup = Dedup(to_md5=False)

    def db_tip(self):
        msg = "\n"
        if setting.ADD_ITEM_TO_MYSQL:
            msg += "item 自动入mysql\n"
        if setting.ADD_ITEM_TO_REDIS:
            msg += "item 自动入redis\n"
        if msg == "\n":
            log.warning("*** 请注意检查item是否入库 !!!")
        else:
            log.info(msg)

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
                    table_folder=self._table_folder, item_name=item_name_underline
                )

                item_table = {}
                item_table["tab_item"] = tab_item

                self._item_tables[item_name] = item_table

            else:
                tab_item = item_table.get("tab_item")

            # 入库前的回调
            item.per_to_db()

            if tab_item not in datas_dict:
                datas_dict[tab_item] = []

            datas_dict[tab_item].append(item.to_dict)

            if is_update_item and tab_item not in self._item_update_keys:
                self._item_update_keys[tab_item] = item.update_key

        return datas_dict

    def __export_to_db(self, tab_item, datas, is_update=False, update_keys=()):
        export_success = False
        # 打点 校验
        to_table = tools.get_info(tab_item, ":s_(.*?)_item", fetch_one=True)
        item_name = to_table + "_item"
        self.check_datas(table=to_table, datas=datas)

        if setting.ADD_ITEM_TO_MYSQL:  # 任务表需要入mysql
            if isinstance(setting.ADD_ITEM_TO_MYSQL, (list, tuple)):
                for item in setting.ADD_ITEM_TO_MYSQL:
                    if item in item_name:
                        export_success = (
                            self._export_data.export_items(tab_item, datas)
                            if not is_update
                            else self._export_data.update_items(
                                tab_item, datas, update_keys=update_keys
                            )
                        )

            else:
                export_success = (
                    self._export_data.export_items(tab_item, datas)
                    if not is_update
                    else self._export_data.update_items(
                        tab_item, datas, update_keys=update_keys
                    )
                )

        if setting.ADD_ITEM_TO_REDIS:
            if isinstance(setting.ADD_ITEM_TO_REDIS, (list, tuple)):
                for item in setting.ADD_ITEM_TO_REDIS:
                    if item in item_name:
                        self._db.sadd(tab_item, datas)
                        export_success = True
                        log.info("共导出 %s 条数据 到redis %s" % (len(datas), tab_item))
                        break

            else:
                self._db.sadd(tab_item, datas)
                export_success = True
                log.info("共导出 %s 条数据 到redis %s" % (len(datas), tab_item))

        return export_success

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
