# -*- coding: utf-8 -*-
"""
Created on 2021/3/4 11:26 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from feapder import Request

request = Request("https://www.baidu.com?a=1&b=2", data={}, params=None)
print(request.fingerprint)
request = Request("https://www.baidu.com?b=2&a=1", data={}, params=None)
print(request.fingerprint)

response = request.get_response()
print(response)

print(response.xpath("//a/@href"))
print(response.css("a::attr(href)"))
print(response.css("a::attr(href)").extract_first())

content = response.re("<a.*?href='(.*?)'")
print(content)