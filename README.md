# FEAPDER

![](https://img.shields.io/badge/python-3.6-brightgreen)
![](https://img.shields.io/github/watchers/Boris-code/feapder?style=social)
![](https://img.shields.io/github/stars/Boris-code/feapder?style=social)
![](https://img.shields.io/github/forks/Boris-code/feapder?style=social)
[![Downloads](https://pepy.tech/badge/feapder)](https://pepy.tech/project/feapder)
[![Downloads](https://pepy.tech/badge/feapder/month)](https://pepy.tech/project/feapder)
[![Downloads](https://pepy.tech/badge/feapder/week)](https://pepy.tech/project/feapder)

## 简介

**feapder是一款上手简单，功能强大的Python爬虫框架**

读音: `[ˈfiːpdə]`

![Feapder](https://tva1.sinaimg.cn/large/008vxvgGly1h8byrr75xnj30u02f7k0j.jpg)

## 文档地址

- 官方文档：https://feapder.com
- github：https://github.com/Boris-code/feapder
- 更新日志：https://github.com/Boris-code/feapder/releases
- 爬虫管理系统：http://feapder.com/#/feapder_platform/feaplat


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

完整版可能会安装出错，若安装出错，请参考[安装问题](question/安装问题)

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
Thread-2|2021-02-09 14:55:11,610|parser_control.py|run|line:415|DEBUG| parser 等待任务...
FirstSpider|2021-02-09 14:55:14,620|air_spider.py|run|line:80|INFO| 无任务，爬虫结束
```

代码解释如下：

1. start_requests： 生产任务
2. parse： 解析数据

## 爬虫工具推荐

1. 爬虫在线工具库：http://www.spidertools.cn
2. 爬虫管理系统：http://feapder.com/#/feapder_platform/feaplat
3. 验证码识别库：https://github.com/sml2h3/ddddocr


## 微信赞赏

如果您觉得这个项目帮助到了您，您可以帮作者买一杯咖啡表示鼓励 🍹

也可和作者交个朋友，解决您在使用过程中遇到的问题


![赞赏码](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/03/16/zan-shang-ma.png)

## 学习交流

<table border="0"> 
    <tr> 
     <td> 知识星球：17321694 </td> 
     <td> 作者微信： boris_tm </td> 
     <td> QQ群号：485067374 </td> 
    </tr> 
    <tr> 
    <td> <img src="http://markdown-media.oss-cn-beijing.aliyuncs.com/2020/02/16/zhi-shi-xing-qiu.jpeg" width=250px>
 </td> 
     <td> <img src="http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/07/12/er-wei-ma.jpeg?x-oss-process=style/markdown-media" width="250px" /> </td> 
     <td> <img src="https://tva1.sinaimg.cn/large/008vxvgGly1h8byl060lnj30ku11c76h.jpg" width="250px" /> </td> 
    </tr> 
  </table> 



  加好友备注：feapder