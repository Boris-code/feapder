# -*- coding: utf-8 -*-
"""
    	*************************** 
    	--------description-------- 
 	 @Date : 2021-12-04
 	 @Author: 沈瑞祥
     @contact: ruixiang.shen@outlook.com
 	 @LastEditTime: 2021-12-04 17:05
 	 @FilePath: feapder/pipelines/pgsql_pipeline.py
     @Project: feapder

    	***************************
"""

from typing import Dict, List, Tuple

import feapder.utils.pgsql_tool as tools
from feapder.db.pgsqldb import PgsqlDB
from feapder.pipelines import BasePipeline
from feapder.utils.log import log


class PgsqlPipeline(BasePipeline):
    def __init__(self):
        self._to_db = None

    @property
    def to_db(self):
        if not self._to_db:
            self._to_db = PgsqlDB()

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
        get_indexes_sql = tools.get_indexes_col_sql(table)
        indexes_cols = self.to_db.find(sql=get_indexes_sql, limit=0, to_json=True)[0]["column_names"]
        sql, datas = tools.make_batch_sql(table, items, indexes_cols=indexes_cols)
        add_count = self.to_db.add_batch(sql, datas)
        log.info(sql)
        datas_size = len(datas)
        if add_count:
            log.info(
                "共导出 %s 条数据 到 %s, 重复 %s 条" % (datas_size, table, datas_size - add_count)
            )

        return add_count is not None

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
        get_indexes_sql = tools.get_indexes_col_sql(table)
        indexes_cols = self.to_db.find(sql=get_indexes_sql, limit=0, to_json=True)[0]["column_names"]
        sql, datas = tools.make_batch_sql(
            table, items, update_columns=update_keys or list(items[0].keys()), indexes_cols=indexes_cols
        )
        log.info(sql)
        update_count = self.to_db.add_batch(sql, datas)
        if update_count:
            msg = "共更新 %s 条数据 到 %s" % (update_count, table)
            if update_keys:
                msg += " 更新字段为 {}".format(update_keys)
            log.info(msg)

        return update_count is not None
