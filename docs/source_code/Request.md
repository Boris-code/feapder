# Request

## 简介

Request为feapder的下载器，基于requests进行了封装，因此支持requests的所有参数

我们可以直接调用框架中的Request发起请求，使用示例：

```
from feapder import Request

request = Request("https://www.baidu.com", data={}, params=None)
response = request.get_response()
print(response)
```

返回的response支持xpath、css等表达式，具体用法见[Response](source_code/Response)

Request除了支持requests的所有参数外，更需要关心的是框架中支持的参数

## 参数详解

```python
@summary: Request参数
---------
框架参数
@param url: 待抓取url
@param retry_times: 当前重试次数
@param priority: 请求优先级 越小越优先 默认300
@param parser_name: 回调函数所在的类名 默认为当前类
@param callback: 回调函数 可以是函数 也可是函数名（如想跨类回调时，parser_name指定那个类名，callback指定那个类想回调的方法名即可）
@param filter_repeat: 是否需要去重 (True/False) 当setting中的REQUEST_FILTER_ENABLE设置为True时该参数生效 默认True
@param auto_request: 是否需要自动请求下载网页 默认是。设置为False时返回的response为空，需要自己去请求网页
@param request_sync: 是否同步请求下载网页，默认异步。如果该请求url过期时间快，可设置为True，相当于yield的reqeust会立即响应，而不是去排队
@param use_session: 是否使用session方式
@param random_user_agent: 是否随机User-Agent (True/False) 当setting中的RANDOM_HEADERS设置为True时该参数生效 默认True
@param download_midware: 下载中间件。默认为parser中的download_midware
@param is_abandoned: 当发生异常时是否放弃重试 True/False. 默认False
--
以下参数于requests参数使用方式一致
@param method: 请求方式，如POST或GET，默认根据data值是否为空来判断
@param params: 请求参数
@param data: 请求body
@param json: 请求json字符串，同 json.dumps(data)
@param headers:
@param cookies: 字典 或 CookieJar 对象
@param files: 
@param auth: 
@param timeout: (浮点或元组)等待服务器数据的超时限制，是一个浮点数，或是一个(connect timeout, read timeout) 元组
@param allow_redirects : Boolean. True 表示允许跟踪 POST/PUT/DELETE 方法的重定向
@param proxies: 代理 {"http":"http://xxx", "https":"https://xxx"}
@param verify: 为 True 时将会验证 SSL 证书
@param stream: 如果为 False，将会立即下载响应内容
@param cert: 
--
@param **kwargs: 其他值: 如 Request(item=item) 则item可直接用 request.item 取出
---------
```

举例说明：如果我们不想用内置的下载器，写法如下：

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com", auto_request=False)

    def parse(self, request, response):
        # response 为None， 需要自己去下载
        pass
        
        
## 方法详解

### 1. 发起请求，获取响应

```
def get_response(self, save_cached=False):
    """
    获取带有selector功能的response
    @param save_cached: 保存缓存 方便调试时不用每次都重新下载
    @return:
    """
```

save_cached 参数用于设置是否把响应缓存到redis，若为True, 需要配置redis连接信息。redis连接信息会读取setting.py文件，所以需要保证工作区间下有setting.py。

或者可以将连接信息设置为环境变量
以mac电脑为例

```
> vim ~/.bash_profile

export REDISDB_IP_PORTS='ip:port' # 多个地址用逗号隔开
export REDISDB_USER_PASS='xxx'
export REDISDB_DB='xxx' # 默认是0, 可不设置
export REDISDB_SERVICE_NAME='xxx' # 用于redis的哨兵模式，单节点或集群模式可不设置

```

这样，当框架读取不到setting时，便会取环境变量里的值

### 2. 从缓存中取响应

```
def get_response_from_cached(self, save_cached=True):
    pass
```

用于从上面的缓存中取response。当缓存不存在时，会先下载，然后将响应存入缓存，之后再返回响应。缓存同样依赖redis，因此需要先配置好redis连接信息

### 3. 删除缓存

```
def del_response_cached(self)
    pass
```

### 4. 复制Request

```
def copy(self):
    pass
```

## 缓存机制

### 1. 缓存有效期

缓存使用redis的str结构存储，每条缓存对应一个key，默认有效期20分钟，可以通过 `Request.cached_expire_time=过期时间`来设置

### 2. 缓存key

默认的key为 `response_cached:test:request指纹`

可通过`Request.cached_redis_key`设置，设置后为 `response_cached:自定义的key:request指纹`

## 代理及UserAgent

 代理及UA的设置优先取传递的参数，若参数没指定，则依赖`setting.py`的配置，默认如下：

```python
# 设置代理
PROXY_EXTRACT_API = None  # 代理提取API ，返回的代理分割符为\r\n
PROXY_ENABLE = True

# 随机headers
RANDOM_HEADERS = True
# requests 使用session
USE_SESSION = False
```

PROXY_EXTRACT_API 为代理的提取地址，如

```python
PROXY_EXTRACT_API="http://xxxx"
```

返回的代理格式为：

```
ip:port
ip:port
ip:port
```
