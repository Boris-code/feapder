# -*- coding: utf-8 -*-
"""
Created on 2021/3/18 4:59 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import inspect
import json
import logging
import os
from typing import Optional, Union, List

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from feapder.utils import tools
from feapder.utils.log import log, OTHERS_LOG_LEVAL
from feapder.utils.webdriver.webdirver import *

# 屏蔽webdriver_manager日志
logging.getLogger("WDM").setLevel(OTHERS_LOG_LEVAL)


class SeleniumDriver(WebDriver, RemoteWebDriver):
    CHROME = "CHROME"
    EDGE = "EDGE"
    PHANTOMJS = "PHANTOMJS"
    FIREFOX = "FIREFOX"

    __DRIVER_ATTRS__ = {"keep_alive"}

    def __init__(self, xhr_url_regexes: list = None, **kwargs):
        """

        Args:
            xhr_url_regexes: 拦截xhr接口，支持正则，数组类型
            **kwargs:
        """
        super(SeleniumDriver, self).__init__(**kwargs)
        self._xhr_url_regexes = xhr_url_regexes
        self._driver_type = self._driver_type or SeleniumDriver.CHROME

        if self._xhr_url_regexes and self._driver_type != SeleniumDriver.CHROME:
            raise Exception(
                "xhr_url_regexes only support by chrome now! eg: driver_type=SeleniumDriver.CHROME"
            )

        if self._driver_type == SeleniumDriver.CHROME:
            self.driver = self.chrome_driver()

        elif self._driver_type == SeleniumDriver.EDGE:
            self.driver = self.edge_driver()

        elif self._driver_type == SeleniumDriver.PHANTOMJS:
            self.driver = self.phantomjs_driver()

        elif self._driver_type == SeleniumDriver.FIREFOX:
            self.driver = self.firefox_driver()

        else:
            raise TypeError(
                "dirver_type must be one of CHROME or PHANTOMJS or FIREFOX, but received {}".format(
                    type(self._driver_type)
                )
            )

        # driver.get(url)一直不返回，但也不报错的问题，这时程序会卡住，设置超时选项能解决这个问题。
        self.driver.set_page_load_timeout(self._timeout)
        # 设置10秒脚本超时时间
        self.driver.set_script_timeout(self._timeout)
        self.url = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            log.error(exc_val)

        self.quit()
        return True

    def filter_kwargs(self, kwargs: dict, driver_attrs: set):
        if not kwargs:
            return {}

        data = {}
        for key, value in kwargs.items():
            if key in driver_attrs:
                data[key] = value

        return data

    def get_options(self, default_options, *option_keys):
        for option_key in option_keys:
            options = self._kwargs.get(option_key)
            if options is not None:
                return options

        return default_options

    def get_driver_kwargs(self):
        return self.filter_kwargs(self._kwargs, self.__DRIVER_ATTRS__)

    def apply_capabilities(self, options, *capability_keys):
        for capability_key in capability_keys:
            capabilities = self._kwargs.get(capability_key)
            if not capabilities:
                continue

            for key, value in capabilities.items():
                options.set_capability(key, value)

        return options

    def build_service(self, service_cls, driver_manager_cls=None):
        service = self._kwargs.get("service")
        if service is not None:
            return service

        service_kwargs = {}
        service_args = self._kwargs.get("service_args")
        if service_args is not None:
            service_kwargs["service_args"] = service_args

        port = self._kwargs.get("port")
        if port is not None:
            service_kwargs["port"] = port

        log_path = self._kwargs.get("service_log_path")
        if log_path is None:
            log_path = self._kwargs.get("log_path")
        if log_path is not None:
            log_param = (
                "log_output"
                if "log_output" in inspect.signature(service_cls).parameters
                else "log_path"
            )
            service_kwargs[log_param] = log_path

        if self._executable_path:
            return service_cls(self._executable_path, **service_kwargs)

        if self._auto_install_driver and driver_manager_cls is not None:
            return service_cls(driver_manager_cls().install(), **service_kwargs)

        if service_kwargs:
            return service_cls(**service_kwargs)

        return None

    def create_driver(self, driver_cls, options, service):
        kwargs = self.get_driver_kwargs()
        if service is not None:
            kwargs["service"] = service

        return driver_cls(options=options, **kwargs)

    def get_proxy(self):
        return self._proxy() if callable(self._proxy) else self._proxy

    def get_user_agent(self):
        return self._user_agent() if callable(self._user_agent) else self._user_agent

    def get_driver(self):
        return self.driver

    def firefox_driver(self):
        from selenium.webdriver.firefox.service import Service

        firefox_options = self.get_options(
            webdriver.FirefoxOptions(), "options", "firefox_options"
        )
        firefox_profile = self._kwargs.get("firefox_profile")
        if firefox_profile is not None:
            firefox_options.profile = firefox_profile
        firefox_binary = self._kwargs.get("firefox_binary")
        if firefox_binary is not None:
            firefox_options.binary_location = (
                getattr(firefox_binary, "path", None)
                or getattr(firefox_binary, "_start_cmd", None)
                or firefox_binary
            )

        self.apply_capabilities(firefox_options, "desired_capabilities", "capabilities")
        if self._proxy:
            proxy = self.get_proxy()
            firefox_options.set_capability(
                "proxy",
                {
                    "proxyType": "MANUAL",
                    "httpProxy": proxy,
                    "ftpProxy": proxy,
                    "sslProxy": proxy,
                },
            )

        if self._user_agent:
            firefox_options.set_preference(
                "general.useragent.override", self.get_user_agent()
            )

        if not self._load_images:
            firefox_options.set_preference("permissions.default.image", 2)

        if self._headless:
            firefox_options.add_argument("--headless")
            firefox_options.add_argument("--disable-gpu")

        # 添加自定义的配置参数
        if self._custom_argument:
            for arg in self._custom_argument:
                firefox_options.add_argument(arg)

        service = self.build_service(Service, GeckoDriverManager)
        driver = self.create_driver(webdriver.Firefox, firefox_options, service)

        if self._window_size:
            driver.set_window_size(*self._window_size)

        return driver

    def chrome_driver(self):
        chrome_options = self.get_options(
            webdriver.ChromeOptions(), "options", "chrome_options"
        )
        # 此步骤很重要，设置为开发者模式，防止被各大网站识别出来使用了Selenium
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        # docker 里运行需要
        chrome_options.add_argument("--no-sandbox")
        from selenium.webdriver.chrome.service import Service

        self.apply_capabilities(chrome_options, "desired_capabilities")

        if self._proxy:
            chrome_options.add_argument("--proxy-server={}".format(self.get_proxy()))
        if self._user_agent:
            chrome_options.add_argument("user-agent={}".format(self.get_user_agent()))
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

        if self._download_path:
            os.makedirs(self._download_path, exist_ok=True)
            prefs = {
                "download.prompt_for_download": False,
                "download.default_directory": self._download_path,
            }
            chrome_options.add_experimental_option("prefs", prefs)

        # 添加自定义的配置参数
        if self._custom_argument:
            for arg in self._custom_argument:
                chrome_options.add_argument(arg)

        service = self.build_service(Service, ChromeDriverManager)
        driver = self.create_driver(webdriver.Chrome, chrome_options, service)

        # 隐藏浏览器特征
        if self._use_stealth_js:
            with open(
                os.path.join(os.path.dirname(__file__), "../js/stealth.min.js")
            ) as f:
                js = f.read()
                driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument", {"source": js}
                )

        if self._xhr_url_regexes:
            assert isinstance(self._xhr_url_regexes, list)
            with open(
                os.path.join(os.path.dirname(__file__), "../js/intercept.js")
            ) as f:
                js = f.read()
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument", {"source": js}
            )
            js = f"window.__urlRegexes = {self._xhr_url_regexes}"
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument", {"source": js}
            )

        if self._download_path:
            driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": self._download_path},
            )

        return driver

    def edge_driver(self):
        edge_options = self.get_options(
            webdriver.EdgeOptions(), "options", "edge_options"
        )
        # 此步骤很重要，设置为开发者模式，防止被各大网站识别出来使用了Selenium
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option("useAutomationExtension", False)
        # docker 里运行需要
        edge_options.add_argument("--no-sandbox")
        from selenium.webdriver.edge.service import Service

        self.apply_capabilities(edge_options, "desired_capabilities")

        if self._proxy:
            edge_options.add_argument("--proxy-server={}".format(self.get_proxy()))
        if self._user_agent:
            edge_options.add_argument("user-agent={}".format(self.get_user_agent()))
        if not self._load_images:
            edge_options.add_experimental_option(
                "prefs", {"profile.managed_default_content_settings.images": 2}
            )

        if self._headless:
            edge_options.add_argument("--headless")
            edge_options.add_argument("--disable-gpu")

        if self._window_size:
            edge_options.add_argument(
                "--window-size={},{}".format(self._window_size[0], self._window_size[1])
            )

        if self._download_path:
            os.makedirs(self._download_path, exist_ok=True)
            prefs = {
                "download.prompt_for_download": False,
                "download.default_directory": self._download_path,
            }
            edge_options.add_experimental_option("prefs", prefs)

        # 添加自定义的配置参数
        if self._custom_argument:
            for arg in self._custom_argument:
                edge_options.add_argument(arg)

        service = self.build_service(Service)
        driver = self.create_driver(webdriver.Edge, edge_options, service)

        # 隐藏浏览器特征
        if self._use_stealth_js:
            with open(
                os.path.join(os.path.dirname(__file__), "../js/stealth.min.js")
            ) as f:
                js = f.read()
                driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument", {"source": js}
                )

        if self._xhr_url_regexes:
            assert isinstance(self._xhr_url_regexes, list)
            with open(
                os.path.join(os.path.dirname(__file__), "../js/intercept.js")
            ) as f:
                js = f.read()
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument", {"source": js}
            )
            js = f"window.__urlRegexes = {self._xhr_url_regexes}"
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument", {"source": js}
            )

        if self._download_path:
            driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": self._download_path},
            )

        return driver

    def phantomjs_driver(self):
        raise NotImplementedError(
            "PhantomJS is not supported by Selenium 4. "
            "Please use CHROME, EDGE, or FIREFOX."
        )

    @property
    def domain(self):
        return tools.get_domain(self.url or self.driver.current_url)

    @property
    def cookies(self):
        cookies_json = {}
        for cookie in self.driver.get_cookies():
            cookies_json[cookie["name"]] = cookie["value"]

        return cookies_json

    @cookies.setter
    def cookies(self, val: Union[dict, List[dict]]):
        """
        设置cookie
        Args:
            val: {"key":"value", "key2":"value2"}

        Returns:

        """
        if isinstance(val, list):
            for cookie in val:
                # "path", "domain", "secure", "expiry"
                _cookie = {
                    "name": cookie.get("name"),
                    "value": cookie.get("value"),
                    "domain": cookie.get("domain"),
                    "path": cookie.get("path"),
                    "expires": cookie.get("expires"),
                    "secure": cookie.get("secure"),
                }
                self.driver.add_cookie(_cookie)
        else:
            for key, value in val.items():
                self.driver.add_cookie({"name": key, "value": value})

    @property
    def user_agent(self):
        return self.driver.execute_script("return navigator.userAgent;")

    def xhr_response(self, xhr_url_regex) -> Optional[InterceptResponse]:
        data = self.driver.execute_script(
            f'return window.__ajaxData["{xhr_url_regex}"];'
        )
        if not data:
            return None

        request = InterceptRequest(**data["request"])
        response = InterceptResponse(request, **data["response"])
        return response

    def xhr_data(self, xhr_url_regex) -> Union[str, dict, None]:
        response = self.xhr_response(xhr_url_regex)
        if not response:
            return None
        return response.content

    def xhr_text(self, xhr_url_regex) -> Optional[str]:
        response = self.xhr_response(xhr_url_regex)
        if not response:
            return None
        if isinstance(response.content, dict):
            return json.dumps(response.content, ensure_ascii=False)
        return response.content

    def xhr_json(self, xhr_url_regex) -> Optional[dict]:
        text = self.xhr_text(xhr_url_regex)
        return json.loads(text)

    def __getattr__(self, name):
        if self.driver:
            return getattr(self.driver, name)
        else:
            raise AttributeError

    # def __del__(self):
    #     self.quit()
