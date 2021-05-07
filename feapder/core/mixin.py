# -*- coding: utf-8 -*-
"""
Created on 2021/5/1 15:37
---------
@summary: 
---------
@author: mkdir700
@email:  mkdir700@gmail.com
"""
import datetime
from typing import List, Tuple, Optional, Dict
from feapder.db.mysqldb import MysqlDB


class BatchDBMixinBase(object):
    
    def _format_task_condition(self, task_condition):
        pass
    
    def _format_task_order(self, task_order_by):
        pass
    
    def _get_task_state_count(self) -> List[Tuple]:
        """
        获取任务状态及总数
        @return:
        """
        pass
    
    def _update_batch_record(self, task_state: Dict):
        """
        @summary: 更新批次表中的任务状态
        ---------
        ---------
        @result:
        """
        pass
    
    def _update_batch_record_done(self):
        """
        更新批次表的is_done状态，减少查询任务表的次数
        @return:
        """
        pass
    
    def _update_batch_record_done_cache_date(self):
        pass
    
    def _get_todo_task(self):
        """
        从数据库从取出代执行的任务
        @return:
        """
        pass
    
    def _get_doing_task(self):
        """
        获取正在执行的任务
        @return:
        """
        pass
    
    def _update_task_status(self, task_ids: List):
        """
        更新任务状态
        @return:
        """
        pass
    
    def _reset_lose_task(self):
        """
        @summary: 重置丢失任务为待做
        ---------
        ---------
        @result:
        """
        pass
    
    def _reset_task(self):
        """
        @summary: 初始化任务表中的任务， 新一个批次开始时调用。
        ---------
        ---------
        @result:
        """
        pass
    
    def _get_latest_batch_record(self) -> Dict:
        """
        获取最新的批次记录数据
        @return:
        """
        pass
    
    def _get_task_total_count(self) -> int:
        """
        获取完整的任务数
        @return:
        """
        pass
    
    def _add_batch_record(self, batch_date, total_task_count) -> Optional[int]:
        """
        新增一个批次记录
        @return:
        """
        pass
    
    def _get_done_or_doing_tasks(self, limit=0):
        """
        获取已完成及正在进行中的任务
        :@param limit: 数据数量限制
        @return:
        """
        pass
    
    def _create_batch_record_table(self):
        pass


