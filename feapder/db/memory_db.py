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


class MemoryDB:
    def __init__(self):
        self.priority_queue = PriorityQueue()

    def add(self, item):
        """
        添加任务
        :param item: 数据: 支持小于号比较的类 或者 （priority, item）
        :return:
        """
        self.priority_queue.put(item)

    def get(self):
        """
        获取任务
        :return:
        """
        try:
            item = self.priority_queue.get_nowait()
            return item
        except:
            return

    def empty(self):
        return self.priority_queue.empty()
