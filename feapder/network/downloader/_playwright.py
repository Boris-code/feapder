# -*- coding: utf-8 -*-
"""
Created on 2022/9/7 4:05 PM
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
from feapder.utils.webdriver import WebDriverPool, PlaywrightDriver


class PlaywrightDownloader(RenderDownloader):
    webdriver_pool: WebDriverPool = None

    @property
    def _webdriver_pool(self):
        if not self.__class__.webdriver_pool:
            self.__class__.webdriver_pool = WebDriverPool(
                **setting.PLAYWRIGHT, driver_cls=PlaywrightDriver, thread_safe=True
            )

        return self.__class__.webdriver_pool

    def download(self, request) -> Response:
        proxy = request.get_proxy()
        user_agent = request.get_user_agent()
        cookies = request.get_cookies()
        url = request.url
        if request.get_params():
            url = tools.joint_url(url, request.get_params())

        driver: PlaywrightDriver = self._webdriver_pool.get(
            user_agent=user_agent, proxy=proxy
        )
        try:
            if cookies:
                driver.url = url
                driver.cookies = cookies
            driver.page.goto(url, wait_until="domcontentloaded")

            if request.render_time:
                tools.delay_time(request.render_time)

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
