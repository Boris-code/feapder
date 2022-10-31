# -*- coding: utf-8 -*-
"""
Created on 2022/9/15 8:47 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

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
