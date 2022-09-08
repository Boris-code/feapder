# -*- coding: utf-8 -*-
"""
Created on 2021/3/18 4:59 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import json
import logging
import os
from typing import Optional, Union

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from feapder.utils.log import log, OTHERS_LOG_LEVAL
from feapder.utils.webdriver.webdirver import WebDriver

# 屏蔽webdriver_manager日志
logging.getLogger("WDM").setLevel(OTHERS_LOG_LEVAL)


class XhrRequest:
    def __init__(self, url, data, headers):
        self.url = url
        self.data = data
        self.headers = headers


class XhrResponse:
    def __init__(self, request: XhrRequest, url, headers, content, status_code):
        self.request = request
        self.url = url
        self.headers = headers
        self.content = content
        self.status_code = status_code


class SeleniumDriver(WebDriver, RemoteWebDriver):
    CHROME = "CHROME"
    PHANTOMJS = "PHANTOMJS"
    FIREFOX = "FIREFOX"

    __CHROME_ATTRS__ = {
        "executable_path",
        "port",
        "options",
        "service_args",
        "desired_capabilities",
        "service_log_path",
        "chrome_options",
        "keep_alive",
    }

    __FIREFOX_ATTRS__ = {
        "firefox_profile",
        "firefox_binary",
        "timeout",
        "capabilities",
        "proxy",
        "executable_path",
        "options",
        "service_log_path",
        "firefox_options",
        "service_args",
        "desired_capabilities",
        "log_path",
        "keep_alive",
    }
    __PHANTOMJS_ATTRS__ = {
        "executable_path",
        "port",
        "desired_capabilities",
        "service_args",
        "service_log_path",
    }

    def __init__(self, **kwargs):
        super(SeleniumDriver, self).__init__(**kwargs)

        if self._xhr_url_regexes and self.driver_type != SeleniumDriver.CHROME:
            raise Exception(
                "xhr_url_regexes only support by chrome now! eg: driver_type=SeleniumDriver.CHROME"
            )

        if self._driver_type == SeleniumDriver.CHROME:
            self.driver = self.chrome_driver()

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

    def get_driver(self):
        return self.driver

    def firefox_driver(self):
        firefox_profile = webdriver.FirefoxProfile()
        firefox_options = webdriver.FirefoxOptions()
        firefox_capabilities = webdriver.DesiredCapabilities.FIREFOX

        if self._proxy:
            proxy = self._proxy() if callable(self._proxy) else self._proxy
            firefox_capabilities["marionette"] = True
            firefox_capabilities["proxy"] = {
                "proxyType": "MANUAL",
                "httpProxy": proxy,
                "ftpProxy": proxy,
                "sslProxy": proxy,
            }

        if self._user_agent:
            firefox_profile.set_preference(
                "general.useragent.override",
                self._user_agent() if callable(self._user_agent) else self._user_agent,
            )

        if not self._load_images:
            firefox_profile.set_preference("permissions.default.image", 2)

        if self._headless:
            firefox_options.add_argument("--headless")
            firefox_options.add_argument("--disable-gpu")

        # 添加自定义的配置参数
        if self._custom_argument:
            for arg in self._custom_argument:
                firefox_options.add_argument(arg)

        kwargs = self.filter_kwargs(self._kwargs, self.__FIREFOX_ATTRS__)

        if self._executable_path:
            kwargs.update(executable_path=self._executable_path)
        elif self._auto_install_driver:
            kwargs.update(executable_path=GeckoDriverManager().install())

        driver = webdriver.Firefox(
            capabilities=firefox_capabilities,
            options=firefox_options,
            firefox_profile=firefox_profile,
            **kwargs,
        )

        if self._window_size:
            driver.set_window_size(*self._window_size)

        return driver

    def chrome_driver(self):
        chrome_options = webdriver.ChromeOptions()
        # 此步骤很重要，设置为开发者模式，防止被各大网站识别出来使用了Selenium
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        # docker 里运行需要
        chrome_options.add_argument("--no-sandbox")

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

        kwargs = self.filter_kwargs(self._kwargs, self.__CHROME_ATTRS__)
        if self._executable_path:
            kwargs.update(executable_path=self._executable_path)
        elif self._auto_install_driver:
            kwargs.update(executable_path=ChromeDriverManager().install())

        driver = webdriver.Chrome(options=chrome_options, **kwargs)

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
            driver.command_executor._commands["send_command"] = (
                "POST",
                "/session/$sessionId/chromium/send_command",
            )
            params = {
                "cmd": "Page.setDownloadBehavior",
                "params": {"behavior": "allow", "downloadPath": self._download_path},
            }
            driver.execute("send_command", params)

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

        # 添加自定义的配置参数
        if self._custom_argument:
            for arg in self._custom_argument:
                service_args.append(arg)

        kwargs = self.filter_kwargs(self._kwargs, self.__PHANTOMJS_ATTRS__)

        if self._executable_path:
            kwargs.update(executable_path=self._executable_path)

        driver = webdriver.PhantomJS(
            service_args=service_args, desired_capabilities=dcap, **kwargs
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

    @property
    def user_agent(self):
        return self.driver.execute_script("return navigator.userAgent;")

    def xhr_response(self, xhr_url_regex) -> Optional[XhrResponse]:
        data = self.driver.execute_script(
            f'return window.__ajaxData["{xhr_url_regex}"];'
        )
        if not data:
            return None

        request = XhrRequest(**data["request"])
        response = XhrResponse(request, **data["response"])
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
