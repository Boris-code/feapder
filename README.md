# FEAPDER

![](https://img.shields.io/badge/python-3.6-brightgreen)
![](https://img.shields.io/github/watchers/Boris-code/feapder?style=social)
![](https://img.shields.io/github/stars/Boris-code/feapder?style=social)
![](https://img.shields.io/github/forks/Boris-code/feapder?style=social)

## 简介

**feapder** 是一款上手简单，功能强大的Python爬虫框架，使用方式类似scrapy，方便由scrapy框架切换过来，框架内置3种爬虫：

- `AirSpider`爬虫比较轻量，学习成本低。面对一些数据量较少，无需断点续爬，无需分布式采集的需求，可采用此爬虫。

- `Spider`是一款基于redis的分布式爬虫，适用于海量数据采集，支持断点续爬、爬虫报警、数据自动入库等功能

- `BatchSpider`是一款分布式批次爬虫，对于需要周期性采集的数据，优先考虑使用本爬虫。

**feapder**除了支持**断点续爬**、**数据防丢**、**监控报警**外，还支持**浏览器渲染下载**，自定义入库**pipeline**，方便对接其他数据库（默认数据库为msyql，数据可自动入库，无需编写pipeline）

读音: `[ˈfiːpdə]`

- 官方文档：http://boris.org.cn/feapder/
- github：https://github.com/Boris-code/feapder
- 更新日志：https://github.com/Boris-code/feapder/releases


## 环境要求：

- Python 3.6.0+
- Works on Linux, Windows, macOS

## 安装

From PyPi:

通用版

```shell
pip3 install feapder
```    

完整版：

```shell
pip3 install feapder[all]
``` 

通用版与完整版区别：

1. 完整版支持基于内存去重

完整版可能会安装出错，若安装出错，请参考[安装问题](https://boris.org.cn/feapder/#/question/%E5%AE%89%E8%A3%85%E9%97%AE%E9%A2%98)

## 小试一下

创建爬虫

```shell
feapder create -s first_spider
```

创建后的爬虫代码如下：

```python

import feapder


class FirstSpider(feapder.AirSpider):
    def start_requests(self):
        yield feapder.Request("https://www.baidu.com")

    def parse(self, request, response):
        print(response)


if __name__ == "__main__":
    FirstSpider().start()
        
```

直接运行，打印如下：

```shell
Thread-2|2021-02-09 14:55:11,373|request.py|get_response|line:283|DEBUG|
                -------------- FirstSpider.parse request for ----------------
                url  = https://www.baidu.com
                method = GET
                body = {'timeout': 22, 'stream': True, 'verify': False, 'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36'}}

<Response [200]>
Thread-2|2021-02-09 14:55:11,610|parser_control.py|run|line:415|DEBUG| parser 等待任务 ...
FirstSpider|2021-02-09 14:55:14,620|air_spider.py|run|line:80|INFO| 无任务，爬虫结束
```

代码解释如下：

1. start_requests： 生产任务
2. parse： 解析数据

## 相关文章

[使用feapder开发爬虫是一种怎样的体验
](https://mp.weixin.qq.com/s/WfClSbsjrn_4aPyI5hsalg)

[爬虫 | 如何快速的将请求头转为json格式](https://mp.weixin.qq.com/s/BgAGo7HwlHxL8jDL5TSuHQ)



## 学习交流

知识星球：

![知识星球](http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/02/16/zhi-shi-xing-qiu.jpeg)

星球会不定时分享爬虫技术干货，涉及的领域包括但不限于js逆向技巧、爬虫框架刨析、爬虫技术分享等

## 赞赏

搞个**微信**赞赏码，不知道屏幕前的你愿不愿意请我喝杯咖啡，让我激动激动🥺

![赞赏码](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/03/16/zan-shang-ma.png)
