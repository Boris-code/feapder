# -*- coding: utf-8 -*-
"""爬虫配置文件"""
import os

# MYSQL
MYSQL_IP = "localhost"
MYSQL_PORT = 3306
MYSQL_DB = "feapder"
MYSQL_USER_NAME = "feapder"
MYSQL_USER_PASS = "feapder123"

# REDIS
# IP:PORT
REDISDB_IP_PORTS = "localhost:6379"
REDISDB_USER_PASS = ""
# 默认 0 到 15 共16个数据库
REDISDB_DB = 0

# # 爬虫相关
# # COLLECTOR
# COLLECTOR_SLEEP_TIME = 1 # 从任务队列中获取任务到内存队列的间隔
# COLLECTOR_TASK_COUNT = 100 # 每次获取任务数量
#
# # SPIDER
# SPIDER_THREAD_COUNT = 10 # 爬虫并发数
# SPIDER_SLEEP_TIME = 0 # 下载时间间隔（解析完一个response后休眠时间）
# SPIDER_MAX_RETRY_TIMES = 100 # 每个请求最大重试次数

# # 重新尝试失败的requests 当requests重试次数超过允许的最大重试次数算失败
# RETRY_FAILED_REQUESTS = False
# # request 超时时间，超过这个时间重新做（不是网络请求的超时时间）单位秒
# REQUEST_TIME_OUT = 600  # 10分钟
# # 保存失败的request
# SAVE_FAILED_REQUEST = True
#
# # 下载缓存 利用redis缓存，由于内存小，所以仅供测试时使用
# RESPONSE_CACHED_ENABLE = False  # 是否启用下载缓存 成本高的数据或容易变需求的数据，建议设置为True
# RESPONSE_CACHED_EXPIRE_TIME = 3600  # 缓存时间 秒
# RESPONSE_CACHED_USED = False  # 是否使用缓存 补采数据时可设置为True
#
# WARNING_FAILED_COUNT = 1000  # 任务失败数 超过WARNING_FAILED_COUNT则报警
#
# # 爬虫初始化工作
# # 爬虫做完request后是否自动结束或者等待任务
# AUTO_STOP_WHEN_SPIDER_DONE = True
# # 是否将item添加到 mysql 支持列表 指定添加的item 可模糊指定
# ADD_ITEM_TO_MYSQL = True
# # 是否将item添加到 redis 支持列表 指定添加的item 可模糊指定
# ADD_ITEM_TO_REDIS = False
#
#
# # 设置代理
# PROXY_EXTRACT_API = None  # 代理提取API ，返回的代理分割符为\r\n
# PROXY_ENABLE = True
#
# # 随机headers
# RANDOM_HEADERS = True
# # requests 使用session
# USE_SESSION = False
#
# # 去重
# ITEM_FILTER_ENABLE = False # item 去重
# REQUEST_FILTER_ENABLE = False # request 去重
#
# # 报警
# DINGDING_WARNING_URL = "" # 钉钉机器人api
# DINGDING_WARNING_PHONE = "" # 报警人
# LINGXI_TOKEN = "" # 灵犀报警token
#
# LOG_NAME = os.path.basename(os.getcwd())
# LOG_PATH = "log/%s.log" % LOG_NAME  # log存储路径
# LOG_LEVEL = "DEBUG"
# LOG_IS_WRITE_TO_FILE = False
# OTHERS_LOG_LEVAL = "ERROR"  # 第三方库的log等级
