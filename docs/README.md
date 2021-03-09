# FEAPDER

![](https://img.shields.io/badge/python-3.6-brightgreen)

## 简介

**feapder** 是一款简单、快速、轻量级的爬虫框架。起名源于 fast、easy、air、pro、spider的缩写，以开发快速、抓取快速、使用简单、功能强大为宗旨，历时4年倾心打造。支持轻量爬虫、分布式爬虫、批次爬虫、爬虫集成，以及完善的爬虫报警机制。

之前一直在公司内部使用，已使用本框架采集100+数据源，日采千万数据。现在开源，供大家学习交流！

读音: `[ˈfiːpdə]`

官方文档：http://boris.org.cn/feapder/


## 环境要求：

- Python 3.6.0+
- Works on Linux, Windows, macOS

## 安装

From PyPi:

    pip3 install feapder

From Git:

    pip3 install git+https://github.com/Boris-code/feapder.git

若安装出错，请参考[安装问题](question/安装问题.md)

## 小试一下

创建爬虫

    feapder create -s first_spider

创建后的爬虫代码如下：


    import feapder


    class FirstSpider(feapder.AirSpider):
        def start_requests(self):
            yield feapder.Request("https://www.baidu.com")

        def parse(self, request, response):
            print(response)


    if __name__ == "__main__":
        FirstSpider().start()

直接运行，打印如下：

    Thread-2|2021-02-09 14:55:11,373|request.py|get_response|line:283|DEBUG|
                    -------------- FirstSpider.parser request for ----------------
                    url  = https://www.baidu.com
                    method = GET
                    body = {'timeout': 22, 'stream': True, 'verify': False, 'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36'}}

    <Response [200]>
    Thread-2|2021-02-09 14:55:11,610|parser_control.py|run|line:415|INFO| parser 等待任务 ...
    FirstSpider|2021-02-09 14:55:14,620|air_spider.py|run|line:80|DEBUG| 无任务，爬虫结束

代码解释如下：

1. start_requests： 生产任务
2. parser： 解析数据

## 为什么不使用scrapy

**scrapy**给我的印象：

1. **重**：框架中的许多东西都用不到，如CrawlSpider、XMLFeedSpider
2. 中间件不灵活
3. 从数据库中取任务作为种子抓取不支持，需要自己写代码取任务，维护任务状态
4. 数据入库不支持批量，需要自己写批量逻辑
5. 启动方式需要用scrapy命令行，打断点调试不方便
6. 英文文档，阅读理解起来费精力

**feapder** 正是迎着以上痛点而生的，以数据库中取任务作为种子为例，写法如下：

```
import feapder
from items import *


class TestSpider(feapder.BatchSpider):

    def start_requests(self, task):
        # task 为在任务表中取出的每一条任务
        id, url = task  # id， url为所取的字段，main函数中指定的
        yield feapder.Request(url, task_id=id)

    def parse(self, request, response):
        title = response.xpath('//title/text()').extract_first()  # 取标题
        item = spider_data_item.SpiderDataItem()  # 声明一个item
        item.title = title  # 给item属性赋值
        yield item  # 返回item， item会自动批量入库
        yield self.update_task_batch(request.task_id, 1) # 更新任务状态为1
        
if __name__ == "__main__":
    spider = TestSpider(
        redis_key="feapder:test_batch_spider",  # redis中存放任务等信息的根key
        task_table="batch_spider_task",  # mysql中的任务表
        task_keys=["id", "url"],  # 需要获取任务表里的字段名，可添加多个
        task_state="state",  # mysql中任务状态字段
        batch_record_table="batch_spider_batch_record",  # mysql中的批次记录表
        batch_name="批次爬虫测试(周全)",  # 批次名字
        batch_interval=7,  # 批次周期 天为单位 若为小时 可写 1 / 24。 这里为每一天一个批次
    )


    spider.start_monitor_task()  # 下发及监控任务
    # spider.start()  # 采集        
```

任务表：`batch_spider_task`
![-w398](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/02/22/16139773315622.jpg?x-oss-process=style/markdown-media)

批次记录表记录着每个批次的抓取状态，自动生成
![-w899](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/12/20/16084680404224.jpg?x-oss-process=style/markdown-media)

feapder会自动维护任务状态，每个批次（采集周期）的进度，并且内置丰富的报警，保证我们的数据时效性，如：

1. 实时计算爬虫抓取速度，估算剩余时间，在指定的抓取周期内预判是否会超时

    ![-w657](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/12/20/16084718683378.jpg?x-oss-process=style/markdown-media)


2. 爬虫卡死报警

    ![-w501](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/12/20/16084718974597.jpg?x-oss-process=style/markdown-media)

3. 爬虫任务失败数过多报警，可能是由于网站模板改动或封堵导致

    ![-w416](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/12/29/16092335882158.jpg?x-oss-process=style/markdown-media)


## 学习交流


知识星球：

![知识星球](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/02/16/zhi-shi-xing-qiu.jpeg)

星球会不定时分享爬虫技术干货，涉及的领域包括但不限于js逆向技巧、爬虫框架刨析、爬虫技术分享等