# -*- coding: utf-8 -*-
"""
Created on 2018-12-08 16:50
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import logging
import os
import sys
from logging.handlers import BaseRotatingHandler

from better_exceptions import format_exception

import feapder.setting as setting

LOG_FORMAT = "%(threadName)s|%(asctime)s|%(filename)s|%(funcName)s|line:%(lineno)d|%(levelname)s| %(message)s"
PRINT_EXCEPTION_DETAILS = True


# 重写 RotatingFileHandler 自定义log的文件名
# 原来 xxx.log xxx.log.1 xxx.log.2 xxx.log.3 文件由近及远
# 现在 xxx.log xxx1.log xxx2.log  如果backupCount 是2位数时  则 01  02  03 三位数 001 002 .. 文件由近及远
class RotatingFileHandler(BaseRotatingHandler):
    def __init__(
        self, filename, mode="a", maxBytes=0, backupCount=0, encoding=None, delay=0
    ):
        # if maxBytes > 0:
        #    mode = 'a'
        BaseRotatingHandler.__init__(self, filename, mode, encoding, delay)
        self.maxBytes = maxBytes
        self.backupCount = backupCount
        self.placeholder = str(len(str(backupCount)))

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = ("%0" + self.placeholder + "d.") % i  # '%2d.'%i -> 02
                sfn = sfn.join(self.baseFilename.split("."))
                # sfn = "%d_%s" % (i, self.baseFilename)
                # dfn = "%d_%s" % (i + 1, self.baseFilename)
                dfn = ("%0" + self.placeholder + "d.") % (i + 1)
                dfn = dfn.join(self.baseFilename.split("."))
                if os.path.exists(sfn):
                    # print "%s -> %s" % (sfn, dfn)
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = (("%0" + self.placeholder + "d.") % 1).join(
                self.baseFilename.split(".")
            )
            if os.path.exists(dfn):
                os.remove(dfn)
            # Issue 18940: A file may not have been created if delay is True.
            if os.path.exists(self.baseFilename):
                os.rename(self.baseFilename, dfn)
        if not self.delay:
            self.stream = self._open()

    def shouldRollover(self, record):

        if self.stream is None:  # delay was set...
            self.stream = self._open()
        if self.maxBytes > 0:  # are we rolling over?
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, 2)  # due to non-posix-compliant Windows feature
            if self.stream.tell() + len(msg) >= self.maxBytes:
                return 1
        return 0


def get_logger(
    name, path="", log_level="DEBUG", is_write_to_file=False, is_write_to_stdout=True
):
    """
    @summary: 获取log
    ---------
    @param name: log名
    @param path: log文件存储路径 如 D://xxx.log
    @param log_level: log等级 CRITICAL/ERROR/WARNING/INFO/DEBUG
    @param is_write_to_file: 是否写入到文件 默认否
    ---------
    @result:
    """
    name = name.split(os.sep)[-1].split(".")[0]  # 取文件名

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    formatter = logging.Formatter(LOG_FORMAT)
    if PRINT_EXCEPTION_DETAILS:
        formatter.formatException = lambda exc_info: format_exception(*exc_info)

    # 定义一个RotatingFileHandler，最多备份5个日志文件，每个日志文件最大10M
    if is_write_to_file:
        if path and not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        rf_handler = RotatingFileHandler(
            path, mode="w", maxBytes=10 * 1024 * 1024, backupCount=20, encoding="utf8"
        )
        rf_handler.setFormatter(formatter)
        logger.addHandler(rf_handler)
    if is_write_to_stdout:
        stream_handler = logging.StreamHandler()
        stream_handler.stream = sys.stdout
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    _handler_list = []
    _handler_name_list = []
    # 检查是否存在重复handler
    for _handler in logger.handlers:
        if str(_handler) not in _handler_name_list:
            _handler_name_list.append(str(_handler))
            _handler_list.append(_handler)
    logger.handlers = _handler_list
    return logger


# logging.disable(logging.DEBUG) # 关闭所有log

# 不让打印log的配置
STOP_LOGS = [
    # ES
    "urllib3.response",
    "urllib3.connection",
    "elasticsearch.trace",
    "requests.packages.urllib3.util",
    "requests.packages.urllib3.util.retry",
    "urllib3.util",
    "requests.packages.urllib3.response",
    "requests.packages.urllib3.contrib.pyopenssl",
    "requests.packages",
    "urllib3.util.retry",
    "requests.packages.urllib3.contrib",
    "requests.packages.urllib3.connectionpool",
    "requests.packages.urllib3.poolmanager",
    "urllib3.connectionpool",
    "requests.packages.urllib3.connection",
    "elasticsearch",
    "log_request_fail",
    # requests
    "requests",
    "selenium.webdriver.remote.remote_connection",
    "selenium.webdriver.remote",
    "selenium.webdriver",
    "selenium",
    # markdown
    "MARKDOWN",
    "build_extension",
    # newspaper
    "calculate_area",
    "largest_image_url",
    "newspaper.images",
    "newspaper",
    "Importing",
    "PIL",
]

# 关闭日志打印
for STOP_LOG in STOP_LOGS:
    log_level = eval("logging." + setting.OTHERS_LOG_LEVAL)
    logging.getLogger(STOP_LOG).setLevel(log_level)

# print(logging.Logger.manager.loggerDict) # 取使用debug模块的name

# 日志级别大小关系为：critical > error > warning > info > debug
log = get_logger(
    name=setting.LOG_NAME,
    path=setting.LOG_PATH,
    log_level=setting.LOG_LEVEL,
    is_write_to_file=setting.LOG_IS_WRITE_TO_FILE,
)


def reload():
    global log
    log = get_logger(
        name=setting.LOG_NAME,
        path=setting.LOG_PATH,
        log_level=setting.LOG_LEVEL,
        is_write_to_file=setting.LOG_IS_WRITE_TO_FILE,
    )


log.reload = reload
