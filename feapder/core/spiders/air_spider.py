# -*- coding: utf-8 -*-
"""
Created on 2020/4/22 12:05 AM
---------
@summary: 基于内存队列的爬虫，不支持分布式
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from threading import Thread

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.buffer.item_buffer import ItemBuffer
from feapder.buffer.request_buffer import AirSpiderRequestBuffer
from feapder.core.base_parser import BaseParser
from feapder.core.parser_control import AirSpiderParserControl
from feapder.db.memorydb import MemoryDB
from feapder.network.request import Request
from feapder.utils import metrics
from feapder.utils.log import log


class AirSpider(BaseParser, Thread):
    __custom_setting__ = {}

    def __init__(self, thread_count=None):
        """
        基于内存队列的爬虫，不支持分布式
        :param thread_count: 线程数
        """
        super(AirSpider, self).__init__()

        for key, value in self.__class__.__custom_setting__.items():
            setattr(setting, key, value)

        if thread_count:
            setattr(setting, "SPIDER_THREAD_COUNT", thread_count)
        self._thread_count = setting.SPIDER_THREAD_COUNT

        self._memory_db = MemoryDB()
        self._parser_controls = []
        self._item_buffer = ItemBuffer(redis_key="air_spider")
        self._request_buffer = AirSpiderRequestBuffer(
            db=self._memory_db, dedup_name=self.name
        )

        metrics.init(**setting.METRICS_OTHER_ARGS)

    def distribute_task(self):
        for request in self.start_requests():
            if not isinstance(request, Request):
                raise ValueError("仅支持 yield Request")

            request.parser_name = request.parser_name or self.name
            self._request_buffer.put_request(request)

    def all_thread_is_done(self):
        # 检测 parser_control 状态
        for parser_control in self._parser_controls:
            if not parser_control.is_not_task():
                return False

        # 检测 任务队列 状态
        if not self._memory_db.empty():
            return False

        # 检测 item_buffer 状态
        if (
            self._item_buffer.get_items_count() > 0
            or self._item_buffer.is_adding_to_db()
        ):
            return False

        return True

    def run(self):
        self.start_callback()

        for i in range(self._thread_count):
            parser_control = AirSpiderParserControl(
                memory_db=self._memory_db,
                request_buffer=self._request_buffer,
                item_buffer=self._item_buffer,
            )
            parser_control.add_parser(self)
            parser_control.start()
            self._parser_controls.append(parser_control)

        self._item_buffer.start()

        self.distribute_task()

        while True:
            try:
                if self.all_thread_is_done():
                    # 停止 parser_controls
                    for parser_control in self._parser_controls:
                        parser_control.stop()

                    # 关闭item_buffer
                    self._item_buffer.stop()

                    # 关闭webdirver
                    Request.render_downloader and Request.render_downloader.close_all()

                    log.info("无任务，爬虫结束")
                    break

            except Exception as e:
                log.exception(e)

            tools.delay_time(0.1)  # 1秒钟检查一次爬虫状态

        self.end_callback()
        # 为了线程可重复start
        self._started.clear()
        # 关闭打点
        metrics.close()

    def join(self, timeout=None):
        """
        重写线程的join
        """
        if not self._started.is_set():
            return

        super().join()
    
    def get_all_task_status_count(self):
        '''
        获取所有任务统计
        _failed_task_count： 失败任务数
        _success_task_count：成功任务数
        _total_task_count：  任务总数
        任务总数包含重试任务
        '''
        _failed_task_count, _success_task_count, _total_task_count = 0, 0, 0
        for parser_control in self._parser_controls:
            _failed, _success, _total = parser_control.get_task_status_count()
            _failed_task_count  += _failed
            _success_task_count += _success
            _total_task_count   += _total
        return _failed_task_count, _success_task_count, _total_task_count
