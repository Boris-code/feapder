# 浏览器渲染-Playwright

采集动态页面时（Ajax渲染的页面），常用的有两种方案。一种是找接口拼参数，这种方式比较复杂但效率高，需要一定的爬虫功底；另外一种是采用浏览器渲染的方式，直接获取源码，简单方便

框架支持playwright渲染下载，每个线程持有一个playwright实例


## 使用方式：

1. 修改配置文件的渲染下载器：

    ```
    RENDER_DOWNLOADER="feapder.network.downloader.PlaywrightDownloader"
    ```
2. 使用

    ```python
    def start_requests(self):
        yield feapder.Request("https://news.qq.com/", render=True)
    ```

在返回的Request中传递`render=True`即可

框架支持`chromium`、`firefox`、`webkit` 三种浏览器渲染，可通过[配置文件](source_code/配置文件)进行配置。相关配置如下：

```python
PLAYWRIGHT = dict(
    user_agent=None,  # 字符串 或 无参函数，返回值为user_agent
    proxy=None,  # xxx.xxx.xxx.xxx:xxxx 或 无参函数，返回值为代理地址
    headless=False,  # 是否为无头浏览器
    driver_type="chromium",  # chromium、firefox、webkit
    timeout=30,  # 请求超时时间
    window_size=(1024, 800),  # 窗口大小
    executable_path=None,  # 浏览器路径，默认为默认路径
    download_path=None,  # 下载文件的路径
    render_time=0,  # 渲染时长，即打开网页等待指定时间后再获取源码
    wait_until="networkidle",  # 等待页面加载完成的事件,可选值："commit", "domcontentloaded", "load", "networkidle"
    use_stealth_js=False,  # 使用stealth.min.js隐藏浏览器特征
    page_on_event_callback=None,  # page.on() 事件的回调 如 page_on_event_callback={"dialog": lambda dialog: dialog.accept()}
    storage_state_path=None,  # 保存浏览器状态的路径
    url_regexes=None,  # 拦截接口，支持正则，数组类型
    save_all=False,  # 是否保存所有拦截的接口, 配合url_regexes使用，为False时只保存最后一次拦截的接口
)
```

 - `feapder.Request` 也支持`render_time`参数， 优先级大于配置文件中的`render_time`

 - 代理使用优先级：`feapder.Request`指定的代理 > 配置文件中的`PROXY_EXTRACT_API` > webdriver配置文件中的`proxy`

 - user_agent使用优先级：`feapder.Request`指定的header里的`User-Agent` > 框架随机的`User-Agent` > webdriver配置文件中的`user_agent`

## 设置User-Agent

> 每次生成一个新的浏览器实例时生效

### 方式1：

通过配置文件的 `user_agent` 参数设置

### 方式2：

通过 `feapder.Request`携带，优先级大于配置文件, 如：

```python
def download_midware(self, request):
    request.headers = {
        "User-Agent": "xxxxxxxx"
    }
    return request
```

## 设置代理

> 每次生成一个新的浏览器实例时生效

### 方式1：

通过配置文件的 `proxy` 参数设置

### 方式2：

通过 `feapder.Request`携带，优先级大于配置文件, 如：

```python
def download_midware(self, request):
    request.proxies = {
        "https": "https://xxx.xxx.xxx.xxx:xxxx"
    }
    return request
```
    
## 设置Cookie

通过 `feapder.Request`携带，如：

```python
def download_midware(self, request):
    request.headers = {
        "Cookie": "key=value; key2=value2"
    }
    return request
```

或者

```python
def download_midware(self, request):
    request.cookies = {
        "key": "value",
        "key2": "value2",
    }
    return request
```

或者

```python
def download_midware(self, request):
    request.cookies = [
        {
            "domain": "xxx",
            "name": "xxx",
            "value": "xxx",
            "expirationDate": "xxx"
        },
    ]
    return request
```

## 拦截数据示例

> 注意：主函数使用run方法运行，不能使用start

