# TaskSpider

TaskSpider是一款分布式爬虫，内部封装了取种子任务的逻辑，内置支持从redis或者mysql获取任务，也可通过自定义实现从其他来源获取任务

## 1. 创建项目

参考 [Spider](usage/Spider?id=_1-创建项目)

## 2. 创建爬虫

命令行 TODO

示例代码：

```python
import feapder
from feapder import ArgumentParser


class TestTaskSpider(feapder.TaskSpider):
    # 自定义数据库，若项目中有setting.py文件，此自定义可删除
    __custom_setting__ = dict(
        REDISDB_IP_PORTS="localhost:6379",
        REDISDB_USER_PASS="",
        REDISDB_DB=0,
        MYSQL_IP="localhost",
        MYSQL_PORT=3306,
        MYSQL_DB="feapder",
        MYSQL_USER_NAME="feapder",
        MYSQL_USER_PASS="feapder123",
    )
    
    def add_task(self):
        # 加种子任务
        self._redisdb.zadd(self._task_table, {"id": 1, "url": "https://www.baidu.com"})

    def start_requests(self, task):
        task_id, url = task
        yield feapder.Request(url, task_id=task_id)

    def parse(self, request, response):
        # 提取网站title
        print(response.xpath("//title/text()").extract_first())
        # 提取网站描述
        print(response.xpath("//meta[@name='description']/@content").extract_first())
        print("网站地址: ", response.url)

        # mysql 需要更新任务状态为做完 即 state=1
        # yield self.update_task_batch(request.task_id)
        
def start(args):
    """
    用mysql做种子表
    """
    spider = TestTaskSpider(
        task_table="spider_task", # 任务表名
        task_keys=["id", "url"], # 表里查询的字段
        redis_key="test:task_spider", # redis里做任务队列的key
        keep_alive=True, # 是否常驻
        delete_keys=True, # 重启时是否删除redis里的key，若想断点续爬，设置False
    )
    if args == 1:
        spider.start_monitor_task()
    else:
        spider.start()


def start2(args):
    """
    用redis做种子表
    """
    spider = TestTaskSpider(
        task_table="spider_task2", # 任务表名
        task_table_type="redis", # 任务表类型为redis
        redis_key="test:task_spider", # redis里做任务队列的key
        keep_alive=True, # 是否常驻
        delete_keys=True, # 重启时是否删除redis里的key，若想断点续爬，设置False
    )
    if args == 1:
        spider.start_monitor_task()
    else:
        spider.start()


if __name__ == "__main__":
    parser = ArgumentParser(description="测试TaskSpider")

    parser.add_argument("--start", type=int, nargs=1, help="用mysql做种子表 (1|2）", function=start)
    parser.add_argument("--start2", type=int, nargs=1, help="用redis做种子表 (1|2）", function=start2)

    parser.start()

    # 下发任务  python3 test_task_spider.py --start 1
    # 采集  python3 test_task_spider.py --start 2
```

## 3. 代码讲解

#### 3.1 main

main函数为命令行参数解析，分别定义了两种获取任务的方式。start函数为从mysql里获取任务，前提是需要有任务表。start2函数为从redis里获取任务，指定了根任务的key为`spider_task2`，key的类型为zset

启动：TaskSpider分为master及work两种程序

1. master负责下发任务，监控批次进度，创建批次等功能，启动方式：

        spider.start_monitor_task()

2. worker负责消费任务，抓取数据，启动方式：

        spider.start()

#### 3.1 add_task: 

框架内置的函数，在调用start_monitor_task时会自动调度此函数，用于初始化任务种子，若不需要，可直接删除此函数

本代码示例为向redis的`spider_task2`的key加了个值为`{"id": 1, "url": "https://www.baidu.com"}`的种子




