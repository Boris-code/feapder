# -*- coding: utf-8 -*-
"""
Created on 2021/4/25 10:22 上午
---------
@summary: 将浏览器的cookie转为request的cookie
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import sys

from feapder.utils.tools import dumps_json


class CreateParams:
    def get_data(self):
        """
        @summary: 从控制台读取多行
        ---------
        ---------
        @result:
        """
        print("请输入请求地址")
        data = []
        while True:
            line = sys.stdin.readline().strip()
            if not line:
                break

            data.append(line)

        return "".join(data)

    def get_params(self, url):
        params_json = {}
        params = url.split("?")[-1].split("&")
        for param in params:
            key_value = param.split("=", 1)
            params_json[key_value[0]] = key_value[1]

        return params_json

    def create(self):
        data = self.get_data()

        params = self.get_params(data)
        url = data.split("?")[0]

        print(f'url = "{url}"')
        print(f"params = {dumps_json(params)}")
