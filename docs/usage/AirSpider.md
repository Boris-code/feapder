# AirSpider

AirSpider是一款轻量爬虫框架，学习成本低。面对一些数据量较少，无需断点续爬，无需分布式采集的需求，可采用此爬虫。

## 1. 创建爬虫

    feapder create -s spider_test
    
生成如下

    
    import feapder
    
    
    class SpiderTest(feapder.AirSpider):
        def start_requests(self):
            yield feapder.Request("https://www.baidu.com")
        
        def parser(self, request, response):
            print(response)
    
    
    if __name__ == "__main__":
        SpiderTest().start()
    
    
可直接运行

## 2. 代码讲解

默认生成的代码继承了feapder.AirSpider，包含 `start_requests` 及 `parser` 两个函数，含义如下：

1. feapder.AirSpider：轻量爬虫基类
2. start_requests：初始任务下发入口
3. feapder.Request：基于requests库类似，表示一个请求，支持requests所有参数，同时也可携带些自定义的参数，详情可参考[Request](source_code/Request.md)
4. parser：数据解析函数
5. response：请求响应的返回体，支持xpath、re、css等解析方式，详情可参考[Response](source_code/Response.md)

除了start_requests、parser两个函数。系统还内置了下载中间件等函数，具体支持可参考[BaseParse](source_code/BaseParse.md)

## 3. 自定义解析函数

开发过程中解析函数往往不止有一个，除了系统默认的parser外，还支持自定义解析函数，写法如下

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com", callback=self.parser_xxx)

    def parser_xxx(self, request, response):
        print(response)

即feapder.Request支持指定callback函数，不指定时默认回调parser

## 4. 携带参数

有时我们需要把前面请求到的数据携带到下一级，写法如下

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com",  xxx="我是携带的数据")

    def parser(self, request, response):
        xxx = request.xxx
        print(xxx)
        
直接在feapder.Request中携带即可，xxx为携带数据的key，可以随意写，只要不和feapder.Request默认参数冲突即可。默认参数参考[Request](source_code/Request.md)。可以携带任意类型的值，如字典、类等

取值：如何携带就如何取值，如上我们携带xxx， 那么`request.xxx` 可将xxx值取出，取出的值和携带的值类型一致。

## 5. 下发新任务

parser中支持下发新任务，写法与start_requests一致，只需要`yield feapder.Request`即可。示例如下：

    def parser(self, request, response):
        yield feapder.Request("url1") # 不指定callback，任务会调度默认的parser上
        yield feapder.Request("url2", callback=self.parser_detail) # 指定了callback，任务由callback指定的函数解析

## 6. 下载中间件

下载中间件用于在请求之前，对请求做一些处理，如添加cookie、header等。写法如下：


    def download_midware(self, request):
        request.headers = {'User-Agent':"lalala"}
        return request

request.参数， 这里的参数支持requests所有参数，同时也可携带些自定义的参数，详情可参考[Request](source_code/Request.md)

默认所有的解析函数在请求之前都会经过此下载中间件

## 7. 自定义下载中间件

与自定义解析函数类型，下载中间件也支持自定义，只需要在feapder.Request参数里指定个`download_midware`回调即可，写法如下：

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com", download_midware=self.xxx)

    def xxx(self, request):
        """
        我是自定义的下载中间件
        :param request: 
        :return: 
        """
        request.headers = {'User-Agent':"lalala"}
        return request
        
自定义的下载中间件只有指定的请求才会经过。其他未指定下载中间件的请求，还是会经过默认的下载中间件

## 8. 失败重试

框架支持重试机制，下载失败、解析函数抛出异常会自动重试。

如下，校验了返回的code是否为200，非200抛出异常，触发重试

    def parser(self, request, response):
        if response.code != 200:
            raise Exception("非法页面")
            
默认最大重试次数为100次，我们可以引入配置文件或自定义配置来修改重试次数，详情参考[配置文件](source_code/配置文件.md)

## 9. 加快采集速度

默认爬虫为1线程，我们可通过修改线程数来加快采集速度。除了在配置文件中修改外，可以在启动函数中传递线程数


    if __name__ == "__main__":
        SpiderTest(thread_count=10).start()
        
        
## 10. 爬虫配置

爬虫配置支持自定义配置或引入配置文件的方式。

自定义配置，使用类变量`__custom_setting__`：

    class SpiderTest(feapder.AirSpider):
        __custom_setting__ = dict(
            PROXY_EXTRACT_API="代理提取地址",
        )
        
上例是配置代理提取地址，以便爬虫使用代理。还支持更丰富的配置信息，具体参考[配置文件](source_code/配置文件.md)。不过AirSpider不支持去重，因此配置文件中的去重配置无效