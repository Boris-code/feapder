# 代理使用说明

代理使用有两种方式
1. 用框架内置的代理池
2. 自己写

## 1. 框架内置的代理池

### 基本使用

在配置文件中配置代理提取接口

```python
# 设置代理
PROXY_EXTRACT_API = None  # 代理提取API ，返回的代理分割符为\r\n
PROXY_ENABLE = True
```

要求API返回的代理格式为：

```
ip:port
ip:port
ip:port
```

这样feapder在请求时会自动随机使用上面的代理请求了

### 高阶

> 注意：高阶用法现在不太友好，后期会调整使用方式

1. 标记代理失效或延时使用

    例如在发生异常时处理代理
    
    ```python
    import feapder
    class TestProxy(feapder.AirSpider):
        def start_requests(self):
            yield feapder.Request("https://www.baidu.com")
        
        def parse(self, request, response):
            print(response)
        
        def exception_request(self, request, response):
    
            # request.proxies_pool.tag_proxy(request.requests_kwargs.get("proxies"), -1)  # 废弃本次代理
            request.proxies_pool.tag_proxy(request.requests_kwargs.get("proxies"), 1, 30)  # 延迟本次代理30秒后再使用
    ```

1. 指定代理拉取时间间隔等

    在代码头部给feapder.Request.proxies_pool重新赋值

    ```python
    import feapder
    from feapder.network.proxy_pool import ProxyPool
    
    proxy_pool= ProxyPool(reset_interval_max=180, reset_interval=5)
    feapder.Request.proxies_pool = proxy_pool
    ```
    
    相当于修改了代理池的默认参数值，更多参数看源码

1. 从redis里提取代理
    
    ```python
    import feapder
    from feapder.network.proxy_pool import ProxyPool
    
    proxy_pool = ProxyPool(
        proxy_source_url="redis://:passwd@host:ip/db", redis_proxies_key="proxies"
    )
    feapder.Request.proxies_pool = proxy_pool
    ```
    
    要求redis使用zset集合存储代理，存储内容示例如下：
    ```
    ip:port
    ip:port
    ip:port
    ```
    
    redis_proxies_key及为存储代理的key，每次拉取时会拉取全量

## 2. 自己写

自己写就比较灵活，自己随机取个代理，然后给request赋值即可，例如在下载中间件里使用

```python
import feapder

class TestProxy(feapder.AirSpider):
    def start_requests(self):
        yield feapder.Request("https://www.baidu.com")
        
    def download_midware(self, request):
        # 这里随机取个代理使用即可,
        #proxies 是requests的参数,需要通过request.requests_kwargs传递
        request.requests_kwargs = {}
        request.requests_kwargs['proxies'] = {"https": "https://ip:port", "http": "http://ip:port"}
        return request

    def parse(self, request, response):
        print(response)
```