# -*- coding: utf-8 -*-
"""
Created on 2021/4/8 11:32 上午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""


def ensure_value(value):
    if isinstance(value, (list, tuple)):
        _value = []
        for v in value:
            _value.append(ensure_value(v))

        if isinstance(value, tuple):
            value = tuple(_value)
        else:
            value = _value

    if isinstance(value, dict):
        return PerfectDict(value)
    else:
        return value


class PerfectDict(dict):
    """
    >>> data = PerfectDict({"id":1, "url":"xxx"})
    >>> data
    {'id': 1, 'url': 'xxx'}
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
    >>> data = PerfectDict({"a": 1, "b": {"b1": 2}, "c": [{"c1": [{"d": 1}]}]})
    >>> data.b.b1
    2
    >>> data[1].b1
    2
    >>> data.get("b").b1
    2
    >>> data.c[0].c1
    [{'d': 1}]
    >>> data.c[0].c1[0]
    {'d': 1}
    """

    def __init__(self, _dict: dict = None, _values: list = None, **kwargs):
        self.__dict__ = _dict or kwargs or {}
        self.__dict__.pop("__values__", None)
        super().__init__(self.__dict__, **kwargs)
        self.__values__ = _values or list(self.__dict__.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            value = self.__values__[key]
        else:
            value = self.__dict__[key]

        return ensure_value(value)

    def __iter__(self, *args, **kwargs):
        for value in self.__values__:
            yield ensure_value(value)

    def __getattribute__(self, item):
        value = object.__getattribute__(self, item)
        if item == "__dict__" or item == "__values__":
            return value
        return ensure_value(value)

    def get(self, key, default=None):
        if key in self.__dict__:
            value = self.__dict__[key]
            return ensure_value(value)

        return default
