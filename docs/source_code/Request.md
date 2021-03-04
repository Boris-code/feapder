# Request

request为feapder的下载器，基于requests进行了封装，因此支持requests的所有参数

使用示例

```
from feapder import Request

request = Request("https://www.baidu.com", data={}, params=None)
response = request.get_response()
print(response)
```

Request除了支持requests的所有参数外，更需要关心的是框架中支持的参数

## 参数详解

```python
@summary: Request参数
---------
框架参数
@param url: 待抓取url
@param retry_times: 当前重试次数
@param priority: 优先级 越小越优先 默认300
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
@param **kwargs: 其他值: 如 Request(item=item) 则item可直接用 reqeust.item 取出
---------
```