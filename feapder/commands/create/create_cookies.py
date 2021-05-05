# -*- coding: utf-8 -*-
"""
Created on 2021/4/25 10:22 上午
---------
@summary: 将浏览器的cookie转为request的cookie
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import json
import sys

from feapder.utils.tools import get_cookies_from_str, print_pretty


class CreateCookies:
    def get_data(self):
        """
        @summary: 从控制台读取多行
        ---------
        ---------
        @result:
        """
        print("请输入浏览器cookie (列表或字符串格式)")
        data = []
        while True:
            line = sys.stdin.readline().strip()
            if not line:
                break

            data.append(line)

        return "".join(data)

    def create(self):
        data = self.get_data()
        cookies = {}
        try:
            data_json = json.loads(data)

            for data in data_json:
                cookies[data.get("name")] = data.get("value")

        except:
            cookies = get_cookies_from_str(data)

        print_pretty(cookies)
