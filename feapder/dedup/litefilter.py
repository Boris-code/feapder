# -*- coding: utf-8 -*-
"""
Created on 2022/9/21 11:28 AM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
from typing import List, Union, Set

from feapder.dedup.basefilter import BaseFilter


class LiteFilter(BaseFilter):
    def __init__(self):
        self.datas: Set[str] = set()

    def add(
        self, keys: Union[List[str], str], *args, **kwargs
    ) -> Union[List[bool], bool]:
        """

        Args:
            keys: list / 单个值
            *args:
            **kwargs:

        Returns:
            list / 单个值 (如果数据已存在 返回 0 否则返回 1, 可以理解为是否添加成功)
        """
        is_exist = self.get(keys)

        if isinstance(keys, list):
            self.datas.update(keys)
            is_add = [1 ^ exist for exist in is_exist]
        else:
            self.datas.add(keys)
            is_add = 1 ^ is_exist
        return is_add

    def get(self, keys: Union[List[str], str]) -> Union[List[bool], bool]:
        """
        检查数据是否存在
        Args:
            keys: list / 单个值

        Returns:
            list / 单个值 (如果数据已存在 返回 1 否则返回 0)
        """
        if isinstance(keys, list):
            return [key in self.datas for key in keys]
        else:
            return keys in self.datas
