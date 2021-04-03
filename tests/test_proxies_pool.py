# -*- coding: utf-8 -*-
"""
Created on 2021/4/3 4:25 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
from feapder.network.proxy_pool import ProxyPool, check_proxy
import requests

url = "http://tunnel-api.apeyun.com/h?id=2020120800184471713&secret=3U1fEJPuabi3y2QJ&limit=10&format=txt&auth_mode=auto"

proxy_pool = ProxyPool(size=-1, proxy_source_url=url)

print(proxy_pool.get())
#
# headers = {
#     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
#     "Accept-Encoding": "gzip, deflate, br",
#     "Accept-Language": "zh-CN,zh;q=0.9",
#     "Connection": "keep-alive",
# }
#
#
# resp = requests.get(
#     "http://www.baidu.com",
#     headers=headers,
#     proxies={
#         "https": "https://182.106.136.67:13586",
#         "http": "http://182.106.136.67:13586",
#     },
# )
# print(resp.text)
#
# a = check_proxy("182.106.136.67", "13586", show_error_log=True, type=1)
# print(a)
