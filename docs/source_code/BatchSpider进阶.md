# BatchSpider

## BatchSpider参数

```python
def __init__(
    self,
    task_table,
    batch_record_table,
    batch_name,
    batch_interval,
    task_keys,
    task_state="state",
    min_task_count=10000,
    check_task_interval=5,
    task_limit=10000,
    related_redis_key=None,
    related_batch_record=None,
    task_condition="",
    task_order_by="",
    redis_key=None,
    thread_count=None,
    begin_callback=None,
    end_callback=None,
    delete_keys=(),
    auto_stop_when_spider_done=None,
    send_run_time=False,
):
    """
    @summary: 批次爬虫
    必要条件
    1、需有任务表
        任务表中必须有id 及 任务状态字段 如 state。如指定parser_name字段，则任务会自动下发到对应的parser下, 否则会下发到所有的parser下。其他字段可根据爬虫需要的参数自行扩充

        参考建表语句如下：
        CREATE TABLE `table_name` (
          `id` int(11) NOT NULL AUTO_INCREMENT,
          `param` varchar(1000) DEFAULT NULL COMMENT '爬虫需要的抓取数据需要的参数',
          `state` int(11) DEFAULT NULL COMMENT '任务状态',
          `parser_name` varchar(255) DEFAULT NULL COMMENT '任务解析器的脚本类名',
          PRIMARY KEY (`id`),
          UNIQUE KEY `nui` (`param`) USING BTREE
        ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8;

    2、需有批次记录表 不存在自动创建
    ---------
    @param task_table: mysql中的任务表
    @param batch_record_table: mysql 中的批次记录表
    @param batch_name: 批次采集程序名称
    @param batch_interval: 批次间隔 天为单位。 如想一小时一批次，可写成1/24
    @param task_keys: 需要获取的任务字段 列表 [] 如需指定解析的parser，则需将parser_name字段取出来。
    @param task_state: mysql中任务表的任务状态字段
    @param min_task_count: redis 中最少任务数, 少于这个数量会从mysql的任务表取任务
    @param check_task_interval: 检查是否还有任务的时间间隔；
    @param task_limit: 从数据库中取任务的数量
    @param redis_key: 任务等数据存放在redis中的key前缀
    @param thread_count: 线程数，默认为配置文件中的线程数
    @param begin_callback: 爬虫开始回调函数
    @param end_callback: 爬虫结束回调函数
    @param delete_keys: 爬虫启动时删除的key，类型: 元组/bool/string。 支持正则; 常用于清空任务队列，否则重启时会断点续爬
    @param auto_stop_when_spider_done: 爬虫抓取完毕后是否自动结束或等待任务，默认自动结束
    @param send_run_time: 发送运行时间
    @param related_redis_key: 有关联的其他爬虫任务表（redis）注意：要避免环路 如 A -> B & B -> A 。
    @param related_batch_record: 有关联的其他爬虫批次表（mysql）注意：要避免环路 如 A -> B & B -> A 。
        related_redis_key 与 related_batch_record 选其一配置即可；用于相关联的爬虫没结束时，本爬虫也不结束
        若相关连的爬虫为批次爬虫，推荐以related_batch_record配置，
        若相关连的爬虫为普通爬虫，无批次表，可以以related_redis_key配置
    @param task_condition: 任务条件 用于从一个大任务表中挑选出数据自己爬虫的任务，即where后的条件语句
    @param task_order_by: 取任务时的排序条件 如 id desc
    ---------
    @result:
    """
```

下面介绍下理解起来可能有疑惑的参数

### 1. related_redis_key 与 related_batch_record

这两个参数用于采集之间有关联的爬虫，比如列表爬虫和详情爬虫，详情的任务需依赖列表爬虫生产，列表爬虫没采集完毕，详情爬虫要处于等待状态。

举例说明：BatchSpider依赖Spider

```

def crawl_list():
    """
    普通爬虫 Spider
    """
    spider = spider_test.SpiderTest(redis_key="feapder:list")
    spider.start()


def crawl_detail(args):
    """
    批次爬虫 BatchSpider
    @param args: 1 / 2 / init
    """
    spider = batch_spider_test.BatchSpiderTest(
        task_table="list_task",  # mysql中的任务表
        batch_record_table="list_batch_record",  # mysql中的批次记录表
        batch_name="详情爬虫(周全)",  # 批次名字
        batch_interval=7,  # 批次时间 天为单位 若为小时 可写 1 / 24
        task_keys=["id", "item_id"],  # 需要获取任务表里的字段名，可添加多个
        redis_key="feapder:detail",  # redis中存放request等信息的根key
        task_state="state",  # mysql中任务状态字段
        related_redis_key="feapder:list:z_requsets"
    )

    if args == 1:
        spider.start_monitor_task()
    elif args == 2:
        spider.start()
```

