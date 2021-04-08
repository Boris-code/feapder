# -*- coding: utf-8 -*-
"""
Created on 2021/4/8 1:06 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from feapder.utils.perfect_dict import PerfectDict


task_key = ["id", "url"]
task = [1, "http://www.badu.com"]
task = Task(_dict=dict(zip(task_key, task)), _values=task)

task = Task(id=1, url="http://www.badu.com")
task = Task({"id":"1", "url":"http://www.badu.com"})

print(task)
id, url = task
print(id, url)
print(task[0], task[1])
print(task.id, task.url)
print(task["id"], task["url"])
print(task.get("id"), task.get("url"))