```python
from playwright.sync_api import Response
from feapder.utils.webdriver import (
    PlaywrightDriver,
    InterceptResponse,
    InterceptRequest,
)

import feapder


def on_response(response: Response):
    print(response.url)


class TestPlaywright(feapder.AirSpider):
    __custom_setting__ = dict(
        RENDER_DOWNLOADER="feapder.network.downloader.PlaywrightDownloader",
        PLAYWRIGHT=dict(
            user_agent=None,  # 字符串 或 无参函数，返回值为user_agent
            proxy=None,  # xxx.xxx.xxx.xxx:xxxx 或 无参函数，返回值为代理地址
            headless=False,  # 是否为无头浏览器
            driver_type="chromium",  # chromium、firefox、webkit
            timeout=30,  # 请求超时时间
            window_size=(1024, 800),  # 窗口大小
            executable_path=None,  # 浏览器路径，默认为默认路径
            download_path=None,  # 下载文件的路径
            render_time=0,  # 渲染时长，即打开网页等待指定时间后再获取源码
            wait_until="networkidle",  # 等待页面加载完成的事件,可选值："commit", "domcontentloaded", "load", "networkidle"
            use_stealth_js=False,  # 使用stealth.min.js隐藏浏览器特征
            # page_on_event_callback=dict(response=on_response),  # 监听response事件
            # page.on() 事件的回调 如 page_on_event_callback={"dialog": lambda dialog: dialog.accept()}
            storage_state_path=None,  # 保存浏览器状态的路径
            url_regexes=["wallpaper/list"],  # 拦截接口，支持正则，数组类型
            save_all=True,  # 是否保存所有拦截的接口
        ),
    )

    def start_requests(self):
        yield feapder.Request(
            "http://www.soutushenqi.com/image/search/?searchWord=%E6%A0%91%E5%8F%B6",
            render=True,
        )

    def parse(self, reqeust, response):
        driver: PlaywrightDriver = response.driver

        intercept_response: InterceptResponse = driver.get_response("wallpaper/list")
        intercept_request: InterceptRequest = intercept_response.request

        req_url = intercept_request.url
        req_header = intercept_request.headers
        req_data = intercept_request.data
        print("请求url", req_url)
        print("请求header", req_header)
        print("请求data", req_data)

        data = driver.get_json("wallpaper/list")
        print("接口返回的数据", data)

        print("------ 测试save_all=True ------- ")

        # 测试save_all=True
        all_intercept_response: list = driver.get_all_response("wallpaper/list")
        for intercept_response in all_intercept_response:
            intercept_request: InterceptRequest = intercept_response.request
            req_url = intercept_request.url
            req_header = intercept_request.headers
            req_data = intercept_request.data
            print("请求url", req_url)
            print("请求header", req_header)
            print("请求data", req_data)

        all_intercept_json = driver.get_all_json("wallpaper/list")
        for intercept_json in all_intercept_json:
            print("接口返回的数据", intercept_json)

        # 千万别忘了
        driver.clear_cache()


if __name__ == "__main__":
    TestPlaywright(thread_count=1).run()
```
可通过配置的`page_on_event_callback`参数自定义事件的回调，如设置`on_response`的事件回调，亦可直接使用`url_regexes`设置拦截的接口

## 操作浏览器对象示例

> 注意：主函数使用run方法运行，不能使用start

```python
import time

from playwright.sync_api import Page

import feapder
from feapder.utils.webdriver import PlaywrightDriver


class TestPlaywright(feapder.AirSpider):
    __custom_setting__ = dict(
        RENDER_DOWNLOADER="feapder.network.downloader.PlaywrightDownloader",
    )

    def start_requests(self):
        yield feapder.Request("https://www.baidu.com", render=True)

    def parse(self, reqeust, response):
        driver: PlaywrightDriver = response.driver
        page: Page = driver.page

        page.type("#kw", "feapder")
        page.click("#su")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        html = page.content()
        response.text = html  # 使response加载最新的页面
        for data_container in response.xpath("//div[@class='c-container']"):
            print(data_container.xpath("string(.//h3)").extract_first())


if __name__ == "__main__":
    TestPlaywright(thread_count=1).run()
```