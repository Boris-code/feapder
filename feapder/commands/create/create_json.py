# -*- coding: utf-8 -*-
"""
Created on 2018-08-28 17:38:43
---------
@summary: 字符串转json
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import sys

import feapder.utils.tools as tools


class CreateJson:
    def get_data(self):
        """
        @summary: 从控制台读取多行
        ---------
        ---------
        @result:
        """
        data = []
        while True:
            line = sys.stdin.readline().strip().replace("\t", " " * 4)
            if not line:
                break

            data.append(line)

        return data

    def create(self, sort_keys=False):
        contents = self.get_data()

        json = {}
        for content in contents:
            content = content.strip()
            if not content or content.startswith(":"):
                continue

            regex = "([^:\s]*)[:|\s]*(.*)"

            result = tools.get_info(content, regex, fetch_one=True)
            if result[0] in json:
                json[result[0]] = json[result[0]] + "&" + result[1]
            else:
                json[result[0]] = result[1].strip()

        print(tools.dumps_json(json, sort_keys=sort_keys))