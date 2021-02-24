# FEAPDER

![](https://img.shields.io/badge/python-3.6-brightgreen) 

## 简介

**feapder** 是一款简单、快速、轻量级的爬虫框架。起名源于 fast、easy、air、pro、spider的缩写，以开发快速、抓取快速、使用简单、功能强大为宗旨，历时4年倾心打造。支持分布式爬虫、批次爬虫、多模板爬虫，以及完善的爬虫报警机制。

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

## 功能概览

### 1. 支持周期性采集

周期性抓取是爬虫中常见的需求，如每日抓取一次商品的销量等，我们把每个周期称为一个批次。

这类爬虫，普遍做法是设置个定时任务，每天启动一次。但你有没有想过，若由于某种原因，定时任务启动程序时没启动起来怎么办？比如服务器资源不够了，启动起来直接被kill了。

另外如何保证每条数据在每个批次内都得以更新呢？

本框架支持批次采集，引入了批次表的概念，详细记录了每一批次的抓取状态

![-w899](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/12/20/16084680404224.jpg?x-oss-process=style/markdown-media)

### 2. 支持分布式采集

面对海量的数据，分布式采集必不可少的，本框架支持分布式，且可随时重启爬虫，任务不丢失

### 3. 支持多模板采集

有时我们要采集数十个数据源，采集的结构化信息一致，通常我们会编写数十个爬虫，然后启动数十个窗口去采集，这样我们管理起来比较麻烦。本框架支持将多种数据源（多模板）集成到一个爬虫里来管理，降低维护成本

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