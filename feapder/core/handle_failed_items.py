# -*- coding: utf-8 -*-
"""
Created on 2022/11/18 11:33 AM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import feapder.setting as setting
from feapder.buffer.item_buffer import ItemBuffer
from feapder.db.redisdb import RedisDB
from feapder.network.item import Item, UpdateItem
from feapder.utils.log import log


class HandleFailedItems:
    def __init__(self, redis_key, task_table=None, item_buffer=None):
        self._redis_key = redis_key

        self._redisdb = RedisDB()
        self._item_buffer = item_buffer or ItemBuffer(
            self._redis_key, task_table=task_table
        )

        self._table_failed_items = setting.TAB_FAILED_ITEMS.format(redis_key=redis_key)

    def get_failed_items(self, count=1):
        failed_items = self._redisdb.sget(
            self._table_failed_items, count=count, is_pop=False
        )
        return failed_items

    def reput_failed_items_to_db(self):
        log.debug("正在重新写入失败的items...")
        total_count = 0
        while True:
            try:
                failed_items = self.get_failed_items()
                if not failed_items:
                    break

                for data_str in failed_items:
                    data = eval(data_str)

                    for add in data.get("add"):
                        table = add.get("table")
                        datas = add.get("datas")
                        for _data in datas:
                            item = Item(**_data)
                            item.table_name = table
                            self._item_buffer.put_item(item)
                            total_count += 1

                    for update in data.get("update"):
                        table = update.get("table")
                        datas = update.get("datas")
                        update_keys = update.get("update_keys")
                        for _data in datas:
                            item = UpdateItem(**_data)
                            item.table_name = table
                            item.update_keys = update_keys
                            self._item_buffer.put_item(item)
                            total_count += 1

                    # 入库成功后删除
                    def delete_item():
                        self._redisdb.srem(self._table_failed_items, data_str)

                    self._item_buffer.put_item(delete_item)
                    self._item_buffer.flush()

            except Exception as e:
                log.exception(e)

        if total_count:
            log.debug("导入%s条失败item到数库" % total_count)
        else:
            log.debug("没有失败的item")

    def close(self):
        self._item_buffer.close()
