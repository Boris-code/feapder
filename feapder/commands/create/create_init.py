# -*- coding: utf-8 -*-
"""
Created on 2018-08-28 17:38:43
---------
@summary: 创建__init__.py
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

from feapder.utils.tools import dumps_json


class CreateInit:
    def create(self):
        __all__ = []

        import os

        path = os.getcwd()
        for file in os.listdir(path):
            if file.endswith(".py") and not file.startswith("__init__"):
                model = file.split(".")[0]
                __all__.append(model)

        del os

        with open("__init__.py", "w", encoding="utf-8") as file:
            text = "__all__ = %s" % dumps_json(__all__)
            file.write(text)
