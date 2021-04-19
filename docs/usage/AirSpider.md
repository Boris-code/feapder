# AirSpider

AirSpider是一款轻量爬虫，学习成本低。面对一些数据量较少，无需断点续爬，无需分布式采集的需求，可采用此爬虫。

## 1. 创建爬虫

命令参考：[命令行工具](command/cmdline.md?id=_2-创建爬虫)

示例

    feapder create -s air_spider_test

生成如下


    import feapder


    class AirSpiderTest(feapder.AirSpider):
        def start_requests(self):
            yield feapder.Request("https://www.baidu.com")

        def parse(self, request, response):
            print(response)


    if __name__ == "__main__":
        AirSpiderTest().start()


可直接运行

## 2. 代码讲解

默认生成的代码继承了feapder.AirSpider，包含 `start_requests` 及 `parser` 两个函数，含义如下：

1. feapder.AirSpider：轻量爬虫基类
2. start_requests：初始任务下发入口
3. feapder.Request：基于requests库类似，表示一个请求，支持requests所有参数，同时也可携带些自定义的参数，详情可参考[Request](source_code/Request.md)
4. parser：数据解析函数
5. response：请求响应的返回体，支持xpath、re、css等解析方式，详情可参考[Response](source_code/Response.md)

除了start_requests、parser两个函数。系统还内置了下载中间件等函数，具体支持可参考[BaseParser](source_code/BaseParser.md)

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

    def parse(self, request, response):
        xxx = request.xxx
        print(xxx)

直接在feapder.Request中携带即可，xxx为携带数据的key，可以随意写，只要不和feapder.Request默认参数冲突即可。默认参数参考[Request](source_code/Request.md)。可以携带任意类型的值，如字典、类等

取值：如何携带就如何取值，如上我们携带xxx， 那么`request.xxx` 可将xxx值取出，取出的值和携带的值类型一致。

## 5. 下发新任务

parser中支持下发新任务，写法与start_requests一致，只需要`yield feapder.Request`即可。示例如下：

    def parse(self, request, response):
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

与自定义解析函数类似，下载中间件也支持自定义，只需要在feapder.Request参数里指定个`download_midware`回调即可，写法如下：

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

## 8. 校验

```python
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
```

例如：

```python
def validate(self, request, response):
    if response.status_code != 200:
        raise Exception("response code not 200") # 重试

    # if "哈哈" not in response.text:
    #     return False # 抛弃当前请求
```

## 9. 失败重试

框架支持重试机制，下载失败或解析函数抛出异常会自动重试请求。

例如下面代码，校验了返回的code是否为200，非200抛出异常，触发重试

    def parse(self, request, response):
        if response.status_code != 200:
            raise Exception("非法页面")

默认最大重试次数为100次，我们可以引入配置文件或自定义配置来修改重试次数，详情参考[配置文件](source_code/配置文件.md)


## 10. 爬虫配置

爬虫配置支持自定义配置或引入配置文件`setting.py`的方式。

配置文件：在工作区间的根目录下引入`setting.py`，具体参考[配置文件](source_code/配置文件.md)

![-w261](http://markdown-media.oss-cn-beijing.aliyuncs.com/2021/02/21/16138971894815.jpg)


自定义配置：
使用类变量`__custom_setting__`：

    class AirSpiderTest(feapder.AirSpider):
        __custom_setting__ = dict(
            PROXY_EXTRACT_API="代理提取地址",
        )

上例是配置代理提取地址，以便爬虫使用代理，自定义配置支持配置文件中的所有参数。

配置优先级： 自定义配置 > 配置文件，即自定义配置会覆盖配置文件里的配置信息，不过自定义配置只对自己有效，配置文件可以是多个爬虫公用的

AirSpider不支持去重，因此配置文件中的去重配置无效

## 11. 加快采集速度

默认爬虫为1线程，我们可通过修改线程数来加快采集速度。除了在配置文件中修改或使用自定义配置外，可以在启动函数中传递线程数


    if __name__ == "__main__":
        AirSpiderTest(thread_count=10).start()

## 12. 数据入库

框架内封装了`MysqlDB`、`RedisDB`，与pymysql不同的是，MysqlDB 使用了线程池，且对方法进行了封装，使用起来更方便。RedisDB 支持 哨兵模式、集群模式。使用方法如下：

导入

    from feapder.db.mysqldb import MysqlDB
    from feapder.db.redisdb import RedisDB

以mysql为例，获取mysql对象

方式1：若`setting.py` 或 `__custom_setting__`中指定了数据库连接信息，则可以直接以`db = MysqlDB()`方式获取

    class AirSpiderTest(feapder.AirSpider):
        __custom_setting__ = dict(
            MYSQL_IP="localhost",
            MYSQL_PORT = 3306,
            MYSQL_DB = "feapder",
            MYSQL_USER_NAME = "feapder",
            MYSQL_USER_PASS = "feapder123"

        )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = MysqlDB()

方式2：若没配置文件，则MysqlDB需要传递连接信息

    db = MysqlDB(
            ip="localhost",
            port=3306,
            user_name="feapder",
            user_pass="feapder123",
            db="feapder"
        )

MysqlDB 的具体使用方法见 [MysqlDB](source_code/MysqlDB.md)

RedisDB 的具体使用方法见 [RedisDB](source_code/RedisDB.md)

框架也支持数据自动入库，详见[数据自动入库](usage/Spider?id=_5-数据自动入库)

## 13. 浏览器渲染下载

采集动态页面时（Ajax渲染的页面），常用的有两种方案。一种是找接口拼参数，这种方式比较复杂但效率高，需要一定的爬虫功底；另外一种是采用浏览器渲染的方式，直接获取源码，简单方便

使用方式：
```python
def start_requests(self):
    yield feapder.Request("https://news.qq.com/", render=True)
```
在返回的Request中传递`render=True`即可

框架支持`CHROME`和`PHANTOMJS`两种浏览器渲染，可通过[配置文件](source_code/配置文件)进行配置。相关配置如下：

```python
# 浏览器渲染
WEBDRIVER = dict(
    pool_size=1,  # 浏览器的数量
    load_images=True,  # 是否加载图片
    user_agent=None,  # 字符串 或 无参函数，返回值为user_agent
    proxy=None,  # xxx.xxx.xxx.xxx:xxxx 或 无参函数，返回值为代理地址
    headless=False,  # 是否为无头浏览器
    driver_type="CHROME",  # CHROME 或 PHANTOMJS,
    timeout=30,  # 请求超时时间
    window_size=(1024, 800),  # 窗口大小
    executable_path=None,  # 浏览器路径，默认为默认路径
    render_time=0, # 渲染时长，即打开网页等待指定时间后再获取源码
)
```


## 14. 完整的代码示例

AirSpider：https://github.com/Boris-code/feapder/blob/master/tests/air-spider/test_air_spider.py

浏览器渲染：https://github.com/Boris-code/feapder/blob/master/tests/test_rander.py
