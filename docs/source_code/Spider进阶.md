# Spider

## Spider参数：

```python
@param redis_key: 任务等数据存放在redis中的key前缀
@param min_task_count: 任务队列中最少任务数, 少于这个数量才会添加任务，默认1。start_monitor_task 模式下生效
@param check_task_interval: 检查是否还有任务的时间间隔；默认5秒
@param thread_count: 线程数，默认为配置文件中的线程数
@param begin_callback: 爬虫开始回调函数
@param end_callback: 爬虫结束回调函数
@param delete_tabs:  爬虫启动时删除的表（redis里的key），元组类型。 支持正则; 常用于清空任务队列，否则重启时会断点续爬
@param auto_stop_when_spider_done: 爬虫抓取完毕后是否自动结束或等待任务，默认自动结束
@param auto_start_requests: 爬虫是否自动添加任务
@param send_run_time: 发送运行时间
@param batch_interval: 抓取时间间隔 默认为0 天为单位 多次启动时，只有当前时间与第一次抓取结束的时间间隔大于指定的时间间隔时，爬虫才启动
@param wait_lock: 下发任务时否等待锁，若不等待锁，可能会存在多进程同时在下发一样的任务，因此分布式环境下请将该值设置True
```

下面介绍下理解起来可能有疑惑的参数

### 1. redis_key

redis_key为redis中存储任务等信息的key前缀，如redis_key="feapder:spider_test", 则redis中会生成如下

![-w365](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/02/21/16139009217536.jpg?x-oss-process=style/markdown-media)

key的命名方式为[配置文件](source_code/配置文件.md)中定义的

    # 任务表模版
    TAB_REQUSETS = "{redis_key}:z_requsets"
    # 任务失败模板
    TAB_FAILED_REQUSETS = "{redis_key}:z_failed_requsets"
    # 爬虫状态表模版
    TAB_SPIDER_STATUS = "{redis_key}:z_spider_status"
    # item 表模版
    TAB_ITEM = "{redis_key}:s_{item_name}"
    # 爬虫时间记录表
    TAB_SPIDER_TIME = "{redis_key}:h_spider_time"
    
### 2. min_task_count

这个参数用于控制最小任务数的，少于这个数量再下发任务，防止redis中堆积任务太多，内存撑爆


----

未完待续
