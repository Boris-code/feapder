# -*- coding: utf-8 -*-
"""
Created on 2020/4/22 12:05 AM
---------
@summary: 基于内存队列的爬虫，不支持分布式
---------
@author: Boris
@email: boris@bzkj.tech
"""

from threading import Thread

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.core.base_parser import BaseParse
from feapder.core.parser_control import AirSpiderParserControl
from feapder.db.memory_db import MemoryDB
from feapder.network.request import Request
from feapder.utils.log import log


class AirSpider(BaseParse, Thread):
    __custom_setting__ = {}

    def __init__(self, parser_count=1, *parser_args, **parser_kwargs):
        """
        基于内存队列的爬虫，不支持分布式
        :param parser_count: 线程数
        :param parser_args:
        :param parser_kwargs:
        """
        super(AirSpider, self).__init__()

        for key, value in self.__class__.__custom_setting__.items():
            setattr(setting, key, value)

        self._parser_count = setting.PARSER_COUNT if not parser_count else parser_count

        self._parser_args = parser_args
        self._parser_kwargs = parser_kwargs

        self._memory_db = MemoryDB()
        self._parser_controls = []

    def distribute_task(self):
        for request in self.start_requests(*self._parser_args, **self._parser_kwargs):
            if not isinstance(request, Request):
                raise ValueError("仅支持 yield Request")

            request.parser_name = request.parser_name or self.name
            self._memory_db.add(request)

    def all_thread_is_done(self):
        for i in range(3):  # 降低偶然性, 因为各个环节不是并发的，很有可能当时状态为假，但检测下一条时该状态为真。一次检测很有可能遇到这种偶然性
            # 检测 parser_control 状态
            for parser_control in self._parser_controls:
                if not parser_control.is_not_task():
                    return False

            # 检测 任务队列 状态
            if not self._memory_db.empty():
                return False

            tools.delay_time(1)

        return True

    def run(self):
        self.distribute_task()

        for i in range(self._parser_count):
            parser_control = AirSpiderParserControl(self._memory_db)
            parser_control.add_parser(self)
            parser_control.start()
            self._parser_controls.append(parser_control)

        while True:
            if self.all_thread_is_done():
                # 停止 parser_controls
                for parser_control in self._parser_controls:
                    parser_control.stop()

                log.debug("无任务，爬虫结束")
                break
