# -*- coding: utf-8 -*-
"""
Created on 2022/9/7 4:11 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import os

from playwright.sync_api import Page, BrowserContext
from playwright.sync_api import Playwright, Browser
from playwright.sync_api import sync_playwright

from feapder.utils.log import log
from feapder.utils.webdriver.webdirver import WebDriver


class PlaywrightDriver(WebDriver):
    def __init__(self, **kwargs):
        super(PlaywrightDriver, self).__init__(**kwargs)
        self.driver: Playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self._setup()

    def _setup(self):
        self.driver = sync_playwright().start()
        self.browser = self.driver.chromium.launch(
            headless=self._headless, args=["--no-sandbox"]
        )

        self.context = self.browser.new_context(user_agent=self._user_agent)
        if self._use_stealth_js:
            path = os.path.join(os.path.dirname(__file__), "../js/stealth.min.js")
            self.context.add_init_script(path=path)

        self.page = self.context.new_page()
        self.page.set_default_timeout(self._timeout * 1000)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            log.error(exc_val)

        self.quit()
        return True

    def quit(self):
        self.page.close()
        self.context.close()
        self.browser.close()
        self.driver.stop()

    @property
    def cookies(self):
        cookies_json = {}
        for cookie in self.page.context.cookies():
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
        cookies = []
        for key, value in val.items():
            cookies.append({"name": key, "value": value})
        self.page.context.add_cookies(cookies)

    @property
    def user_agent(self):
        return self.page.evaluate("() => navigator.userAgent")
