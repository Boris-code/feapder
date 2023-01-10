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
    ) -> Union[List[int], int]:
        """

        Args:
            keys: list / 单个值
            *args:
            **kwargs:

        Returns:
            list / 单个值 (如果数据已存在 返回 0 否则返回 1, 可以理解为是否添加成功)
        """
        if isinstance(keys, list):
            is_add = []
            for key in keys:
                if key not in self.datas:
                    self.datas.add(key)
                    is_add.append(1)
                else:
                    is_add.append(0)
        else:
            if keys not in self.datas:
                is_add = 1
                self.datas.add(keys)
            else:
                is_add = 0
        return is_add

    def get(self, keys: Union[List[str], str]) -> Union[List[int], int]:
        """
        检查数据是否存在
        Args:
            keys: list / 单个值

        Returns:
            list / 单个值 (如果数据已存在 返回 1 否则返回 0)
        """
        if isinstance(keys, list):
            temp_set = set()
            is_exist = []
            for key in keys:
                # 数据本身重复或者数据在去重库里
                if key in temp_set or key in self.datas:
                    is_exist.append(1)
                else:
                    is_exist.append(0)
                    temp_set.add(key)

            return is_exist
        else:
            return int(keys in self.datas)
