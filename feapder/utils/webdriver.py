# -*- coding: utf-8 -*-
"""
Created on 2021/3/18 4:59 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import queue
import threading

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.common.proxy import Proxy, ProxyType

from feapder.utils.log import log
from feapder.utils.tools import Singleton

DEFAULT_USERAGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"


class WebDriver(RemoteWebDriver):
    CHROME = "CHROME"
    PHANTOMJS = "PHANTOMJS"
    FIREFOX = 'FIREFOX'

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
            user_data_dir=None,
            **kwargs
    ):
        """
        webdirver 封装，支持chrome及phantomjs 和firefox
        Args:
            load_images: 是否加载图片
            user_agent: 字符串 或 无参函数，返回值为user_agent
            proxy: xxx.xxx.xxx.xxx:xxxx 或 无参函数，返回值为代理地址
            headless: 是否启用无头模式
            driver_type: CHROME 或 PHANTOMJS,FIREFOX
            timeout: 请求超时时间
            window_size: # 窗口大小
            executable_path: 浏览器路径，默认为默认路径
            user_data_dir: 浏览器用户目录，只支持chrome 和 firefox
            **kwargs:
        """
        self._load_images = load_images
        self._user_agent = user_agent or DEFAULT_USERAGENT
        self._proxy = proxy
        self._headless = headless
        self._timeout = timeout
        self._window_size = window_size
        self._executable_path = executable_path

        self.proxies = {}
        self.user_agent = None

        self._user_data_dir = user_data_dir

        if driver_type == WebDriver.CHROME:
            self.driver = self.chrome_driver()

        elif driver_type == WebDriver.PHANTOMJS:
            self.driver = self.phantomjs_driver()

        elif driver_type == WebDriver.FIREFOX:
            self.driver = self.firefox_driver()

        else:
            raise TypeError(
                "dirver_type must be one of CHROME or PHANTOMJS or FIREFOX, but received {}".format(
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

    def firefox_driver(self):
        if self._user_data_dir:
            firefox_profile = webdriver.FirefoxProfile(profile_directory=self._user_data_dir)
        else:
            firefox_profile = webdriver.FirefoxProfile()

        firefox_options = webdriver.FirefoxOptions()
        firefox_capabilities = webdriver.DesiredCapabilities.FIREFOX

        if self._user_agent:
            firefox_profile.set_preference("general.useragent.override", self._user_agent()
            if callable(self._user_agent)
            else self._user_agent)

        if not self._load_images:
            firefox_profile.set_preference('permissions.default.image', 2)

        if self._proxy:
            firefox_capabilities['marionette'] = True
            firefox_capabilities['proxy'] = {
                "proxyType": "MANUAL",
                "httpProxy": self._proxy,
                "ftpProxy": self._proxy,
                "sslProxy": self._proxy
            }

        if self._headless:
            firefox_options.add_argument('--headless')
            firefox_options.add_argument('--disable-gpu')

        if self._window_size:
            firefox_options.add_argument(
                "--window-size={},{}".format(self._window_size[0], self._window_size[1])
            )

        if self._executable_path:
            driver = webdriver.Firefox(
                capabilities=firefox_capabilities,
                options=firefox_options,
                firefox_profile=firefox_profile,
                executable_path=self._executable_path
            )
        else:
            driver = webdriver.Firefox(
                capabilities=firefox_capabilities,
                options=firefox_options,
                firefox_profile=firefox_profile)

        return driver

    def chrome_driver(self):
        chrome_options = webdriver.ChromeOptions()
        # 此步骤很重要，设置为开发者模式，防止被各大网站识别出来使用了Selenium
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        if self._user_data_dir:
            chrome_options.add_argument(f"--user-data-dir={self._user_data_dir}")
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
            driver = webdriver.Chrome(options=chrome_options)

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

    @cookies.setter
    def cookies(self, val: dict):
        """
        设置cookie
        Args:
            val: {"key":"value", "key2":"value2"}

        Returns:

        """
        for key, value in val.items():
            self.driver.add_cookie({"name": key, "value": value})

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
        self.queue = queue.Queue(maxsize=pool_size)
        self.kwargs = kwargs
        self.lock = threading.RLock()
        self.driver_count = 0

    @property
    def is_full(self):
        return self.driver_count >= self.queue.maxsize

    def get(self, user_agent: str = None, proxy: str = None) -> WebDriver:
        """
        获取webdriver
        当webdriver为新实例时会使用 user_agen, proxy, cookie参数来创建
        Args:
            user_agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36
            proxy: xxx.xxx.xxx.xxx
        Returns:

        """
        if not self.is_full:
            with self.lock:
                if not self.is_full:
                    kwargs = self.kwargs.copy()
                    if user_agent:
                        kwargs["user_agent"] = user_agent
                    if proxy:
                        kwargs["proxy"] = proxy
                    driver = WebDriver(**kwargs)
                    self.queue.put(driver)
                    self.driver_count += 1

        driver = self.queue.get()
        return driver

    def put(self, driver):
        self.queue.put(driver)

    def remove(self, driver):
        driver.quit()
        self.driver_count -= 1

    def close(self):
        while not self.queue.empty():
            driver = self.queue.get()
            driver.quit()
            self.driver_count -= 1
