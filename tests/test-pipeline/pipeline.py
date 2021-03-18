# -*- coding: utf-8 -*-
"""
Created on 2021/3/18 12:39 上午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from feapder.pipelines import BasePipeline
from typing import Dict, List, Tuple


class Pipeline(BasePipeline):
    """
    pipeline 是单线程的，批量保存数据的操作，不建议在这里写网络请求代码，如下载图片等
    """

    def save_items(self, table, items: List[Dict]) -> bool:
        """
        保存数据
        Args:
            table: 表名
            items: 数据，[{},{},...]

        Returns: 是否保存成功 True / False
                 若False，不会将本批数据入到去重库，以便再次入库

        """

        print("自定义pipeline， 保存数据 >>>>", table, items)

        return True

    def update_items(self, table, items: List[Dict], update_keys=Tuple) -> bool:
        """
        更新数据, 与UpdateItem配合使用，若爬虫中没使用UpdateItem，则可不实现此接口
        Args:
            table: 表名
            items: 数据，[{},{},...]
            update_keys: 更新的字段, 如 ("title", "publish_time")

        Returns: 是否更新成功 True / False
                 若False，不会将本批数据入到去重库，以便再次入库

        """

        print("自定义pipeline， 更新数据 >>>>", table, items, update_keys)

        return True
