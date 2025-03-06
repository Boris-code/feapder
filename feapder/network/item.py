# -*- coding: utf-8 -*-
"""
Created on 2018-07-26 22:28:10
---------
@summary: 定义实体
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import re

import feapder.utils.tools as tools


class ItemMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs.setdefault("__name__", None)
        attrs.setdefault("__table_name__", None)
        attrs.setdefault("__name_underline__", None)
        attrs.setdefault("__update_key__", None)
        attrs.setdefault("__unique_key__", None)
        attrs.setdefault("__pipelines__", None)

        return type.__new__(cls, name, bases, attrs)


class Item(metaclass=ItemMetaclass):
    __unique_key__ = []

    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    def __repr__(self):
        return "<{}: {}>".format(self.item_name, tools.dumps_json(self.to_dict))

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def update(self, *args, **kwargs):
        """
        更新字段，与字典使用方法一致
        """
        self.__dict__.update(*args, **kwargs)

    def update_strict(self, *args, **kwargs):
        """
        更新严格更新，只更新item中有的字段
        """
        for key, value in dict(*args, **kwargs).items():
            if key in self.__dict__:
                self.__dict__[key] = value

    def pre_to_db(self):
        """
        入库前的处理
        """
        pass

    @property
    def to_dict(self):
        propertys = {}
        for key, value in self.__dict__.items():
            if key not in (
                "__name__",
                "__table_name__",
                "__name_underline__",
                "__update_key__",
                "__unique_key__",
                "__pipelines__",
            ):
                if key.startswith(f"_{self.__class__.__name__}"):
                    key = key.replace(f"_{self.__class__.__name__}", "")
                propertys[key] = value

        return propertys

    def to_sql(self, auto_update=False, update_columns=()):
        return tools.make_insert_sql(
            self.table_name, self.to_dict, auto_update, update_columns
        )

    @property
    def item_name(self):
        return self.__name__ or self.__class__.__name__

    @item_name.setter
    def item_name(self, name):
        self.__name__ = name
        self.__table_name__ = re.sub("_item$", "", self.name_underline)

    @property
    def table_name(self):
        if not self.__table_name__:
            self.__table_name__ = re.sub("_item$", "", self.name_underline)
        return self.__table_name__

    @table_name.setter
    def table_name(self, name):
        self.__table_name__ = name
        self.__name__ = tools.key2hump(name) + "Item"

    @property
    def name_underline(self):
        if not self.__name_underline__:
            self.__name_underline__ = tools.key2underline(self.item_name)

        return self.__name_underline__

    @name_underline.setter
    def name_underline(self, name):
        self.__name_underline__ = name

    @property
    def unique_key(self):
        return self.__unique_key__ or self.__class__.__unique_key__

    @unique_key.setter
    def unique_key(self, keys):
        if isinstance(keys, (tuple, list)):
            self.__unique_key__ = keys
        else:
            self.__unique_key__ = (keys,)

    @property
    def fingerprint(self):
        args = []
        for key, value in self.to_dict.items():
            if value:
                if (self.unique_key and key in self.unique_key) or not self.unique_key:
                    args.append(key + str(value))

        if args:
            args = sorted(args)
            return tools.get_md5(*args)
        else:
            return None

    def to_UpdateItem(self):
        update_item = UpdateItem(**self.__dict__)
        update_item.item_name = self.item_name
        return update_item


class UpdateItem(Item):
    __update_key__ = []
    __pipelines__ = None

    def __init__(self, **kwargs):
        super(UpdateItem, self).__init__(**kwargs)

    @property
    def update_key(self):
        return self.__update_key__ or self.__class__.__update_key__

    @update_key.setter
    def update_key(self, keys):
        if isinstance(keys, (tuple, list)):
            self.__update_key__ = keys
        else:
            self.__update_key__ = (keys,)
