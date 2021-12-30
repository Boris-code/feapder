# -*- coding: utf-8 -*-
"""
Created on 2021-03-02 23:40:37
---------
@summary:
---------
@author: Boris
"""

import feapder


class ParamParser(feapder.BaseParser):

    def __init__(self, *args, **kwargs):
        # super().__init__()
        self.abc = kwargs['abc']

    def start_requests(self):
        """
        注意 这里继承的是BaseParser，而不是Spider
        """
        print('start_requests: {}'.format(self.abc))
        yield feapder.Request("https://news.sina.com.cn/")

    def parse(self, request, response):
        print('parse: {}'.format(self.abc))

        yield
