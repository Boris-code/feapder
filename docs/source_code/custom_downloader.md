# 自定义下载器

下载器一共分为三种：**普通下载器**、**支持保持session的下载器**以及**浏览器渲染下载器**。默认已经在框架中内置，setting中的配置如下

```
DOWNLOADER = "feapder.network.downloader.RequestsDownloader"  # 请求下载器
SESSION_DOWNLOADER = "feapder.network.downloader.RequestsSessionDownloader"
RENDER_DOWNLOADER = "feapder.network.downloader.SeleniumDownloader"  # 渲染下载器
```

- session下载器当配置中`USE_SESSION = True`时会启用
- 渲染下载器当使用浏览器下载功能时会启用

这些下载器均为插件的形式，我们可以自定义

## 自定义普通下载器

1. 编写下载器。如在 `xxx-spider/downloader/my_downloader.py `下自定义了如下下载器

    ```
    import requests
    
    from feapder.network.downloader.base import Downloader
    from feapder.network.response import Response
    
    class RequestsDownloader(Downloader):
        def download(self, request) -> Response:
            response = requests.request(
                request.method, request.url, **request.requests_kwargs
            )
            # 将requests的response转化为feapder的Response 对象，方便后续解析时使用xpath、re等方法
            response = Response(response)
            return response
    ```
    
    注：这里返回的response对象不强制要求为是feapder的Response。返回值会传到解析函数的response参数里，若返回的是文本，则接收到的也是文本。
    
    但为了代码可读性，建议将返回值转为feapder的Response后再返回。
    
    转feapder的Response的方式有如下几种
    
    ```
    # 方式1
    # response参数为reqeusts的response
    Response(response)
    
    # 方式2
    Response.from_text(text="html内容")
    ```    

2. 在settings中指定下载器

    ```
    DOWNLOADER = "downloader.my_downloader.RequestsDownloader"
    ```

## 自定义session下载器

1. 和普通下载器一样，都是继承`Downloader`，如何保持session，可自定义。代码示例 `xxx-spider/downloader/my_downloader.py `

    ```
    class RequestsSessionDownloader(Downloader):
        session = None
    
        @property
        def _session(self):
            if not self.__class__.session:
                self.__class__.session = requests.Session()
                # pool_connections – 缓存的 urllib3 连接池个数  pool_maxsize – 连接池中保存的最大连接数
                http_adapter = HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
                # 任何使用该session会话的 HTTP 请求，只要其 URL 是以给定的前缀开头，该传输适配器就会被使用到。
                self.__class__.session.mount("http", http_adapter)
    
            return self.__class__.session
    
        def download(self, request) -> Response:
            response = self._session.request(
                request.method, request.url, **request.requests_kwargs
            )
            response = Response(response)
            return response
    ```

2. 在settings中指定下载器

    ```
    SESSION_DOWNLOADER = "downloader.my_downloader.RequestsSessionDownloader"
    ```

注意，这里要配置 `SESSION_DOWNLOADER`

## 自定义浏览器渲染下载器

1. 编写下载器 `xxx-spider/downloader/my_downloader.py `

**若浏览器框架本身不支持多线程，但想在多线程中使用，如playwright使用，参考如下：**

