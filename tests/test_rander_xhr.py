import time

import feapder
from feapder.utils.webdriver import WebDriver


class TestRender(feapder.AirSpider):
    __custom_setting__ = dict(
        WEBDRIVER=dict(
            pool_size=1,  # 浏览器的数量
            load_images=True,  # 是否加载图片
            user_agent=None,  # 字符串 或 无参函数，返回值为user_agent
            proxy=None,  # xxx.xxx.xxx.xxx:xxxx 或 无参函数，返回值为代理地址
            headless=False,  # 是否为无头浏览器
            driver_type="CHROME",  # CHROME、EDGE、PHANTOMJS、FIREFOX
            timeout=30,  # 请求超时时间
            window_size=(1024, 800),  # 窗口大小
            executable_path=None,  # 浏览器路径，默认为默认路径
            render_time=0,  # 渲染时长，即打开网页等待指定时间后再获取源码
            custom_argument=["--ignore-certificate-errors"],  # 自定义浏览器渲染参数
            xhr_url_regexes=[
                "/ad",
            ],  # 拦截 http://www.spidertools.cn/spidertools/ad 接口
        )
    )

    def start_requests(self):
        yield feapder.Request("http://www.spidertools.cn", render=True)

    def parse(self, request, response):
        browser: WebDriver = response.browser
        time.sleep(3)

        # 获取接口数据 文本类型
        ad = browser.xhr_text("/ad")
        print(ad)

        # 获取接口数据 转成json，本例因为返回的接口是文本，所以不转了
        # browser.xhr_json("/ad")

        xhr_response = browser.xhr_response("/ad")
        print("请求接口", xhr_response.request.url)
        # 请求头目前获取的不完整
        print("请求头", xhr_response.request.headers)
        print("请求体", xhr_response.request.data)
        print("返回头", xhr_response.headers)
        print("返回地址", xhr_response.url)
        print("返回内容", xhr_response.content)


if __name__ == "__main__":
    TestRender().start()
