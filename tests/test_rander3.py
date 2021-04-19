import time

import feapder
from feapder.utils.webdriver import WebDriver


class TestRender(feapder.AirSpider):
    def start_requests(self):
        yield feapder.Request("http://www.baidu.com", render=True)

    def parse(self, request, response):
        browser: WebDriver = response.browser
        browser.find_element_by_id("kw").send_keys("feapder")
        browser.find_element_by_id("su").click()
        time.sleep(5)
        print(browser.page_source)


if __name__ == "__main__":
    TestRender().start()