class BatchMysqlDBMixin(BatchDBMixinBase):
    _db: MysqlDB
    
    def _format_task_condition(self, task_condition):
        self._task_condition = task_condition
        self._task_condition_prefix_and = task_condition and " and {}".format(
            task_condition
        )
        self._task_condition_prefix_where = task_condition and " where {}".format(
            task_condition
        )
    
    def _format_task_order(self, task_order_by):
        self._task_order_by = task_order_by and " order by {}".format(task_order_by)
    
    def _get_task_state_count(self) -> List[Tuple]:
        """
        获取任务状态及总数
        @return:
        """
        sql = "select {state}, count(1) from {task_table}{task_condition} group by {state}".format(
            state=self._task_state,
            task_table=self._task_table,
            task_condition=self._task_condition_prefix_where,
        )
        task_state_count = self._db.find(sql)
        return task_state_count
    
    def _get_task_total_count(self) -> int:
        """
        获取完整的任务数
        @return:
        """
        # 查询总任务数
        sql = "select count(1) from %s%s" % (
            self._task_table,
            self._task_condition_prefix_where,
        )
        total_task_count = self._db.find(sql)[0][0]
        return total_task_count
    
    def _get_todo_task(self) -> List[Tuple]:
        """
        从数据库从取出代执行的任务
        @return:
        """
        task_keys = ", ".join([f"`{key}`" for key in self._task_keys])
        sql = "select %s from %s where %s = 0%s%s limit %s" % (
            task_keys,
            self._task_table,
            self._task_state,
            self._task_condition_prefix_and,
            self._task_order_by,
            self._task_limit,
        )
        tasks = self._db.find(sql)
        return tasks
    
    def _get_doing_task(self):
        # 查询任务
        task_keys = ", ".join([f"`{key}`" for key in self._task_keys])
        sql = "select %s from %s where %s = 2%s%s limit %s" % (
            task_keys,
            self._task_table,
            self._task_state,
            self._task_condition_prefix_and,
            self._task_order_by,
            self._task_limit,
        )
        tasks = self._db.find(sql)
        return tasks
    
    def _get_done_or_doing_tasks(self, limit=0) -> List:
        sql = "select 1 from %s where (%s = 0 or %s=2)%s limit %" % (
            self._task_table,
            self._task_state,
            self._task_state,
            self._task_condition_prefix_and,
            limit
        )
        tasks = self._db.find(sql)  # [(1,)]  / []
        return tasks
    
    def _get_latest_batch_record(self) -> Optional[Dict]:
        sql = 'select date_format(batch_date, "{date_format}"), total_count, done_count, is_done from {batch_record_table} order by id desc limit 1'.format(
            date_format=self._date_format.replace(":%M", ":%i"),
            batch_record_table=self._batch_record_table,
        )
        try:
            batch_info = self._db.find(sql)[0]  # (('2018-08-19', 49686, 0),)
        except IndexError:
            return None
        # batch_date, total_count, done_count, is_done = batch_info
        return {key: key for key in batch_info}
    
    def _update_batch_record(self, task_state: Dict):
        """
        @summary: 更新批次表中的任务状态
        ---------
        ---------
        @result:
        """
        sql = "update {} set done_count = {}, total_count = {}, fail_count = {}, update_time = CURRENT_TIME, is_done=0, `interval` = {}, interval_unit = '{}' where batch_date = '{}'".format(
            self._batch_record_table,
            task_state.get("done_count"),
            task_state.get("total_count"),
            task_state.get("failed_count"),
            self._batch_interval
            if self._batch_interval >= 1
            else self._batch_interval * 24,
            "day" if self._batch_interval >= 1 else "hour",
            self.batch_date,
        )
        self._mysqldb.update(sql)
    
    def _update_batch_record_done(self):
        """
        更新批次表的is_done状态，减少查询任务表的次数
        @return:
        """
        sql = "update {} set is_done = 1, update_time = CURRENT_TIME where batch_date = '{}' and is_done = 0".format(
            self._batch_record_table, self.batch_date
        )
        self._db.update(sql)
    
    def _update_batch_record_done_cache_date(self):
        # 更新batch_record 表的is_done 状态，减少查询任务表的次数
        sql = 'update {batch_record_table} set is_done = 0 where batch_date = "{batch_date}"'.format(
            batch_record_table=self._batch_record_table,
            batch_date=self._batch_date_cache,
        )
        self._db.update(sql)
    
    def _update_task_status(self, task_ids: List):
        """
        更新任务状态
        @return:
        """
        task_ids = str(
            tuple(task_ids)
        ).replace(",)", ")")
        sql = "update %s set %s = 2 where id in %s" % (
            self._task_table,
            self._task_state,
            task_ids,
        )
        self._db.update(sql)
    
    def _reset_lose_task(self):
        """
        @summary: 重置丢失任务为待做
        ---------
        ---------
        @result:
        """
        sql = "update {table} set {state} = 0 where {state} = 2{task_condition}".format(
            table=self._task_table,
            state=self._task_state,
            task_condition=self._task_condition_prefix_and,
        )
        return self._db.update(sql)
    
    def _reset_task(self):
        """
        @summary: 初始化任务表中的任务， 新一个批次开始时调用。
        ---------
        ---------
        @result:
        """
        sql = "update {task_table} set {state} = 0 where {state} != -1{task_condition}".format(
            task_table=self._task_table,
            state=self._task_state,
            task_condition=self._task_condition_prefix_and,
        )
        return self._db.update(sql)
    
    def _add_batch_record(self, batch_date, total_task_count) -> Optional[int]:
        """
        新增一个批次记录
        @return:
        """
        sql = (
            "insert into %s (batch_date, done_count, total_count, `interval`, interval_unit, create_time) values ('%s', %s, %s, %s, '%s', CURRENT_TIME)"
            % (
                self._batch_record_table,
                batch_date,
                0,
                total_task_count,
                self._batch_interval
                if self._batch_interval >= 1
                else self._batch_interval * 24,
                "day" if self._batch_interval >= 1 else "hour",
            )
        )
        
        affect_count = self._db.add(sql)  # None / 0 / 1 (1 为成功)
        return affect_count
    
    def _create_batch_record_table(self):
        sql = (
            "select table_name from information_schema.tables where table_name like '%s'"
            % self._batch_record_table
        )
        tables_name = self._db.find(sql)
        if not tables_name:
            sql = """
                CREATE TABLE `{table_name}` (
                      `id` int(11) UNSIGNED NOT NULL AUTO_INCREMENT,
                      `batch_date` {batch_date} DEFAULT NULL COMMENT '批次时间',
                      `total_count` int(11) DEFAULT NULL COMMENT '任务总数',
                      `done_count` int(11) DEFAULT NULL COMMENT '完成数 (1,-1)',
                      `fail_count` int(11) DEFAULT NULL COMMENT '失败任务数 (-1)',
                      `interval` float(11) DEFAULT NULL COMMENT '批次间隔',
                      `interval_unit` varchar(20) DEFAULT NULL COMMENT '批次间隔单位 day, hour',
                      `create_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '批次开始时间',
                      `update_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '本条记录更新时间',
                      `is_done` int(11) DEFAULT '0' COMMENT '批次是否完成 0 未完成  1 完成',
                      PRIMARY KEY (`id`)
                    ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;
            """.format(
                table_name=self._batch_record_table,
                batch_date="date" if self._date_format == "%Y-%m-%d" else "datetime",
            )
            
            self._db.execute(sql)

