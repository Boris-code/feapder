# -*- coding: utf-8 -*-
"""
Created on 2018-07-25 11:49:08
---------
@summary: 请求结构体
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import copy
import os
import re

import requests
from requests.cookies import RequestsCookieJar
from requests.packages.urllib3.exceptions import InsecureRequestWarning

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.db.redisdb import RedisDB
from feapder.network import user_agent
from feapder.network.downloader.base import Downloader, RenderDownloader
from feapder.network.proxy_pool import ProxyPool
from feapder.network.response import Response
from feapder.utils.log import log

# 屏蔽warning信息
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Request:
    user_agent_pool = user_agent
    proxies_pool: ProxyPool = None

    cache_db = None  # redis / pika
    cached_redis_key = None  # 缓存response的文件文件夹 response_cached:cached_redis_key:md5
    cached_expire_time = 1200  # 缓存过期时间

    # 下载器
    downloader: Downloader = None
    session_downloader: Downloader = None
    render_downloader: RenderDownloader = None

    __REQUEST_ATTRS__ = {
        # "method",
        # "url",
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
    }

    _DEFAULT_KEY_VALUE_ = dict(
        url="",
        method=None,
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
        make_absolute_links=None,
    )

    _CUSTOM_PROPERTIES_ = {
        "requests_kwargs",
        "custom_ua",
        "custom_proxies",
    }

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
        make_absolute_links=None,
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
        @param make_absolute_links: 是否转成绝对连接，默认是
        --
        以下参数与requests参数使用方式一致
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
        self.method = None
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
        self.render_time = render_time
        self.make_absolute_links = (
            make_absolute_links
            if make_absolute_links is not None
            else setting.MAKE_ABSOLUTE_LINKS
        )

        # 自定义属性，不参与序列化
        self.requests_kwargs = {}
        for key, value in kwargs.items():
            if key in self.__class__.__REQUEST_ATTRS__:  # 取requests参数
                self.requests_kwargs[key] = value

            self.__dict__[key] = value

        self.custom_ua = False
        self.custom_proxies = False

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
    def _proxies_pool(self):
        if not self.__class__.proxies_pool:
            self.__class__.proxies_pool = ProxyPool()

        return self.__class__.proxies_pool

    @property
    def _downloader(self):
        if not self.__class__.downloader:
            self.__class__.downloader = tools.import_cls(setting.DOWNLOADER)()

        return self.__class__.downloader

    @property
    def _session_downloader(self):
        if not self.__class__.session_downloader:
            self.__class__.session_downloader = tools.import_cls(
                setting.SESSION_DOWNLOADER
            )()

        return self.__class__.session_downloader

    @property
    def _render_downloader(self):
        if not self.__class__.render_downloader:
            try:
                self.__class__.render_downloader = tools.import_cls(
                    setting.RENDER_DOWNLOADER
                )()
            except AttributeError:
                log.error('当前是渲染模式，请安装 pip install "feapder[render]"')
                os._exit(0)

        return self.__class__.render_downloader

    @property
    def to_dict(self):
        request_dict = {}

        self.callback = (
            getattr(self.callback, "__name__")
            if callable(self.callback)
            else self.callback
        )

        if isinstance(self.download_midware, (tuple, list)):
            self.download_midware = [
                getattr(download_midware, "__name__")
                if callable(download_midware)
                else download_midware
                for download_midware in self.download_midware
            ]
        else:
            self.download_midware = (
                getattr(self.download_midware, "__name__")
                if callable(self.download_midware)
                else self.download_midware
            )

        for key, value in self.__dict__.items():
            if (
                key in self.__class__._DEFAULT_KEY_VALUE_
                and self.__class__._DEFAULT_KEY_VALUE_.get(key) == value
                or key in self.__class__._CUSTOM_PROPERTIES_
            ):
                continue

            if value is not None:
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

    def make_requests_kwargs(self):
        """
        处理参数
        """
        # 设置超时默认时间
        self.requests_kwargs.setdefault(
            "timeout", setting.REQUEST_TIMEOUT
        )  # connect=22 read=22

        # 设置stream
        # 默认情况下，当你进行网络请求后，响应体会立即被下载。
        # stream=True是，调用Response.content 才会下载响应体，默认只返回header。
        # 缺点： stream 设为 True，Requests 无法将连接释放回连接池，除非消耗了所有的数据，或者调用了 Response.close。 这样会带来连接效率低下的问题。
        self.requests_kwargs.setdefault("stream", True)

        # 关闭证书验证
        self.requests_kwargs.setdefault("verify", False)

        # 设置请求方法
        method = self.__dict__.get("method")
        if not method:
            if "data" in self.requests_kwargs or "json" in self.requests_kwargs:
                method = "POST"
            else:
                method = "GET"
        self.method = method

        # 设置user—agent
        headers = self.requests_kwargs.get("headers", {})
        if "user-agent" not in headers and "User-Agent" not in headers:
            if self.random_user_agent and setting.RANDOM_HEADERS:
                # 随机user—agent
                ua = self.__class__.user_agent_pool.get(setting.USER_AGENT_TYPE)
                headers.update({"User-Agent": ua})
                self.requests_kwargs.update(headers=headers)
            else:
                # 使用默认的user—agent
                self.requests_kwargs.setdefault(
                    "headers", {"User-Agent": setting.DEFAULT_USERAGENT}
                )
        else:
            self.custom_ua = True

        # 代理
        proxies = self.requests_kwargs.get("proxies", -1)
        if proxies == -1 and setting.PROXY_ENABLE and setting.PROXY_EXTRACT_API:
            while True:
                proxies = self._proxies_pool.get()
                if proxies:
                    self.requests_kwargs.update(proxies=proxies)
                    break
                else:
                    log.debug("暂无可用代理 ...")
        else:
            self.custom_proxies = True

    def get_response(self, save_cached=False):
        """
        获取带有selector功能的response
        @param save_cached: 保存缓存 方便调试时不用每次都重新下载
        @return:
        """
        self.make_requests_kwargs()

        log.debug(
            """
                -------------- %srequest for ----------------
                url  = %s
                method = %s
                args = %s
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
                self.method,
                self.requests_kwargs,
            )
        )

        # def hooks(response, *args, **kwargs):
        #     print(response.url)
        #
        # self.requests_kwargs.update(hooks={'response': hooks})

        # self.use_session 优先级高
        use_session = (
            setting.USE_SESSION if self.use_session is None else self.use_session
        )

        if self.render:
            response = self._render_downloader.download(self)
        elif use_session:
            response = self._session_downloader.download(self)
        else:
            response = self._downloader.download(self)

        response.make_absolute_links = self.make_absolute_links

        if save_cached:
            self.save_cached(response, expire_time=self.__class__.cached_expire_time)

        return response

    def get_params(self):
        return self.requests_kwargs.get("params")

    def get_proxies(self) -> dict:
        """

        Returns: {"https": "https://ip:port", "http": "http://ip:port"}

        """
        return self.requests_kwargs.get("proxies")

    def get_proxy(self) -> str:
        """

        Returns: ip:port

        """
        proxies = self.get_proxies()
        if proxies:
            return re.sub(
                "http.*?//", "", proxies.get("http", "") or proxies.get("https", "")
            )

    def get_headers(self) -> dict:
        return self.requests_kwargs.get("headers", {})

    def get_user_agent(self) -> str:
        return self.get_headers().get("user_agent") or self.get_headers().get(
            "User-Agent"
        )

    def get_cookies(self) -> dict:
        cookies = self.requests_kwargs.get("cookies")
        if cookies and isinstance(cookies, RequestsCookieJar):
            cookies = cookies.get_dict()

        if not cookies:
            cookie_str = self.get_headers().get("Cookie") or self.get_headers().get(
                "cookie"
            )
            if cookie_str:
                cookies = tools.get_cookies_from_str(cookie_str)
        return cookies

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
        return self.__class__.from_dict(copy.deepcopy(self.to_dict))
