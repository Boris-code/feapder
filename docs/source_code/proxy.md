# 代理使用说明

代理使用有三种方式
1. 使用框架内置代理池
2. 自定义代理池
3. 请求中直接指定

## 方式1. 使用框架内置代理池

### 配置代理

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

## 管理代理

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
    
## 方式2. 自定义代理池

1. 编写代理池：例如在你的项目下创建个my_proxypool.py，实现下面的函数
    
    ```python
    from feapder.network.proxy_pool import BaseProxyPool 
        
    class MyProxyPool(BaseProxyPool):
        def get_proxy(self):
            """
            获取代理
            Returns:
                {"http": "xxx", "https": "xxx"}
            """
            pass
        
        def del_proxy(self, proxy):
            """
            @summary: 删除代理
            ---------
            @param proxy: xxx
            """
            pass
    ```

3. 修改setting的代理配置

    ```
    PROXY_POOL = "my_proxypool.MyProxyPool"  # 代理池
    ```
    
    将编写好的代理池配置进来，值为类的模块路径，需要指定到具体的类名
 


## 方式3. 不使用代理池，直接给请求指定代理

直接给request.proxies赋值即可，例如在下载中间件里使用

```python
import feapder

class TestProxy(feapder.AirSpider):
    def start_requests(self):
        yield feapder.Request("https://www.baidu.com")
        
    def download_midware(self, request):
        # 这里使用代理使用即可
        request.proxies = {"https": "https://ip:port", "http": "http://ip:port"} 
        return request

    def parse(self, request, response):
        print(response)
```