# -*- coding: utf-8 -*-
"""
Created on 2023/7/25 10:03
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import abc

from feapder.utils.log import log


class BaseProxyPool:
    @abc.abstractmethod
    def get_proxy(self):
        """
        获取代理
        Returns:
            {"http": "xxx", "https": "xxx"}
        """
        raise NotImplementedError

    @abc.abstractmethod
    def del_proxy(self, proxy):
        """
        @summary: 删除代理
        ---------
        @param proxy: ip:port
        """
        raise NotImplementedError

    def tag_proxy(self, **kwargs):
        """
        @summary: 标记代理
        ---------
        @param kwargs:
        @return:
        """
        log.warning("暂不支持标记代理")
        pass
