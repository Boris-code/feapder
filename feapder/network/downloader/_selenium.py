# -*- coding: utf-8 -*-
"""
Created on 2022/7/26 4:28 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.network.downloader.base import RenderDownloader
from feapder.network.response import Response
from feapder.utils.webdriver import WebDriverPool, SeleniumDriver


class SeleniumDownloader(RenderDownloader):
    webdriver_pool: WebDriverPool = None

    @property
    def _webdriver_pool(self):
        if not self.__class__.webdriver_pool:
            self.__class__.webdriver_pool = WebDriverPool(
                **setting.WEBDRIVER, driver=SeleniumDriver
            )

        return self.__class__.webdriver_pool

    def download(self, request) -> Response:
        proxy = request.get_proxy()
        user_agent = request.get_user_agent()
        cookies = request.get_cookies()
        url = request.url
        if request.get_params():
            url = tools.joint_url(url, request.get_params())

        browser: SeleniumDriver = self._webdriver_pool.get(
            user_agent=user_agent, proxy=proxy
        )
        try:
            browser.get(url)
            if cookies:
                browser.cookies = cookies
            if request.render_time:
                tools.delay_time(request.render_time)

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
