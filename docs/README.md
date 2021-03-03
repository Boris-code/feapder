# FEAPDER

![](https://img.shields.io/badge/python-3.6-brightgreen)
[![Gitter](https://badges.gitter.im/feapder/community.svg)](https://gitter.im/feapder/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

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


## 学习交流


知识星球：

![知识星球](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/02/16/zhi-shi-xing-qiu.jpeg)

星球会不定时分享爬虫技术干货，涉及的领域包括但不限于js逆向技巧、爬虫框架刨析、爬虫技术分享等