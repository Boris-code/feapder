# -*- coding: utf-8 -*-
"""
Created on 2021/4/8 11:32 上午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""


class PerfectDict(dict):
    """
    >>> from feapder.utils.perfect_dict import PerfectDict
    >>> data = PerfectDict(id=1, url="xxx")
    >>> data
    {'id': 1, 'url': 'xxx'}
    >>> data.id
    1
    >>> data.get("id")
    1
    >>> data["id"]
    1
    >>> id, url = data
    >>> id
    1
    >>> url
    'xxx'
    >>> data[0]
    1
    >>> data[1]
    'xxx'
    >>> data = PerfectDict({"id":1, "url":"xxx"})
    >>> data
    {'id': 1, 'url': 'xxx'}
    """

    def __init__(self, _dict: dict = None, _values: list = None, **kwargs):
        self.__dict__ = _dict or kwargs or {}
        super().__init__(self.__dict__, **kwargs)
        self.__values__ = _values or list(self.__dict__.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.__values__[key]
        else:
            return self.__dict__[key]

    def __iter__(self, *args, **kwargs):
        for value in self.__values__:
            yield value
