# -*- coding: utf-8 -*-
"""
Created on 2022/10/19 10:40 AM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
from queue import Queue

import requests

import feapder.setting as setting
from feapder.utils import metrics
from feapder.utils import tools
from feapder.utils.log import log


class ProxyPool:
    def __init__(self, proxy_api=setting.PROXY_EXTRACT_API, **kwargs):
        self.proxy_api = proxy_api
        self.proxy_queue = Queue()

    def format_proxy(self, proxy):
        return {"http": "http://" + proxy, "https": "http://" + proxy}

    @tools.retry(3, interval=5)
    def pull_proxies(self):
        resp = requests.get(self.proxy_api)
        proxies = resp.text.strip()
        resp.close()
        if "{" in proxies:
            raise Exception("获取代理失败", proxies)
        # 使用 /r/n 分隔
        return proxies.split("\r\n")

    def get_proxy(self):
        try:
            if self.proxy_queue.empty():
                proxies = self.pull_proxies()
                for proxy in proxies:
                    self.proxy_queue.put_nowait(proxy)
                    metrics.emit_counter("total", 1, classify="proxy")

            proxy = self.proxy_queue.get_nowait()
            self.proxy_queue.put_nowait(proxy)

            metrics.emit_counter("used_times", 1, classify="proxy")

            return self.format_proxy(proxy)
        except Exception as e:
            tools.send_msg("获取代理失败", level="error")
            raise Exception("获取代理失败", e)

    get = get_proxy

    def del_proxy(self, proxy):
        """
        @summary: 删除代理
        ---------
        @param proxy: ip:port
        """
        if proxy in self.proxy_queue.queue:
            self.proxy_queue.queue.remove(proxy)
            metrics.emit_counter("invalid", 1, classify="proxy")

    def tag_proxy(self, **kwargs):
        """
        @summary: 标记代理
        ---------
        @param kwargs:
        @return:
        """
        log.warning("暂不支持标记代理")
        pass
