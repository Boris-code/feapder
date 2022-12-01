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
import threading


class MemoryDB:
    def __init__(self):
        # 添加互斥锁，供多线程提取任务使用
        self.lock = threading.Lock()
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

    def get(self):
        """
        获取任务
        :return:
        """
        try:
            item = self.priority_queue.get(timeout=1)
            return item
        except:
            return

    def empty(self):
        return self.priority_queue.qsize() == 0