# TODO:
# class BatchMongoDBMixin(BatchDBMixinBase):
#     """
#     与数据库交互
#     """
#
#     def _get_task_state_count(self):
#         """
#         获取任务状态及总数
#         @return:
#         """
#         task_state_count = self._mongodb.run_command({
#             "aggregate": self._task_table,
#             "pipeline": [
#                 {"$match": self._task_condition_prefix_where},
#                 {"$group": {"_id": self._task_state, "count": {"$sum": 1}}},
#                 {"$project": {"state": "$_id", "count": "$count"}}
#             ]
#         })
#         return task_state_count
#
#     def _update_batch_record(self):
#         """
#         @summary: 更新批次表中的任务状态
#         ---------
#         ---------
#         @result:
#         """
#         task_count = self.__get_task_state_count()
#
#         self._mongodb.update(
#             self._batch_record_table,
#             data={
#                 'done_count': task_count.get('done_count'),
#                 'total_count': task_count.get('total_count'),
#                 'failed_count': task_count.get('failed_count'),
#                 'update_time': datetime.datetime.now(),
#                 'is_done': 0,
#                 'interval': self._batch_interval if self._batch_interval >= 1 else self._batch_interval * 24,
#                 'interval_unit': "day" if self._batch_interval >= 1 else "hour",
#             },
#             condition={
#                 'batch_date': self.batch_date
#             }
#         )
#
#     def update_is_done(self):
#         self._mongodb.update(
#             self._batch_record_table,
#             data={
#                 'is_done': 1,
#                 'update_time': datetime.datetime.now(),
#             },
#             condition={
#                 'batch_date': self.batch_date,
#                 'is_done': 0
#             }
#         )
#
#     def _get_todo_task(self):
#         """
#         从数据库从取出代执行的任务
#         @return:
#         """
#         tasks = self._mongodb.find(
#             self._task_table,
#             condition={self._task_state: 0, **self._task_condition_prefix_and},
#             limit=self._task_limit,
#             projection={key: 1 for key in self._task_keys},
#             order={self._task_order_by: 0}
#         )
#         return tasks
#
#     def _update_task_status(self, task_ids: List):
#         """
#         更新任务状态
#         @return:
#         """
#         self._mongodb.update(
#             self._task_table,
#             data={self._task_state: 2},
#             condition={'_id': {'$in': task_ids}}
#         )
#
#     def get_lose_task_record(self) -> Tuple:
#         """
#         获取任务丢失的记录
#         @return:
#         """
#         # sql = 'select date_format(batch_date, "{date_format}"), total_count, done_count from {batch_record_table} order by id desc limit 1'.format(
#         #     date_format=self._date_format.replace(":%M", ":%i"),
#         #     batch_record_table=self._batch_record_table,
#         # )
#         batch_info = self._mongodb.find(
#             self._batch_record_table,
#             limit=1,
#             projection={'_id': 0, 'batch_date': 1, 'total_count': 1, 'done_count': 1},
#             sort={'_id': -1}
#         )
#         batch_info = batch_info[0]
#         return batch_info
#
#     def _reset_lose_task(self):
#         """
#         @summary: 重置丢失任务为待做
#         ---------
#         ---------
#         @result:
#         """
#         return self._mongodb.update(
#             self._task_table,
#             {self._task_state: 0},
#             {self._task_table: 2, **self._task_condition_prefix_and}
#         )
#
#     def _reset_task(self):
#         """
#         @summary: 初始化任务表中的任务， 新一个批次开始时调用。
#         ---------
#         ---------
#         @result:
#         """
#
#         # sql = "update {task_table} set {state} = 0 where {state} != -1{task_condition}".format(
#         #     task_table=self._task_table,
#         #     state=self._task_state,
#         #     task_condition=self._task_condition_prefix_and,
#         # )
#         return self._mongodb.update(
#             self._task_table,
#             data={self._task_state: 0},
#             condition={self._task_condition: -1, **self._task_condition_prefix_and}
#         )
#
#     def _get_latest_batch_record(self):
#         """
#         获取最新的批次记录数据
#         @return:
#         """
#         return self._mongodb.find(
#             self._batch_record_table,
#             limit=1,
#             projection={'_id': 0, 'batch_date': 1, 'total_count': 1, 'done_count': 1},
#             sort={'_id': -1}
#         )
#
#     def get_latest_batch_status(self):
#         """
#         获取最新的一批的任务是否执行完毕
#         @return:
#         """
#         is_done = self._mongodb.find(
#             self._related_batch_record,
#             order=-1,
#             limit=1,
#             projection={'_id': 0, 'is_done': 1}
#         )
#         return is_done
#
#     def get_latest_batch_record_info(self):
#         batch_info = self._mongodb.find(
#             self._batch_record_table,
#             projection={'_id': 1, 'batch_date': 1, 'total_count': 1, 'done_count': 1, 'is_done': 1},
#             order={'_id': -1},
#             limit=1
#         )
#
#         # 查看批次记录表任务状态
#         # sql = 'select date_format(batch_date, "{date_format}"), total_count, done_count, is_done from {batch_record_table} order by id desc limit 1'.format(
#         #     date_format=self._date_format.replace(":%M", ":%i"),
#         #     batch_record_table=self._batch_record_table,
#         # )
#         #
#         return batch_info
#
#     def _get_task_total_count(self) -> int:
#         """
#         获取完整的任务数
#         @return:
#         """
#         total_task_count = self._mongodb.run_command({
#             'count': self._task_table,
#             'query': self._task_condition_prefix_where
#         })['n']
#         return total_task_count
#
#     def _add_batch_record(self, batch_date, total_task_count) -> Optional[int]:
#         """
#         新增一个批次记录
#         @return:
#         """
#         affect_count = self._mongodb.add(
#             self._batch_record_table,
#             data={
#                 'batch_date': batch_date,
#                 'done_count': 0,
#                 'total_count': total_task_count,
#                 'interval': self._batch_interval if self._batch_interval >= 1 else self._batch_interval * 24,
#                 'interval_unit': "day" if self._batch_interval >= 1 else "hour",
#                 'create_time': datetime.datetime.now()
#             }
#         )
#
#     def _get_done_or_doing_tasks(self, limit=0):
#         """
#         获取已完成及正在进行中的任务
#         :@param limit: 数据数量限制
#         @return:
#         """
#         tasks = self._mongodb.find(
#             self._task_table,
#             condition={'$or': [{self._task_state: 0}, {self._task_state: 2}], **self._task_condition_prefix_and},
#             limit=limit
#         )
#         return tasks
#
#     def update_batch_record_status(self):
#         """
#         更新批次的状态
#         @return:
#         """
#         self._mongodb.update(
#             self._batch_date_cache,
#             data={'is_done': 0},
#             condition={'batch_date': self._batch_date_cache}
#         )
