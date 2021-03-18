# -*- coding: utf-8 -*-
"""
Created on 2021/3/18 4:59 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import collections
import threading

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from feapder.utils.log import log
from feapder.utils.tools import Singleton


class WebDriver:
    CHROME = "CHROME"
    PHANTOMJS = "PHANTOMJS"

    def __init__(
        self,
        load_images=True,
        user_agent=None,
        proxy=None,
        headless=False,
        driver_type=PHANTOMJS,
        timeout=16,
        window_size=(1024, 800),
        executable_path=None,
    ):
        """

        @param load_images: 是否加载图片
        @param user_agent_pool: user-agent池 为None时不使用
        @param proxies_pool: ；代理池 为None时不使用
        @param headless: 是否启用无头模式
        @param driver_type: web driver 类型
        @param user_agent: 字符串 或 返回user_agent的函数
        @param proxy xxx.xxx.xxx.xxx:xxxx 或 返回代理的函数
        @param timeout: 请求超时时间 默认16s
        @param window_size: 屏幕分辨率 (width, height)
        @param executable_path: 浏览器路径，默认为默认路径
        """
        self._load_images = load_images
        self._user_agent = (
            user_agent
            or " Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        )
        self._proxy = proxy
        self._headless = headless
        self._timeout = timeout
        self._window_size = window_size
        self._executable_path = executable_path

        self.proxies = {}
        self.user_agent = None

        if driver_type == WebDriver.CHROME:
            self.driver = self.chrome_driver()

        elif driver_type == WebDriver.PHANTOMJS:
            self.driver = self.phantomjs_driver()

        else:
            raise TypeError(
                "dirver_type must be one of CHROME or PHANTOMJS, but received {}".format(
                    type(driver_type)
                )
            )

        # driver.get(url)一直不返回，但也不报错的问题，这时程序会卡住，设置超时选项能解决这个问题。
        self.driver.set_page_load_timeout(self._timeout)
        # 设置10秒脚本超时时间
        self.driver.set_script_timeout(self._timeout)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            log.error(exc_val)

        self.quit()
        return True

    def get_driver(self):
        return self.driver

    def chrome_driver(self):
        chrome_options = webdriver.ChromeOptions()
        # 此步骤很重要，设置为开发者模式，防止被各大网站识别出来使用了Selenium
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        if self._proxy:
            chrome_options.add_argument(
                "--proxy-server={}".format(
                    self._proxy() if callable(self._proxy) else self._proxy
                )
            )
        if self._user_agent:
            chrome_options.add_argument(
                "user-agent={}".format(
                    self._user_agent()
                    if callable(self._user_agent)
                    else self._user_agent
                )
            )
        if not self._load_images:
            chrome_options.add_experimental_option(
                "prefs", {"profile.managed_default_content_settings.images": 2}
            )
        if self._headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
        if self._window_size:
            chrome_options.add_argument(
                "--window-size={},{}".format(self._window_size[0], self._window_size[1])
            )

        if self._executable_path:
            driver = webdriver.Chrome(
                chrome_options=chrome_options, executable_path=self._executable_path
            )
        else:
            driver = webdriver.Chrome(chrome_options=chrome_options)

        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                  """
            },
        )

        return driver

    def phantomjs_driver(self):
        import warnings

        warnings.filterwarnings("ignore")

        service_args = []
        dcap = DesiredCapabilities.PHANTOMJS

        if self._proxy:
            service_args.append(
                "--proxy=%s" % self._proxy() if callable(self._proxy) else self._proxy
            )
        if self._user_agent:
            dcap["phantomjs.page.settings.userAgent"] = (
                self._user_agent() if callable(self._user_agent) else self._user_agent
            )
        if not self._load_images:
            service_args.append("--load-images=no")

        if self._executable_path:
            driver = webdriver.PhantomJS(
                service_args=service_args,
                desired_capabilities=dcap,
                executable_path=self._executable_path,
            )
        else:
            driver = webdriver.PhantomJS(
                service_args=service_args, desired_capabilities=dcap
            )

        if self._window_size:
            driver.set_window_size(self._window_size[0], self._window_size[1])

        del warnings

        return driver

    @property
    def cookies(self):
        cookies_json = {}
        for cookie in self.driver.get_cookies():
            cookies_json[cookie["name"]] = cookie["value"]

        return cookies_json

    def __getattr__(self, name):
        if self.driver:
            return getattr(self.driver, name)
        else:
            raise AttributeError

    # def __del__(self):
    #     self.quit()


@Singleton
class WebDriverPool:
    def __init__(self, pool_size=5, **kwargs):
        self.queue = collections.deque(maxlen=pool_size)
        self.kwargs = kwargs
        self.lock = threading.RLock()

    def get(self):
        if not len(self.queue) >= self.queue.maxlen:
            with self.lock:
                if not len(self.queue) >= self.queue.maxlen:
                    driver = WebDriver(**self.kwargs)
                    self.queue.append(driver)

        driver = self.queue.popleft()
        self.queue.append(driver)

        return driver

    def remove(self, driver):
        driver.quit()
        self.queue.remove(driver)

    def close(self):
        while self.queue:
            driver = self.queue.pop()
            driver.quit()