```
import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.network.downloader.base import RenderDownloader
from feapder.network.response import Response
from feapder.utils.webdriver import WebDriverPool, PlaywrightDriver


class MyDownloader(RenderDownloader):
    webdriver_pool: WebDriverPool = None

    @property
    def _webdriver_pool(self):
        if not self.__class__.webdriver_pool:
            self.__class__.webdriver_pool = WebDriverPool(
                **setting.PLAYWRIGHT, driver_cls=PlaywrightDriver, thread_safe=True
            )

        return self.__class__.webdriver_pool

    def download(self, request) -> Response:
        # 代理优先级 自定义 > 配置文件 > 随机
        if request.custom_proxies:
            proxy = request.get_proxy()
        elif setting.PLAYWRIGHT.get("proxy"):
            proxy = setting.PLAYWRIGHT.get("proxy")
        else:
            proxy = request.get_proxy()

        # user_agent优先级 自定义 > 配置文件 > 随机
        if request.custom_ua:
            user_agent = request.get_user_agent()
        elif setting.PLAYWRIGHT.get("user_agent"):
            user_agent = setting.PLAYWRIGHT.get("user_agent")
        else:
            user_agent = request.get_user_agent()

        cookies = request.get_cookies()
        url = request.url
        render_time = request.render_time or setting.PLAYWRIGHT.get("render_time")
        wait_until = setting.PLAYWRIGHT.get("wait_until") or "domcontentloaded"
        if request.get_params():
            url = tools.joint_url(url, request.get_params())

        driver: PlaywrightDriver = self._webdriver_pool.get(
            user_agent=user_agent, proxy=proxy
        )
        try:
            if cookies:
                driver.url = url
                driver.cookies = cookies
            driver.page.goto(url, wait_until=wait_until)

            if render_time:
                tools.delay_time(render_time)

            html = driver.page.content()
            response = Response.from_dict(
                {
                    "url": driver.page.url,
                    "cookies": driver.cookies,
                    "_content": html.encode(),
                    "status_code": 200,
                    "elapsed": 666,
                    "headers": {
                        "User-Agent": driver.user_agent,
                        "Cookie": tools.cookies2str(driver.cookies),
                    },
                }
            )

            response.driver = driver
            response.browser = driver
            return response
        except Exception as e:
            self._webdriver_pool.remove(driver)
            raise e

    def close(self, driver):
        if driver:
            self._webdriver_pool.remove(driver)

    def put_back(self, driver):
        """
        释放浏览器对象
        """
        self._webdriver_pool.put(driver)

    def close_all(self):
        """
        关闭所有浏览器
        """
        # 不支持
        # self._webdriver_pool.close()
        pass
```

这里使用了WebDriverPool，参数`thread_safe=True`，即要保证使用时的线程安全，确保同个浏览器对象只能被同一个线程调用

**若浏览器框架本身支持多线程，如selenium，则参考如下**

```
import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.network.downloader.base import RenderDownloader
from feapder.network.response import Response
from feapder.utils.webdriver import WebDriverPool, SeleniumDriver


class MyDownloader(RenderDownloader):
    webdriver_pool: WebDriverPool = None

    @property
    def _webdriver_pool(self):
        if not self.__class__.webdriver_pool:
            self.__class__.webdriver_pool = WebDriverPool(
                **setting.WEBDRIVER, driver=SeleniumDriver
            )

        return self.__class__.webdriver_pool

    def download(self, request) -> Response:
        # 代理优先级 自定义 > 配置文件 > 随机
        if request.custom_proxies:
            proxy = request.get_proxy()
        elif setting.WEBDRIVER.get("proxy"):
            proxy = setting.WEBDRIVER.get("proxy")
        else:
            proxy = request.get_proxy()

        # user_agent优先级 自定义 > 配置文件 > 随机
        if request.custom_ua:
            user_agent = request.get_user_agent()
        elif setting.WEBDRIVER.get("user_agent"):
            user_agent = setting.WEBDRIVER.get("user_agent")
        else:
            user_agent = request.get_user_agent()

        cookies = request.get_cookies()
        url = request.url
        render_time = request.render_time or setting.WEBDRIVER.get("render_time")
        if request.get_params():
            url = tools.joint_url(url, request.get_params())

        browser: SeleniumDriver = self._webdriver_pool.get(
            user_agent=user_agent, proxy=proxy
        )
        try:
            browser.get(url)
            if cookies:
                browser.cookies = cookies
                # 刷新使cookie生效
                browser.get(url)

            if render_time:
                tools.delay_time(render_time)

            html = browser.page_source
            response = Response.from_dict(
                {
                    "url": browser.current_url,
                    "cookies": browser.cookies,
                    "_content": html.encode(),
                    "status_code": 200,
                    "elapsed": 666,
                    "headers": {
                        "User-Agent": browser.user_agent,
                        "Cookie": tools.cookies2str(browser.cookies),
                    },
                }
            )

            response.driver = browser
            response.browser = browser
            return response
        except Exception as e:
            self._webdriver_pool.remove(browser)
            raise e

    def close(self, driver):
        if driver:
            self._webdriver_pool.remove(driver)

    def put_back(self, driver):
        """
        释放浏览器对象
        """
        self._webdriver_pool.put(driver)

    def close_all(self):
        """
        关闭所有浏览器
        """
        self._webdriver_pool.close()
```

2. 在settings中指定下载器

```
RENDER_DOWNLOADER = "downloader.my_downloader.MyDownloader"
```

注，这里要写`RENDER_DOWNLOADER`