# -*- coding: utf-8 -*-
"""
Created on 2022/4/10 5:57 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import requests
from requests.adapters import HTTPAdapter

from feapder.network.downloader import Downloader
from feapder.network.response import Response


class RequestsDownloader(Downloader):
    def download(self, method, url, **kwargs) -> Response:
        response = requests.request(method, url, **kwargs)
        response = Response(response)
        return response


class RequestsSessionDownloader(Downloader):
    session = None

    @property
    def _session(self):
        if not self.__class__.session:
            self.__class__.session = requests.Session()
            # pool_connections – 缓存的 urllib3 连接池个数  pool_maxsize – 连接池中保存的最大连接数
            http_adapter = HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
            # 任何使用该session会话的 HTTP 请求，只要其 URL 是以给定的前缀开头，该传输适配器就会被使用到。
            self.__class__.session.mount("http", http_adapter)

        return self.__class__.session

    def download(self, method, url, **kwargs) -> Response:
        response = self._session.request(method, url, **kwargs)
        response = Response(response)
        return response
