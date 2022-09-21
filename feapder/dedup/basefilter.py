# -*- coding: utf-8 -*-
"""
Created on 2022/9/21 11:17 AM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import abc
from typing import List, Union


class BaseFilter:
    @abc.abstractmethod
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
        pass

    @abc.abstractmethod
    def get(self, keys: Union[List[str], str]) -> Union[List[bool], bool]:
        """
        检查数据是否存在
        Args:
            keys: list / 单个值

        Returns:
            list / 单个值 (如果数据已存在 返回 1 否则返回 0)
        """
        pass
