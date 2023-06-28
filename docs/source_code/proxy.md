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
PROXY_MAX_FAILED_TIMES = 5  # 代理最大失败次数，超过则不使用，自动删除
```

要求API返回的代理格式为使用 /r/n 分隔：

```
ip:port
ip:port
ip:port
```

这样feapder在请求时会自动随机使用上面的代理请求了

### 高阶

1. 删除代理（默认是请求异常连续5次，再删除代理）

    例如在发生异常时删除代理
    
    ```python
    import feapder
    class TestProxy(feapder.AirSpider):
        def start_requests(self):
            yield feapder.Request("https://www.baidu.com")
        
        def parse(self, request, response):
            print(response)
        
        def exception_request(self, request, response):
            request.del_proxy()
            
    ```

## 2. 自己写

自己写就比较灵活，自己随机取个代理，然后给request赋值即可，例如在下载中间件里使用

```python
import feapder

class TestProxy(feapder.AirSpider):
    def start_requests(self):
        yield feapder.Request("https://www.baidu.com")
        
    def download_midware(self, request):
        # 这里随机取个代理使用即可
        request.proxies = {"https": "https://ip:port", "http": "http://ip:port"} 
        return request

    def parse(self, request, response):
        print(response)
```