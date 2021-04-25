# -*- coding: utf-8 -*-
"""爬虫配置文件"""
import os


# MYSQL
MYSQL_IP = ""
MYSQL_PORT = 3306
MYSQL_DB = ""
MYSQL_USER_NAME = ""
MYSQL_USER_PASS = ""

# MONGODB
MONGO_IP = "localhost"
MONGO_PORT = 27017
MONGO_DB = ""
MONGO_USER_NAME = ""
MONGO_USER_PASS = ""

# REDIS
# IP:PORT
REDISDB_IP_PORTS = "xxx:6379"
REDISDB_USER_PASS = ""
# 默认 0 到 15 共16个数据库
REDISDB_DB = 0
# # 适用于redis哨兵模式
# REDISDB_SERVICE_NAME = None
#
# # 数据入库的pipeline，可自定义，默认MysqlPipeline
ITEM_PIPELINES = [
    "feapder.pipelines.mysql_pipeline.MysqlPipeline",
    # "feapder.pipelines.mongo_pipeline.MongoPipeline",
]
#
# # 爬虫相关
# # COLLECTOR
# COLLECTOR_SLEEP_TIME = 1  # 从任务队列中获取任务到内存队列的间隔
# COLLECTOR_TASK_COUNT = 100  # 每次获取任务数量
#
# # SPIDER
# SPIDER_THREAD_COUNT = 100  # 爬虫并发数
# SPIDER_SLEEP_TIME = 0  # 下载时间间隔（解析完一个response后休眠时间）
# SPIDER_MAX_RETRY_TIMES = 100  # 每个请求最大重试次数
# WARNING_FAILED_COUNT = 1000  # 任务失败数 超过WARNING_FAILED_COUNT则报警
#
# # 浏览器渲染下载
# WEBDRIVER = dict(
#     pool_size=2,  # 浏览器的数量
#     load_images=False,  # 是否加载图片
#     user_agent=None,  # 字符串 或 无参函数，返回值为user_agent
#     proxy=None,  # xxx.xxx.xxx.xxx:xxxx 或 无参函数，返回值为代理地址
#     headless=False,  # 是否为无头浏览器
#     driver_type="CHROME",  # CHROME 或 PHANTOMJS,
#     timeout=30,  # 请求超时时间
#     window_size=(1024, 800),  # 窗口大小
#     executable_path=None,  # 浏览器路径，默认为默认路径
#     render_time=0, # 渲染时长，即打开网页等待指定时间后再获取源码
# )
#
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
# # 爬虫是否自动结束，若为False，则会等待新任务下发，进程不退出
# AUTO_STOP_WHEN_SPIDER_DONE = True
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
# ITEM_FILTER_ENABLE = False  # item 去重
# REQUEST_FILTER_ENABLE = False  # request 去重
#
# 报警 支持钉钉、企业微信、邮件
# # 钉钉报警
# DINGDING_WARNING_URL = ""  # 钉钉机器人api
# DINGDING_WARNING_PHONE = ""  # 报警人 支持列表，可指定多个
# # 企业微信报警
# WECHAT_WARNING_URL = ""  # 企业微信机器人api
# WECHAT_WARNING_PHONE = ""  # 报警人 将会在群内@此人, 支持列表，可指定多人
# WECHAT_WARNING_ALL = False  # 是否提示所有人， 默认为False
# # 邮件报警
# EAMIL_SENDER = ""  # 发件人
# EAMIL_PASSWORD = ""  # 授权码
# EMAIL_RECEIVER = "" # 收件人 支持列表，可指定多个
# # 报警时间间隔及级别
# WARNING_INTERVAL = 3600  # 相同报警的报警时间间隔，防止刷屏; 0表示不去重
# WARNING_LEVEL = "DEBUG" # 报警级别， DEBUG / ERROR
#
# LOG_NAME = os.path.basename(os.getcwd())
# LOG_PATH = "log/%s.log" % LOG_NAME  # log存储路径
# LOG_LEVEL = "DEBUG"
# LOG_IS_WRITE_TO_FILE = False
