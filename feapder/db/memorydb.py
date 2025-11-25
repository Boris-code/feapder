# -*- coding: utf-8 -*-
"""
Created on 2020/4/21 11:42 PM
---------
@summary: 基于内存的队列，代替redis
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
from queue import PriorityQueue

from feapder import setting


class MemoryDB:
    def __init__(self):
        self.priority_queue = PriorityQueue(maxsize=setting.TASK_MAX_CACHED_SIZE)

    def add(self, item, ignore_max_size=False):
        """
        添加任务
        :param item: 数据: 支持小于号比较的类 或者 （priority, item）
        :param ignore_max_size: queue满时是否等待，为True时无视队列的maxsize，直接往里塞
        :return:
        """
        if ignore_max_size:
            self.priority_queue._put(item)
            self.priority_queue.unfinished_tasks += 1
        else:
            self.priority_queue.put(item)

    def get(self, timeout: float = 1):
        """
        获取任务（阻塞模式）
        :param timeout: 超时时间（秒），默认1秒
        :return: 任务对象，超时返回None
        """
        try:
            item = self.priority_queue.get(timeout=timeout)
            return item
        except:
            return

    def get_nowait(self):
        """
        获取任务（非阻塞模式）

        立即返回，队列为空时返回None，不会阻塞等待。
        用于QPS调度器快速获取请求。

        :return: 任务对象，队列为空返回None
        """
        try:
            item = self.priority_queue.get_nowait()
            return item
        except:
            return None

    def empty(self):
        return self.priority_queue.empty()
