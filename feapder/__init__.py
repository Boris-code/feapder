# -*- coding: utf-8 -*-
"""
Created on 2020/4/21 10:41 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import os
import re
import sys

sys.path.insert(0, re.sub(r"([\\/]items$)|([\\/]spiders$)", "", os.getcwd()))

__all__ = [
    "AirSpider",
    "TaskSpider",
    "Spider",
    "BatchSpider",
    "BaseParser",
    "BatchParser",
    "Request",
    "Response",
    "Item",
    "UpdateItem",
    "ArgumentParser",
]

from feapder.core.spiders import Spider, BatchSpider, AirSpider, TaskSpider
from feapder.core.base_parser import BaseParser, BatchParser
from feapder.network.request import Request
from feapder.network.response import Response
from feapder.network.item import Item, UpdateItem
from feapder.utils.custom_argparse import ArgumentParser
