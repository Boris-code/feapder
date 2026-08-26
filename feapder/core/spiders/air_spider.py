# -*- coding: utf-8 -*-
"""
Created on 2020/4/22 12:05 AM
---------
@summary: 基于内存队列的爬虫，不支持分布式
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

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
from feapder.utils.tail_thread import TailThread


class AirSpider(BaseParser, TailThread):
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
        self._item_buffer = ItemBuffer(redis_key=self.name)
        self._request_buffer = AirSpiderRequestBuffer(
            db=self._memory_db, dedup_name=self.name
        )

        # 智能上下文分析
        if self.__class__.__custom_setting__.get("SMART_CONTEXT_ENABLE", False):
            import threading
            from feapder.utils.context_analyzer import ContextAnalyzer

            # 初始化线程本地存储
            if Request._request_context is None:
                Request._request_context = threading.local()

            # 执行静态分析
            analyzer = ContextAnalyzer(self.__class__)

            # 1. 分析每个回调自己需要的参数（direct 模式）
            callback_needs = analyzer.analyze()
            Request._callback_needs = callback_needs

            # 2. 构建回调依赖图（谁 yield 了谁）
            callback_graph = analyzer.build_callback_graph()

            # 3. 计算传递性需求（transitive 模式）
            transitive_needs = analyzer.compute_transitive_needs(
                callback_graph, callback_needs
            )
            Request._transitive_needs = transitive_needs

            if callback_needs:
                log.info(f"[AirSpider] 智能上下文分析完成，检测到 {len(callback_needs)} 个回调函数")
                for callback_name, params in callback_needs.items():
                    log.debug(f"[智能上下文] 直接需求 {callback_name}: {params}")

                # 如果有传递性需求，也打印日志
                if transitive_needs:
                    log.debug(f"[智能上下文] 传递性需求计算完成")
                    for callback_name, params in transitive_needs.items():
                        if params != callback_needs.get(callback_name, set()):
                            log.debug(f"[智能上下文] 传递需求 {callback_name}: {params}")
            else:
                log.warning("[智能上下文] 未检测到任何回调函数使用自定义参数")

        self._stop_spider = False
        metrics.init(**setting.METRICS_OTHER_ARGS)

    def distribute_task(self):
        for request in self.start_requests():
            if not isinstance(request, Request):
                raise ValueError("仅支持 yield Request")

            request.parser_name = request.parser_name or self.name
            self._request_buffer.put_request(request, ignore_max_size=False)

    def all_thread_is_done(self):
        for i in range(3):  # 降低偶然性, 因为各个环节不是并发的，很有可能当时状态为假，但检测下一条时该状态为真。一次检测很有可能遇到这种偶然性
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

            tools.delay_time(1)

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
                if self._stop_spider or self.all_thread_is_done():
                    # 停止 parser_controls
                    for parser_control in self._parser_controls:
                        parser_control.stop()

                    # 关闭item_buffer
                    self._item_buffer.stop()

                    # 关闭webdirver
                    Request.render_downloader and Request.render_downloader.close_all()

                    if self._stop_spider:
                        log.info("爬虫被终止")
                    else:
                        log.info("无任务，爬虫结束")
                    break

            except Exception as e:
                log.exception(e)

            tools.delay_time(1)  # 1秒钟检查一次爬虫状态

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

    def stop_spider(self):
        self._stop_spider = True
