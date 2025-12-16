# -*- coding: utf-8 -*-
"""
Created on 2018-06-19 17:17
---------
@summary: item 管理器， 负责缓冲添加到数据库中的item， 由该manager统一添加。防止多线程同时访问数据库
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import threading
from queue import Queue

import feapder.utils.tools as tools
from feapder import setting
from feapder.db.redisdb import RedisDB
from feapder.dedup import Dedup
from feapder.network.item import Item, UpdateItem
from feapder.pipelines import BasePipeline
from feapder.pipelines.mysql_pipeline import MysqlPipeline
from feapder.utils import metrics
from feapder.utils.log import log

MYSQL_PIPELINE_PATH = "feapder.pipelines.mysql_pipeline.MysqlPipeline"


class ItemBuffer(threading.Thread):
    dedup = None
    __redis_db = None

    def __init__(self, redis_key, task_table=None):
        if not hasattr(self, "_table_item"):
            super(ItemBuffer, self).__init__()

            self._thread_stop = False
            self._is_adding_to_db = False
            self._redis_key = redis_key
            self._task_table = task_table

            self._items_queue = Queue(maxsize=setting.ITEM_MAX_CACHED_COUNT)

            self._table_request = setting.TAB_REQUESTS.format(redis_key=redis_key)
            self._table_failed_items = setting.TAB_FAILED_ITEMS.format(
                redis_key=redis_key
            )

            self._item_tables = {
                # 'item_name': 'table_name' # 缓存item名与表名对应关系
            }

            self._item_update_keys = {
                # 'table_name': ['id', 'name'...] # 缓存table_name与__update_key__的关系
            }

            self._item_pipelines = {
                # 'table_name': ['pipeline1', 'pipeline2'] # 缓存table_name与pipelines的关系
            }

            self._pipelines = self.load_pipelines()

            self._have_mysql_pipeline = MYSQL_PIPELINE_PATH in setting.ITEM_PIPELINES
            self._mysql_pipeline = None

            if setting.ITEM_FILTER_ENABLE and not self.__class__.dedup:
                if setting.ITEM_FILTER_SETTING.get(
                        "filter_type"
                ) == Dedup.BloomFilter or setting.ITEM_FILTER_SETTING.get("name"):
                    self.__class__.dedup = Dedup(
                        to_md5=False, **setting.ITEM_FILTER_SETTING
                    )
                else:
                    self.__class__.dedup = Dedup(
                        to_md5=False,
                        name=self._redis_key,
                        **setting.ITEM_FILTER_SETTING,
                    )

            # 导出重试的次数
            self.export_retry_times = 0
            # 导出失败的次数 TODO 非air爬虫使用redis统计
            self.export_falied_times = 0

    @property
    def redis_db(self):
        if self.__class__.__redis_db is None:
            self.__class__.__redis_db = RedisDB()

        return self.__class__.__redis_db

    def load_pipelines(self):
        pipelines = []
        for pipeline_path in setting.ITEM_PIPELINES:
            pipeline = tools.import_cls(pipeline_path)()
            if not isinstance(pipeline, BasePipeline):
                raise ValueError(f"{pipeline_path} 需继承 feapder.pipelines.BasePipeline")
            pipelines.append(pipeline)

        return pipelines

    @property
    def mysql_pipeline(self):
        if not self._mysql_pipeline:
            self._mysql_pipeline = tools.import_cls(MYSQL_PIPELINE_PATH)()

        return self._mysql_pipeline

    def run(self):
        self._thread_stop = False
        while not self._thread_stop:
            self.flush()
            tools.delay_time(setting.ITEM_UPLOAD_INTERVAL)

        self.close()

    def stop(self):
        self._thread_stop = True
        self._started.clear()

    def put_item(self, item):
        if isinstance(item, Item):
            # 入库前的回调
            item.pre_to_db()

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

                if data_count >= setting.ITEM_UPLOAD_BATCH_MAX_SIZE:
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
        @return: 表名与数据的字典
        """
        datas_dict = {
            # 'table_name': [{}, {}]
        }

        while items:
            item = items.pop(0)
            # 取item下划线格式的名
            # 下划线类的名先从dict中取，没有则现取，然后存入dict。加快下次取的速度
            item_name = item.item_name
            table_name = self._item_tables.get(item_name)
            if not table_name:
                table_name = item.table_name
                self._item_tables[item_name] = table_name
                self._item_pipelines[table_name] = item.pipelines

            if is_update_item and table_name not in self._item_update_keys:
                self._item_update_keys[table_name] = item.update_key

            if table_name not in datas_dict:
                datas_dict[table_name] = []

            datas_dict[table_name].append(item.to_dict)

        return datas_dict

    def __export_to_db(self, table, datas, is_update=False, update_keys=(), used_pipelines=None):
        pipelines = used_pipelines or self._pipelines  # 优先采用指定的pipelines
        for pipeline in pipelines:
            if is_update:
                if table == self._task_table and not isinstance(
                        pipeline, MysqlPipeline
                ):
                    continue

                if not pipeline.update_items(table, datas, update_keys=update_keys):
                    log.error(
                        f"{pipeline.__class__.__name__} 更新数据失败. table: {table}  items: {datas}"
                    )
                    return False

            else:
                if not pipeline.save_items(table, datas):
                    log.error(
                        f"{pipeline.__class__.__name__} 保存数据失败. table: {table}  items: {datas}"
                    )
                    return False

        # 若是任务表, 且上面的pipeline里没mysql，则需调用mysql更新任务
        if not self._have_mysql_pipeline and is_update and table == self._task_table:
            if not self.mysql_pipeline.update_items(
                    table, datas, update_keys=update_keys
            ):
                log.error(
                    f"{self.mysql_pipeline.__class__.__name__} 更新数据失败. table: {table}  items: {datas}"
                )
                return False

        self.metric_datas(table=table, datas=datas)
        return True

    def __add_item_to_db(
            self, items, update_items, requests, callbacks, items_fingerprints
    ):
        export_success = True
        self._is_adding_to_db = True

        # 去重
        if setting.ITEM_FILTER_ENABLE:
            items, items_fingerprints = self.__dedup_items(items, items_fingerprints)

        # 分捡（返回值包含 pipelines_dict）
        items_dict = self.__pick_items(items)
        update_items_dict = self.__pick_items(update_items, is_update_item=True)

        # item批量入库
        failed_items = {"add": [], "update": [], "requests": []}
        while items_dict:
            table, datas = items_dict.popitem()
            used_pipelines = self._item_pipelines.get(table)

            log.debug(
                """
                -------------- item 批量入库 --------------
                表名: %s
                datas: %s
                    """
                % (table, tools.dumps_json(datas, indent=16))
            )

            if not self.__export_to_db(table, datas, used_pipelines=used_pipelines):
                export_success = False
                failed_items["add"].append({"table": table, "datas": datas})

        # 执行批量update
        while update_items_dict:
            table, datas = update_items_dict.popitem()
            used_pipelines = self._item_pipelines.get(table)

            log.debug(
                """
                -------------- item 批量更新 --------------
                表名: %s
                datas: %s
                    """
                % (table, tools.dumps_json(datas, indent=16))
            )

            update_keys = self._item_update_keys.get(table)
            if not self.__export_to_db(
                    table, datas, is_update=True, update_keys=update_keys, used_pipelines=used_pipelines
            ):
                export_success = False
                failed_items["update"].append(
                    {"table": table, "datas": datas, "update_keys": update_keys}
                )

        if export_success:
            # 执行回调
            while callbacks:
                try:
                    callback = callbacks.pop(0)
                    callback()
                except Exception as e:
                    log.exception(e)

            # 删除做过的request
            if requests:
                self.redis_db.zrem(self._table_request, requests)

            # 去重入库
            if setting.ITEM_FILTER_ENABLE:
                if items_fingerprints:
                    self.__class__.dedup.add(items_fingerprints, skip_check=True)
        else:
            failed_items["requests"] = requests

            if self.export_retry_times > setting.EXPORT_DATA_MAX_RETRY_TIMES:
                if self._redis_key != "air_spider":
                    # 失败的item记录到redis
                    self.redis_db.sadd(self._table_failed_items, failed_items)

                    # 删除做过的request
                    if requests:
                        self.redis_db.zrem(self._table_request, requests)

                    log.error(
                        "入库超过最大重试次数，不再重试，数据记录到redis，items:\n {}".format(
                            tools.dumps_json(failed_items)
                        )
                    )
                self.export_retry_times = 0

            else:
                tip = ["入库不成功"]
                if callbacks:
                    tip.append("不执行回调")
                if requests:
                    tip.append("不删除任务")
                    exists = self.redis_db.zexists(self._table_request, requests)
                    for exist, request in zip(exists, requests):
                        if exist:
                            self.redis_db.zadd(self._table_request, requests, 300)

                if setting.ITEM_FILTER_ENABLE:
                    tip.append("数据不入去重库")

                if self._redis_key != "air_spider":
                    tip.append("将自动重试")

                tip.append("失败items:\n {}".format(tools.dumps_json(failed_items)))
                log.error("，".join(tip))

                self.export_falied_times += 1

                if self._redis_key != "air_spider":
                    self.export_retry_times += 1

            if self.export_falied_times > setting.EXPORT_DATA_MAX_FAILED_TIMES:
                # 报警
                msg = "《{}》爬虫导出数据失败，失败次数：{}，请检查爬虫是否正常".format(
                    self._redis_key, self.export_falied_times
                )
                log.error(msg)
                tools.send_msg(
                    msg=msg,
                    level="error",
                    message_prefix="《%s》爬虫导出数据失败" % (self._redis_key),
                )

        self._is_adding_to_db = False

    def metric_datas(self, table, datas):
        """
        打点 记录总条数及每个key情况
        @param table: 表名
        @param datas: 数据 列表
        @return:
        """
        total_count = 0
        for data in datas:
            total_count += 1
            for k, v in data.items():
                metrics.emit_counter(k, int(bool(v)), classify=table)
        metrics.emit_counter("total count", total_count, classify=table)

    def close(self):
        # 调用pipeline的close方法
        for pipeline in self._pipelines:
            try:
                pipeline.close()
            except:
                pass
