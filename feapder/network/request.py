# -*- coding: utf-8 -*-
"""
Created on 2018-07-25 11:49:08
---------
@summary: 请求结构体
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.exceptions import InsecureRequestWarning

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.db.redisdb import RedisDB
from feapder.network import user_agent
from feapder.network.proxy_pool import proxy_pool
from feapder.network.response import Response
from feapder.utils.log import log
from feapder.utils.webdriver import WebDriverPool
from requests.cookies import RequestsCookieJar

# 屏蔽warning信息
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Request(object):
    session = None
    webdriver_pool: WebDriverPool = None
    user_agent_pool = user_agent
    proxies_pool = proxy_pool

    cache_db = None  # redis / pika
    cached_redis_key = None  # 缓存response的文件文件夹 response_cached:cached_redis_key:md5
    cached_expire_time = 1200  # 缓存过期时间

    local_filepath = None
    oss_handler = None

    __REQUEST_ATTRS__ = [
        # 'method', 'url', 必须传递 不加入**kwargs中
        "params",
        "data",
        "headers",
        "cookies",
        "files",
        "auth",
        "timeout",
        "allow_redirects",
        "proxies",
        "hooks",
        "stream",
        "verify",
        "cert",
        "json",
    ]

    DEFAULT_KEY_VALUE = dict(
        url="",
        retry_times=0,
        priority=300,
        parser_name=None,
        callback=None,
        filter_repeat=True,
        auto_request=True,
        request_sync=False,
        use_session=None,
        random_user_agent=True,
        download_midware=None,
        is_abandoned=False,
        render=False,
        render_time=0,
    )

    def __init__(
        self,
        url="",
        retry_times=0,
        priority=300,
        parser_name=None,
        callback=None,
        filter_repeat=True,
        auto_request=True,
        request_sync=False,
        use_session=None,
        random_user_agent=True,
        download_midware=None,
        is_abandoned=False,
        render=False,
        render_time=0,
        **kwargs,
    ):
        """
        @summary: Request参数
        ---------
        框架参数
        @param url: 待抓取url
        @param retry_times: 当前重试次数
        @param priority: 优先级 越小越优先 默认300
        @param parser_name: 回调函数所在的类名 默认为当前类
        @param callback: 回调函数 可以是函数 也可是函数名（如想跨类回调时，parser_name指定那个类名，callback指定那个类想回调的方法名即可）
        @param filter_repeat: 是否需要去重 (True/False) 当setting中的REQUEST_FILTER_ENABLE设置为True时该参数生效 默认True
        @param auto_request: 是否需要自动请求下载网页 默认是。设置为False时返回的response为空，需要自己去请求网页
        @param request_sync: 是否同步请求下载网页，默认异步。如果该请求url过期时间快，可设置为True，相当于yield的reqeust会立即响应，而不是去排队
        @param use_session: 是否使用session方式
        @param random_user_agent: 是否随机User-Agent (True/False) 当setting中的RANDOM_HEADERS设置为True时该参数生效 默认True
        @param download_midware: 下载中间件。默认为parser中的download_midware
        @param is_abandoned: 当发生异常时是否放弃重试 True/False. 默认False
        @param render: 是否用浏览器渲染
        @param render_time: 渲染时长，即打开网页等待指定时间后再获取源码
        --
        以下参数于requests参数使用方式一致
        @param method: 请求方式，如POST或GET，默认根据data值是否为空来判断
        @param params: 请求参数
        @param data: 请求body
        @param json: 请求json字符串，同 json.dumps(data)
        @param headers:
        @param cookies: 字典 或 CookieJar 对象
        @param files:
        @param auth:
        @param timeout: (浮点或元组)等待服务器数据的超时限制，是一个浮点数，或是一个(connect timeout, read timeout) 元组
        @param allow_redirects : Boolean. True 表示允许跟踪 POST/PUT/DELETE 方法的重定向
        @param proxies: 代理 {"http":"http://xxx", "https":"https://xxx"}
        @param verify: 为 True 时将会验证 SSL 证书
        @param stream: 如果为 False，将会立即下载响应内容
        @param cert:
        --
        @param **kwargs: 其他值: 如 Request(item=item) 则item可直接用 request.item 取出
        ---------
        @result:
        """

        self.url = url
        self.retry_times = retry_times
        self.priority = priority
        self.parser_name = parser_name
        self.callback = callback
        self.filter_repeat = filter_repeat
        self.auto_request = auto_request
        self.request_sync = request_sync
        self.use_session = use_session
        self.random_user_agent = random_user_agent
        self.download_midware = download_midware
        self.is_abandoned = is_abandoned
        self.render = render
        self.render_time = render_time or setting.WEBDRIVER.get("render_time", 0)

        self.requests_kwargs = {}
        for key, value in kwargs.items():
            if key in self.__class__.__REQUEST_ATTRS__:  # 取requests参数
                self.requests_kwargs[key] = value

            self.__dict__[key] = value

    def __repr__(self):
        try:
            return "<Request {}>".format(self.url)
        except:
            return "<Request {}>".format(str(self.to_dict)[:40])

    def __setattr__(self, key, value):
        """
        针对 request.xxx = xxx 的形式，更新reqeust及内部参数值
        @param key:
        @param value:
        @return:
        """
        self.__dict__[key] = value

        if key in self.__class__.__REQUEST_ATTRS__:
            self.requests_kwargs[key] = value

    def __lt__(self, other):
        return self.priority < other.priority

    @property
    def _session(self):
        use_session = (
            setting.USE_SESSION if self.use_session is None else self.use_session
        )  # self.use_session 优先级高
        if use_session and not self.__class__.session:
            self.__class__.session = requests.Session()
            # pool_connections – 缓存的 urllib3 连接池个数  pool_maxsize – 连接池中保存的最大连接数
            http_adapter = HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
            # 任何使用该session会话的 HTTP 请求，只要其 URL 是以给定的前缀开头，该传输适配器就会被使用到。
            self.__class__.session.mount("http", http_adapter)

        return self.__class__.session

    @property
    def _webdriver_pool(self):
        if not self.__class__.webdriver_pool:
            self.__class__.webdriver_pool = WebDriverPool(**setting.WEBDRIVER)

        return self.__class__.webdriver_pool

    @property
    def to_dict(self):
        request_dict = {}

        self.callback = (
            getattr(self.callback, "__name__")
            if callable(self.callback)
            else self.callback
        )
        self.download_midware = (
            getattr(self.download_midware, "__name__")
            if callable(self.download_midware)
            else self.download_midware
        )

        for key, value in self.__dict__.items():
            if (
                key in self.__class__.DEFAULT_KEY_VALUE
                and self.__class__.DEFAULT_KEY_VALUE.get(key) == value
                or key == "requests_kwargs"
            ):
                continue

            if key in self.__class__.__REQUEST_ATTRS__:
                if not isinstance(
                    value, (bytes, bool, float, int, str, tuple, list, dict)
                ):
                    value = tools.dumps_obj(value)
            else:
                if not isinstance(value, (bytes, bool, float, int, str)):
                    value = tools.dumps_obj(value)

            request_dict[key] = value

        return request_dict

    @property
    def callback_name(self):
        return (
            getattr(self.callback, "__name__")
            if callable(self.callback)
            else self.callback
        )

    def get_response(self, save_cached=False):
        """
        获取带有selector功能的response
        @param save_cached: 保存缓存 方便调试时不用每次都重新下载
        @return:
        """
        # 设置超时默认时间
        self.requests_kwargs.setdefault("timeout", 22)  # connect=22 read=22

        # 设置stream
        # 默认情况下，当你进行网络请求后，响应体会立即被下载。你可以通过 stream 参数覆盖这个行为，推迟下载响应体直到访问 Response.content 属性。此时仅有响应头被下载下来了。缺点： stream 设为 True，Requests 无法将连接释放回连接池，除非你 消耗了所有的数据，或者调用了 Response.close。 这样会带来连接效率低下的问题。
        self.requests_kwargs.setdefault("stream", True)

        # 关闭证书验证
        self.requests_kwargs.setdefault("verify", False)

        # 设置请求方法
        method = self.__dict__.get("method")
        if not method:
            if "data" in self.requests_kwargs:
                method = "POST"
            else:
                method = "GET"

        # 随机user—agent
        headers = self.requests_kwargs.get("headers", {})
        if "user-agent" not in headers and "User-Agent" not in headers:
            if self.random_user_agent and setting.RANDOM_HEADERS:
                headers.update({"User-Agent": self.__class__.user_agent_pool.get()})
                self.requests_kwargs.update(headers=headers)
        else:
            self.requests_kwargs.setdefault(
                "headers", {"User-Agent": setting.DEFAULT_USERAGENT}
            )

        # 代理
        proxies = self.requests_kwargs.get("proxies", -1)
        if proxies == -1 and setting.PROXY_ENABLE and self.__class__.proxies_pool:
            while True:
                proxies = self.__class__.proxies_pool.get()
                if proxies:
                    self.requests_kwargs.update(proxies=proxies)
                    break
                else:
                    log.debug("暂无可用代理 ...")

        log.debug(
            """
                -------------- %srequest for ----------------
                url  = %s
                method = %s
                body = %s
                """
            % (
                ""
                if not self.parser_name
                else "%s.%s "
                % (
                    self.parser_name,
                    (
                        self.callback
                        and callable(self.callback)
                        and getattr(self.callback, "__name__")
                        or self.callback
                    )
                    or "parse",
                ),
                self.url,
                method,
                self.requests_kwargs,
            )
        )

        # def hooks(response, *args, **kwargs):
        #     print(response.url)
        #
        # self.requests_kwargs.update(hooks={'response': hooks})

        use_session = (
            setting.USE_SESSION if self.use_session is None else self.use_session
        )  # self.use_session 优先级高

        if self.render:
            # 使用request的user_agent、cookies、proxy
            user_agent = headers.get("User-Agent") or headers.get("user-agent")
            cookies = self.requests_kwargs.get("cookies")
            if cookies and isinstance(cookies, RequestsCookieJar):
                cookies = cookies.get_dict()

            if not cookies:
                cookie_str = headers.get("Cookie") or headers.get("cookie")
                if cookie_str:
                    cookies = tools.get_cookies_from_str(cookie_str)

            proxy = None
            if proxies and proxies != -1:
                proxy = proxies.get("http", "").strip("http://") or proxies.get(
                    "https", ""
                ).strip("https://")

            browser = self._webdriver_pool.get(user_agent=user_agent, proxy=proxy)

            try:
                browser.get(self.url)
                if cookies:
                    browser.cookies = cookies
                if self.render_time:
                    tools.delay_time(self.render_time)

                html = browser.page_source
                response = Response.from_dict(
                    {
                        "url": browser.current_url,
                        "cookies": browser.cookies,
                        "text": html,
                        "_content": html.encode(),
                        "status_code": 200,
                        "elapsed": 666,
                        "headers": {
                            "User-Agent": browser.execute_script(
                                "return navigator.userAgent"
                            ),
                            "Cookie": tools.cookies2str(browser.cookies),
                        },
                    }
                )

                response._cached_text = html
                response.browser = browser
            except Exception as e:
                self._webdriver_pool.remove(browser)
                raise e

        elif use_session:
            response = self._session.request(method, self.url, **self.requests_kwargs)
            response = Response(response)
        else:
            response = requests.request(method, self.url, **self.requests_kwargs)
            response = Response(response)

        if save_cached:
            self.save_cached(response, expire_time=self.__class__.cached_expire_time)

        return response

    @property
    def fingerprint(self):
        """
        request唯一表识
        @return:
        """
        url = self.__dict__.get("url", "")
        # url 归一化
        url = tools.canonicalize_url(url)
        args = [url]

        for arg in ["params", "data", "files", "auth", "cert", "json"]:
            if self.requests_kwargs.get(arg):
                args.append(self.requests_kwargs.get(arg))

        return tools.get_md5(*args)

    @property
    def _cache_db(self):
        if not self.__class__.cache_db:
            self.__class__.cache_db = RedisDB()  # .from_url(setting.pika_spider_1_uri)

        return self.__class__.cache_db

    @property
    def _cached_redis_key(self):
        if self.__class__.cached_redis_key:
            return (
                f"response_cached:{self.__class__.cached_redis_key}:{self.fingerprint}"
            )
        else:
            return f"response_cached:test:{self.fingerprint}"

    def save_cached(self, response, expire_time=1200):
        """
        使用redis保存response 用于调试 不用每回都下载
        @param response:
        @param expire_time: 过期时间
        @return:
        """

        self._cache_db.strset(self._cached_redis_key, response.to_dict, ex=expire_time)

    def get_response_from_cached(self, save_cached=True):
        """
        从缓存中获取response
        注意：
            属性值为空：
                -raw ： urllib3.response.HTTPResponse
                -connection：requests.adapters.HTTPAdapter
                -history

            属性含义改变：
                - request 由requests 改为Request
        @param: save_cached 当无缓存 直接下载 下载完是否保存缓存
        @return:
        """
        response_dict = self._cache_db.strget(self._cached_redis_key)
        if not response_dict:
            log.info("无response缓存  重新下载")
            response_obj = self.get_response(save_cached=save_cached)
        else:
            response_dict = eval(response_dict)
            response_obj = Response.from_dict(response_dict)
        return response_obj

    def del_response_cached(self):
        self._cache_db.clear(self._cached_redis_key)

    @classmethod
    def from_dict(cls, request_dict):
        for key, value in request_dict.items():
            if isinstance(value, bytes):  # 反序列化 如item
                request_dict[key] = tools.loads_obj(value)

        return cls(**request_dict)

    def copy(self):
        return self.__class__.from_dict(self.to_dict)
