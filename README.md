# FEAPDER

![](https://img.shields.io/badge/python-3.6-brightgreen) 

## 简介

**feapder** 是一款简单、快速、轻量级的爬虫框架。起名源于 fast、easy、air、pro、spider的缩写，以开发快速、抓取快速、使用简单、功能强大为宗旨，历时4年倾心打造。支持轻量爬虫、分布式爬虫、批次爬虫、爬虫集成，以及完善的爬虫报警机制。

之前一直在公司内部使用，已使用本框架采集100+数据源，日采千万数据。现在开源，供大家学习交流！

读音: `[ˈfiːpdə]`

官方文档：http://boris.org.cn/feapder/


![](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/02/22/16139928869250.jpg?x-oss-process=style/markdown-media)


## 环境要求：

- Python 3.6.0+
- Works on Linux, Windows, macOS

## 安装

From PyPi:

    pip3 install feapder

From Git:

    pip3 install git+https://github.com/Boris-code/feapder.git

若安装出错，请参考[安装问题](https://boris.org.cn/feapder/#/question/%E5%AE%89%E8%A3%85%E9%97%AE%E9%A2%98)

## 小试一下

创建爬虫

    feapder create -s first_spider

创建后的爬虫代码如下：


    import feapder


    class FirstSpider(feapder.AirSpider):
        def start_requests(self):
            yield feapder.Request("https://www.baidu.com")

        def parser(self, request, response):
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

## 功能概览

### 1. 支持周期性采集

周期性抓取是爬虫中常见的需求，如每日抓取一次商品的销量等，我们把每个周期称为一个批次。

本框架支持批次采集，引入了批次表的概念，详细记录了每一批次的抓取状态

![-w899](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/12/20/16084680404224.jpg?x-oss-process=style/markdown-media)

### 2. 支持分布式采集

面对海量的数据，分布式采集必不可少的，本框架支持分布式，且可随时重启爬虫，任务不丢失

### 3. 支持爬虫集成

本功能可以将多个爬虫以插件的形式集成为一个爬虫，常用于采集周期一致，需求一致的，但需要采集多个数据源的项目

### 4. 支持海量数据去重

框架内置3种去重机制，通过简单的配置可对任务及数据自动去重，也可拿出来单独作为模块使用，支持批量去重。

1. 临时去重：处理一万条数据约0.26秒。 去重1亿条数据占用内存约1.43G，可指定去重的失效周期
2. 内存去重：处理一万条数据约0.5秒。 去重一亿条数据占用内存约285MB
3. 永久去重：处理一万条数据约3.5秒。去重一亿条数据占用内存约285MB

### 5. 数据自动入库

只需要根据数据库表自动生成item，然后给item属性赋值，直接yield 返回即可批量入库

### 6. 支持Debug模式

爬虫支持debug模式，debug模式下默认数据不入库、不修改任务状态。可针对某个任务进行调试，方便开发

### 7. 完善的报警机制

为了保证数据的全量性、准确性、时效性，本框架内置报警机制，有了这些报警，我们可以实时掌握爬虫状态

1. 实时计算爬虫抓取速度，估算剩余时间，在指定的抓取周期内预判是否会超时

    ![-w657](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/12/20/16084718683378.jpg?x-oss-process=style/markdown-media)


2. 爬虫卡死报警

    ![-w501](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/12/20/16084718974597.jpg?x-oss-process=style/markdown-media)

3. 爬虫任务失败数过多报警，可能是由于网站模板改动或封堵导致

    ![-w416](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/12/29/16092335882158.jpg?x-oss-process=style/markdown-media)

### 8. 下载监控

框架对请求总数、成功数、失败数、解析异常数进行监控，将数据点打入到infuxdb，结合Grafana面板，可方便掌握抓取情况

![-w1299](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/02/09/16128568548280.jpg?x-oss-process=style/markdown-media)



## 学习交流

官方文档：http://boris.org.cn/feapder/

知识星球：

![知识星球](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/02/16/zhi-shi-xing-qiu.jpeg)

星球会不定时分享爬虫技术干货，涉及的领域包括但不限于js逆向技巧、爬虫框架刨析、爬虫技术分享等