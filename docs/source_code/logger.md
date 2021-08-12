# 日志配置及使用

## 日志配置

见配置文件，相关配置如下：

```python
LOG_NAME = os.path.basename(os.getcwd())
LOG_PATH = "log/%s.log" % LOG_NAME  # log存储路径
LOG_LEVEL = "DEBUG"
LOG_COLOR = True  # 是否带有颜色
LOG_IS_WRITE_TO_CONSOLE = True  # 是否打印到控制台
LOG_IS_WRITE_TO_FILE = False  # 是否写文件
LOG_MODE = "w"  # 写文件的模式
LOG_MAX_BYTES = 10 * 1024 * 1024  # 每个日志文件的最大字节数
LOG_BACKUP_COUNT = 20  # 日志文件保留数量
LOG_ENCODING = "utf8"  # 日志文件编码
OTHERS_LOG_LEVAL = "ERROR"  # 第三方库的log等级
```

框架屏蔽了requests、selenium等一些第三方库的日志，OTHERS_LOG_LEVAL是用来控制这些第三库日志等级的。

## 使用日志工具


```python
from feapder.utils.log import log

log.debug("xxx")
log.info("xxx")
log.warning("xxx")
log.error("xxx")
log.critical("xxx")
```

默认是带有颜色的日志：

![-w583](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/08/06/16282311862710.jpg)

日志等级：CRITICAL > ERROR > WARNING > INFO > DEBUG