若批次爬虫和批次爬虫之前有依赖，除了设置related_redis_key参数外，还支持设置related_batch_record参数，指定对方的批次记录表即可。两个参数二选一

### 2. task_condition

取任务的条件，可以理解为sql后面的where条件。如获取url不为空的任务且id大于10的任务

    task_condition="url is not null and id > 10"


## BatchSpider方法

BatchSpider继承至BatchParser，并且BatchParser是对开发者暴露的常用方法接口，因此推荐先看[BatchParser](source_code/BatchParser)，BatchSpider方法如下：

### init_task 任务初始化

init_task函数会在每个批次开始时调用，用于将已完成的任务状态重置为0。

因此当本函数被重写为空时，可实现增量抓取

```
def init_task(self):
    pass
```

当手动调用本函数时，可将任务状态刷新为0，开发阶段经常使用

    spider.init_task()
    

## 其他细节

### 1. 任务防丢

BatchSpider除了支持Spider的[任务防丢机制](source_code/Spider进阶?id=_1-任务防丢)外，还多了一层mysql任务表的保障，mysql任务表中每条任务都有任务状态，BatchSpider有任务丢失重发机制，直到所有任务都处于成功或者失败两种状态，才算采集结束。

### 2. 任务重试

> 与Spider相同

任务请求失败或解析函数抛出异常时，会自动重试，默认重试次数为100次，可通过配置文件`SPIDER_MAX_RETRY_TIMES`参数修改。当任务超过最大重试次数时，默认会将失败的任务存储到Redis的`{redis_key}:z_failed_requsets`里，供人工排查。

相关配置为：

```python
# 每个请求最大重试次数
SPIDER_MAX_RETRY_TIMES = 100 
# 重新尝试失败的requests 当requests重试次数超过允许的最大重试次数算失败
RETRY_FAILED_REQUESTS = False
# 保存失败的request
SAVE_FAILED_REQUEST = True
# 任务失败数 超过WARNING_FAILED_COUNT则报警
WARNING_FAILED_COUNT = 1000
```

当`RETRY_FAILED_REQUESTS=True`时，爬虫再次启动时会将失败的任务重新下发到任务队列中，重新抓取

### 3. 去重

> 与Spider相同

支持任务去重和数据去重，任务默认是临时去重，去重库保留1个月，即只去重1个月内的任务，数据是永久去重。默认去重是关闭的，相关配置为：

```
ITEM_FILTER_ENABLE = False # item 去重
REQUEST_FILTER_ENABLE = False # request 去重
```

修改默认去重库：

```
from feapder.buffer.request_buffer import RequestBuffer
from feapder.buffer.item_buffer import ItemBuffer
from feapder.dedup import Dedup

RequestBuffer.dedup = Dedup(filter_type=MemoryError)
ItemBuffer.dedup = Dedup(filter_type=MemoryError)
```

RequestBuffer 为任务入库前缓冲的buffer，ItemBuffer为数据入库前缓冲的buffer

关于去重库详情见：[海量数据去重](source_code/dedup)

### 4. 加速采集

> 与Spider相同

与爬虫采集速度的相关配置为：

```python
# 爬虫相关
# COLLECTOR
COLLECTOR_SLEEP_TIME = 1 # 从任务队列中获取任务到内存队列的间隔
COLLECTOR_TASK_COUNT = 10 # 每次获取任务数量

# SPIDER
SPIDER_THREAD_COUNT = 1 # 爬虫并发数
SPIDER_SLEEP_TIME = 0 # 下载时间间隔（解析完一个response后休眠时间）
SPIDER_MAX_RETRY_TIMES = 100 # 每个请求最大重试次数
# 是否主动执行添加 设置为False 需要手动调用start_monitor_task，适用于多进程情况下

```

COLLECTOR 为从任务队列中取任务到内存队列的线程，SPIDER为实际采集的线程

`COLLECTOR_TASK_COUNT` 建议 >= `SPIDER_THREAD_COUNT`, 这样每个线程的爬虫才有任务可做。但COLLECTOR_TASK_COUNT不建议过大，不然分布式时，一个池子里的任务都被节点A取走了，其他节点取不到任务了。

### 了解更多

更多配置，详见[配置文件](source_code/配置文件)
