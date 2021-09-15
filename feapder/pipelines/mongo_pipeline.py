# -*- coding: utf-8 -*-
"""
Created on 2021-04-18 14:12:21
---------
@summary: 导出数据
---------
@author: Mkdir700
@email:  mkdir700@gmail.com
"""
from typing import Dict, List, Tuple

from feapder.db.mongodb import MongoDB
from feapder.pipelines import BasePipeline
from feapder.utils.log import log


class MongoPipeline(BasePipeline):
    def __init__(self):
        self._to_db = None

    @property
    def to_db(self):
        if not self._to_db:
            self._to_db = MongoDB()

        return self._to_db

    def save_items(self, table, items: List[Dict]) -> bool:
        """
        保存数据
        Args:
            table: 表名
            items: 数据，[{},{},...]

        Returns: 是否保存成功 True / False
                 若False，不会将本批数据入到去重库，以便再次入库

        """
        add_count = self.to_db.add_batch(coll_name=table, datas=items)
        datas_size = len(items)
        if add_count is not None:
            log.info(
                "共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, table, datas_size - add_count)
            )

        return add_count != None

    def update_items(self, table, items: List[Dict], update_keys=Tuple) -> bool:
        """
        更新数据
        Args:
            table: 表名
            items: 数据，[{},{},...]
            update_keys: 更新的字段, 如 ("title", "publish_time")

        Returns: 是否更新成功 True / False
                 若False，不会将本批数据入到去重库，以便再次入库

        """
        update_values = []
        for key in update_keys:
            for item in items:
                update_values.append(item[key])

        update_count = self.to_db.add_batch(
            coll_name=table,
            datas=items,
            update_columns=update_keys or list(items[0].keys()),
            update_columns_value=update_values,
        )
        if update_count:
            msg = "共更新 %s 条数据 到 %s" % (update_count, table)
            if update_keys:
                msg += " 更新字段为 {}".format(update_keys)
            log.info(msg)

        return update_count != None
