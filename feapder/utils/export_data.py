# -*- coding: utf-8 -*-
"""
Created on 2018-07-29 22:48:30
---------
@summary: 导出数据
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""
import feapder.utils.tools as tools
from feapder.db.mysqldb import MysqlDB
from feapder.db.redisdb import RedisDB
from feapder.utils.log import log


class ExportData(object):
    def __init__(self):
        self._redisdb = None
        self._to_db = None

    @property
    def redisdb(self):
        if not self._redisdb:
            self._redisdb = RedisDB()

        return self._redisdb

    @property
    def to_db(self):
        if not self._to_db:
            self._to_db = MysqlDB()

        return self._to_db

    def export(self, from_table, to_table, auto_update=False, batch_count=100):
        """
        @summary:
        用于从redis的item中导出数据到关系型数据库，如mysql/oracle
        from_table与to_table表结构必须一致
        ---------
        @param from_table:
        @param to_table:
        @param auto_update: 当数据存在时是否自动更新 默认否
        ---------
        @result:
        """
        total_count = 0

        while True:
            datas = []
            try:
                datas = self.redisdb.sget(from_table, count=batch_count, is_pop=False)
                if not datas:
                    log.info(
                        """
                        \r%s -> %s 共导出 %s 条数据"""
                        % (from_table, to_table, total_count)
                    )
                    break

                json_datas = [eval(data) for data in datas]
                sql, json_datas = tools.make_batch_sql(
                    to_table, json_datas, auto_update
                )
                if self.to_db.add_batch(sql, json_datas):
                    total_count += len(json_datas)
                    self.redisdb.srem(from_table, datas)

            except Exception as e:
                log.exception(e)
                log.error(datas)

    def export_all(
        self,
        tables,
        auto_update=False,
        batch_count=100,
        every_table_per_export_callback=None,
    ):
        """
        @summary: 导出所有item
        ---------
        @param tables: 如qidian  则导出起点下面所有的items
        数据库中的表格式必须有规律 如导出 qidian:comment:s_qidian_book_comment_dynamic_item 对应导入 qidian_book_comment_dynamic
        @param auto_update: 是否自动更新
        @param batch_count: 每批次导出的数量
        @every_table_per_export_callback: 导出前的回调函数, 用来修改特定表的参数 to_table, auto_update, batch_count
        如：
            def every_table_per_export_callback(to_table, auto_update, batch_count):
                if to_table == 'xxx':
                    auto_update = True
                return to_table, auto_update, batch_count
        ---------
        @result:
        """
        tables = (
            self.redisdb.getkeys(tables + "*_item")
            if not isinstance(tables, list)
            else tables
        )
        if not tables:
            log.info("无表数据")
        for table in tables:
            from_table = table
            to_table = tools.get_info(str(from_table), ":s_(.*?)_item", fetch_one=True)
            if callable(every_table_per_export_callback):
                to_table, auto_update, batch_count = every_table_per_export_callback(
                    to_table, auto_update, batch_count
                )

            log.info(
                """
                \r正在导出 %s -> %s"""
                % (from_table, to_table)
            )
            self.export(from_table, to_table, auto_update, batch_count)

    def export_items(self, tab_item, items_data):
        """
        @summary:
        ---------
        @param tab_item: redis中items的表名
        @param items_data: [item.to_dict] 数据
        ---------
        @result:
        """

        to_table = tools.get_info(tab_item, ":s_(.*?)_item", fetch_one=True)
        sql, datas = tools.make_batch_sql(to_table, items_data)
        add_count = self.to_db.add_batch(sql, datas)
        datas_size = len(datas)
        if add_count is None:
            log.error("导出数据到表 %s 失败" % (to_table))
        else:
            log.info(
                "共导出 %s 条数据 到 %s, 重复 %s 条"
                % (datas_size, to_table, datas_size - add_count)
            )

        return add_count != None

    def update_items(self, tab_item, items_data, update_keys=()):
        """
        @summary:
        ---------
        @param tab_item: redis中items的表名
        @param items_data: [item.to_dict] 数据
        @param update_keys: 更新的字段
        ---------
        @result:
        """
        to_table = tools.get_info(tab_item, ":s_(.*?)_item", fetch_one=True)
        sql, datas = tools.make_batch_sql(
            to_table,
            items_data,
            update_columns=update_keys or list(items_data[0].keys()),
        )
        update_count = self.to_db.add_batch(sql, datas)
        if update_count is None:
            log.error("更新表 %s 数据失败" % (to_table))
        else:
            msg = "共更新 %s 条数据 到 %s" % (update_count // 2, to_table)
            if update_keys:
                msg += " 更新字段为 {}".format(update_keys)
            log.info(msg)

        return update_count != None
