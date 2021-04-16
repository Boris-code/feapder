
# BaseParser

BaseParser为Spider的基类，用来定义任务下发与数据解析，是面向用户提供的接口

## 源码


```python
class BaseParser(object):
    def start_requests(self):
        """
        @summary: 添加初始url
        ---------
        ---------
        @result: yield Request()
        """

        pass

    def download_midware(self, request):
        """
        @summary: 下载中间件 可修改请求的一些参数
        ---------
        @param request:
        ---------
        @result: return request / None (不会修改原来的request)
        """

        pass

    def validate(self, request, response):
        """
        @summary: 校验函数, 可用于校验response是否正确
        若函数内抛出异常，则重试请求
        若返回True 或 None，则进入解析函数
        若返回False，则抛弃当前请求
        可通过request.callback_name 区分不同的回调函数，编写不同的校验逻辑
        ---------
        @param request:
        @param response:
        ---------
        @result: True / None / False
        """

        pass

    def parse(self, request, response):
        """
        @summary: 默认的解析函数
        ---------
        @param request:
        @param response:
        ---------
        @result:
        """

        pass

    def exception_request(self, request, response):
        """
        @summary: 请求或者parser里解析出异常的request
        ---------
        @param request:
        @param response:
        ---------
        @result: request / callback / None (返回值必须可迭代)
        """

        pass

    def failed_request(self, request, response):
        """
        @summary: 超过最大重试次数的request
        可返回修改后的request  若不返回request，则将传进来的request直接人redis的failed表。否则将修改后的request入failed表
        ---------
        @param request:
        ---------
        @result: request / item / callback / None (返回值必须可迭代)
        """

        pass

    def start_callback(self):
        """
        @summary: 程序开始的回调
        ---------
        ---------
        @result: None
        """

        pass

    def end_callback(self):
        """
        @summary: 程序结束的回调
        ---------
        ---------
        @result: None
        """

        pass

    @property
    def name(self):
        return self.__class__.__name__

    def close(self):
        pass
```

## 使用

以程序开始结束回调举例：

```python
import feapder


class TestSpider(feapder.Spider):
    def start_callback(self):
        print("爬虫开始了")

    def end_callback(self):
        print("爬虫结束了")
```