# -*- coding: utf-8 -*-
"""
Created on 2023-06-09 20:26:29
---------
@summary: 爬虫入口
---------
@author: Boris
"""

import feapder

from spiders import *


if __name__ == "__main__":
    test_debugger.TestDebugger.to_DebugSpider(
        request=feapder.Request("https://spidertools.cn", render=True),
        redis_key="test:xxx",
    ).start()
