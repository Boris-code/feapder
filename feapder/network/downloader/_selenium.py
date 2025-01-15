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
            if cookies:
                browser.cookies = cookies
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
