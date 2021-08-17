# -*- coding: utf-8 -*-
"""爬虫配置文件"""
# import os
# import sys
#
# # MYSQL
# MYSQL_IP = "localhost"
# MYSQL_PORT = 3306
# MYSQL_DB = ""
# MYSQL_USER_NAME = ""
# MYSQL_USER_PASS = ""
#
# # MONGODB
# MONGO_IP = "localhost"
# MONGO_PORT = 27017
# MONGO_DB = ""
# MONGO_USER_NAME = ""
# MONGO_USER_PASS = ""
#
# # REDIS
# # ip:port 多个可写为列表或者逗号隔开 如 ip1:port1,ip2:port2 或 ["ip1:port1", "ip2:port2"]
# REDISDB_IP_PORTS = "localhost:6379"
# REDISDB_USER_PASS = ""
# REDISDB_DB = 0
# # 适用于redis哨兵模式
# REDISDB_SERVICE_NAME = ""
#
# # 数据入库的pipeline，可自定义，默认MysqlPipeline
# ITEM_PIPELINES = [
#     "feapder.pipelines.mysql_pipeline.MysqlPipeline",
#     # "feapder.pipelines.mongo_pipeline.MongoPipeline",
# ]
# EXPORT_DATA_MAX_FAILED_TIMES = 10 # 导出数据时最大的失败次数，包括保存和更新，超过这个次数报警
# EXPORT_DATA_MAX_RETRY_TIMES = 10 # 导出数据时最大的重试次数，包括保存和更新，超过这个次数则放弃重试
#
# # 爬虫相关
# # COLLECTOR
# COLLECTOR_SLEEP_TIME = 1  # 从任务队列中获取任务到内存队列的间隔
# COLLECTOR_TASK_COUNT = 10  # 每次获取任务数量
#
# # SPIDER
# SPIDER_THREAD_COUNT = 1  # 爬虫并发数
# SPIDER_SLEEP_TIME = 0  # 下载时间间隔 单位秒。 支持随机 如 SPIDER_SLEEP_TIME = [2, 5] 则间隔为 2~5秒之间的随机数，包含2和5
# SPIDER_TASK_COUNT = 1  # 每个parser从内存队列中获取任务的数量
# SPIDER_MAX_RETRY_TIMES = 100  # 每个请求最大重试次数
# KEEP_ALIVE = False  # 爬虫是否常驻
#
# # 浏览器渲染
# WEBDRIVER = dict(
#     pool_size=1,  # 浏览器的数量
#     load_images=True,  # 是否加载图片
#     user_agent=None,  # 字符串 或 无参函数，返回值为user_agent
#     proxy=None,  # xxx.xxx.xxx.xxx:xxxx 或 无参函数，返回值为代理地址
#     headless=False,  # 是否为无头浏览器
#     driver_type="CHROME",  # CHROME、PHANTOMJS、FIREFOX
#     timeout=30,  # 请求超时时间
#     window_size=(1024, 800),  # 窗口大小
#     executable_path=None,  # 浏览器路径，默认为默认路径
#     render_time=0,  # 渲染时长，即打开网页等待指定时间后再获取源码
#     custom_argument=["--ignore-certificate-errors"],  # 自定义浏览器渲染参数
# )
#
# # 爬虫启动时，重新抓取失败的requests
# RETRY_FAILED_REQUESTS = False
# # 保存失败的request
# SAVE_FAILED_REQUEST = True
# # request防丢机制。（指定的REQUEST_LOST_TIMEOUT时间内request还没做完，会重新下发 重做）
# REQUEST_LOST_TIMEOUT = 600  # 10分钟
# # request网络请求超时时间
# REQUEST_TIMEOUT = 22  # 等待服务器响应的超时时间，浮点数，或(connect timeout, read timeout)元组
#
# # 下载缓存 利用redis缓存，但由于内存大小限制，所以建议仅供开发调试代码时使用，防止每次debug都需要网络请求
# RESPONSE_CACHED_ENABLE = False  # 是否启用下载缓存 成本高的数据或容易变需求的数据，建议设置为True
# RESPONSE_CACHED_EXPIRE_TIME = 3600  # 缓存时间 秒
# RESPONSE_CACHED_USED = False  # 是否使用缓存 补采数据时可设置为True
#
# # 设置代理
# PROXY_EXTRACT_API = None  # 代理提取API ，返回的代理分割符为\r\n
# PROXY_ENABLE = True
#
# # 随机headers
# RANDOM_HEADERS = True
# # UserAgent类型 支持 'chrome', 'opera', 'firefox', 'internetexplorer', 'safari'，'mobile' 若不指定则随机类型
# USER_AGENT_TYPE = "chrome"
# # 默认使用的浏览器头 RANDOM_HEADERS=True时不生效
# DEFAULT_USERAGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"
# # requests 使用session
# USE_SESSION = False
#
# # 去重
# ITEM_FILTER_ENABLE = False  # item 去重
# REQUEST_FILTER_ENABLE = False  # request 去重
#
# # 报警 支持钉钉、企业微信、邮件
# # 钉钉报警
# DINGDING_WARNING_URL = ""  # 钉钉机器人api
# DINGDING_WARNING_PHONE = ""  # 报警人 支持列表，可指定多个
# DINGDING_WARNING_ALL = False # 是否提示所有人， 默认为False
# # 邮件报警
# EMAIL_SENDER = ""  # 发件人
# EMAIL_PASSWORD = ""  # 授权码
# EMAIL_RECEIVER = ""  # 收件人 支持列表，可指定多个
# EMAIL_SMTPSERVER = "smtp.163.com" # 邮件服务器 默认为163邮箱
# # 企业微信报警
# WECHAT_WARNING_URL = ""  # 企业微信机器人api
# WECHAT_WARNING_PHONE = ""  # 报警人 将会在群内@此人, 支持列表，可指定多人
# WECHAT_WARNING_ALL = False  # 是否提示所有人， 默认为False
# # 时间间隔
# WARNING_INTERVAL = 3600  # 相同报警的报警时间间隔，防止刷屏; 0表示不去重
# WARNING_LEVEL = "DEBUG"  # 报警级别， DEBUG / ERROR
# WARNING_FAILED_COUNT = 1000  # 任务失败数 超过WARNING_FAILED_COUNT则报警
#
# LOG_NAME = os.path.basename(os.getcwd())
# LOG_PATH = "log/%s.log" % LOG_NAME  # log存储路径
# LOG_LEVEL = "DEBUG"
# LOG_COLOR = True  # 是否带有颜色
# LOG_IS_WRITE_TO_CONSOLE = True # 是否打印到控制台
# LOG_IS_WRITE_TO_FILE = False  # 是否写文件
# LOG_MODE = "w"  # 写文件的模式
# LOG_MAX_BYTES = 10 * 1024 * 1024  # 每个日志文件的最大字节数
# LOG_BACKUP_COUNT = 20  # 日志文件保留数量
# LOG_ENCODING = "utf8"  # 日志文件编码
# OTHERS_LOG_LEVAL = "ERROR"  # 第三方库的log等级
#
# # 切换工作路径为当前项目路径
# project_path = os.path.abspath(os.path.dirname(__file__))
# os.chdir(project_path)  # 切换工作路经
# sys.path.insert(0, project_path)
# print('当前工作路径为 ' + os.getcwd())
