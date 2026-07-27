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
import socket
import sys
import threading
import types

import requests
from requests.cookies import RequestsCookieJar
from requests.packages.urllib3.exceptions import InsecureRequestWarning

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.db.redisdb import RedisDB
from feapder.network import user_agent
from feapder.network.downloader.base import Downloader, RenderDownloader
from feapder.network.proxy_pool import BaseProxyPool
from feapder.network.response import Response
from feapder.utils.log import log

# 屏蔽warning信息
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 预定义锁类型（用于 _should_skip_value 方法，避免每次都创建新对象）
_LOCK_TYPES = (type(threading.Lock()), type(threading.RLock()))


class Request:
    user_agent_pool = user_agent
    proxies_pool: BaseProxyPool = None

    cache_db = None  # redis / pika
    cached_redis_key = None  # 缓存response的文件文件夹 response_cached:cached_redis_key:md5
    cached_expire_time = 1200  # 缓存过期时间

    # 下载器
    downloader: Downloader = None
    session_downloader: Downloader = None
    render_downloader: RenderDownloader = None

    # 智能上下文管理
    _callback_needs = None  # 静态分析结果: direct模式的参数需求
    _transitive_needs = None  # 传递性分析结果: transitive模式的参数需求
    _request_context = None  # 线程本地存储，用于传递父请求对象

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
        auto_inherit_context=False,
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

        # ====================== 智能上下文继承逻辑 ======================
        # 如果启用了自动上下文继承，并且已完成静态分析
        if auto_inherit_context and self.__class__._callback_needs:
            import inspect
            from feapder import setting
            from feapder.utils.log import log

            # 1. 确定使用哪种模式：direct（只传递给下一层）或 transitive（传递给所有后续层）
            mode = getattr(setting, "SMART_CONTEXT_MODE", "transitive")

            # 2. 获取当前回调函数需要的参数列表
            # callback 可能是: 函数/方法(callable), 字符串(函数名), 或 None
            # 注意: 当 callback 是 bound method (如 self.parse_detail) 时,
            #       callback.__name__ 可以正确获取到方法名 'parse_detail'
            if callback is None:
                # 没有回调函数，跳过智能上下文
                callback_name = None
            elif callable(callback):
                # 可调用对象（函数、方法、bound method）
                try:
                    callback_name = callback.__name__
                except AttributeError:
                    # 某些可调用对象可能没有 __name__ 属性
                    log.warning(f"[智能上下文] callback 没有 __name__ 属性: {callback}")
                    callback_name = None
            elif isinstance(callback, str):
                # 字符串形式的函数名（用于跨类回调）
                callback_name = callback
            else:
                # 未知类型，记录警告并跳过
                log.warning(f"[智能上下文] 不支持的 callback 类型: {type(callback)}")
                callback_name = None

            # 如果有有效的 callback_name，进行参数继承
            if callback_name:
                if mode == "transitive" and self.__class__._transitive_needs:
                    # transitive 模式：获取当前回调及所有后续回调需要的参数（传递性需求）
                    needed_params = self.__class__._transitive_needs.get(callback_name, set())
                else:
                    # direct 模式：只获取当前回调自己需要的参数（直接需求）
                    needed_params = self.__class__._callback_needs.get(callback_name, set())

                # 3. 如果有需要的参数，开始收集
                if needed_params:
                    # 获取调用者的栈帧（用于提取局部变量）
                    caller_frame = inspect.currentframe().f_back

                    # 边界检查：如果无法获取栈帧（如在 C 扩展中调用），跳过参数继承
                    if not caller_frame:
                        log.warning(f"[智能上下文] 无法获取调用者栈帧，跳过参数继承")
                    else:
                        try:
                            caller_locals = caller_frame.f_locals

                            # 获取父请求对象（从调用者局部变量 request 获取）
                            parent_request = caller_locals.get('request', None)

                            # 4. 从三个来源收集参数（按优先级从高到低）
                            inherited_params = {}

                            for param_name in needed_params:
                                # 优先级1: 显式传入的 kwargs（最高优先级）
                                # 注意：这里不添加到 inherited_params，因为它本来就在 kwargs 中
                                if param_name in kwargs:
                                    continue

                                # 优先级2: 调用者的局部变量
                                if param_name in caller_locals:
                                    value = caller_locals[param_name]
                                    # 过滤掉特殊对象（None 值允许传递，用户可能需要显式清除父级的值）
                                    if not self._should_skip_value(param_name, value):
                                        inherited_params[param_name] = value
                                        continue

                                # 优先级3: 父请求的属性（最低优先级）
                                if parent_request and hasattr(parent_request, param_name):
                                    value = getattr(parent_request, param_name)
                                    # 过滤掉特殊对象和 None 值（父请求的 None 值不继承，避免传递空值）
                                    if value is not None and not self._should_skip_value(param_name, value):
                                        inherited_params[param_name] = value

                            # 5. 将收集到的参数合并到 kwargs 中
                            if inherited_params:
                                kwargs.update(inherited_params)
                                log.debug(f"[智能上下文] {callback_name} 继承参数: {list(inherited_params.keys())}")
                        finally:
                            # 显式清理栈帧引用，避免潜在的内存泄漏
                            del caller_frame

        # ====================== 原有的初始化逻辑 ======================
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

    # def __getattr__(self, item):
    #     try:
    #         return self.__dict__[item]
    #     except:
    #         raise AttributeError("Request has no attribute %s" % item)

    def __lt__(self, other):
        return self.priority < other.priority

    @property
    def _proxies_pool(self):
        if not self.__class__.proxies_pool:
            self.__class__.proxies_pool = tools.import_cls(setting.PROXY_POOL)()

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
                and download_midware.__class__.__name__ == "method"
                else download_midware
                for download_midware in self.download_midware
            ]
        else:
            self.download_midware = (
                getattr(self.download_midware, "__name__")
                if callable(self.download_midware)
                and self.download_midware.__class__.__name__ == "method"
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
                        value, (bool, float, int, str, tuple, list, dict)
                    ):
                        value = tools.dumps_obj(value)
                else:
                    if not isinstance(value, (bool, float, int, str)):
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
                proxies = self._proxies_pool.get_proxy()
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

    def del_proxy(self):
        proxy = self.get_proxy()
        if proxy:
            self._proxies_pool.del_proxy(proxy)
            del self.requests_kwargs["proxies"]

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

    @staticmethod
    def _should_skip_value(param_name: str, value) -> bool:
        """
        判断是否应该跳过某个参数值（过滤特殊对象）

        Args:
            param_name: 参数名
            value: 参数值

        Returns:
            bool: True 表示应该跳过，False 表示可以继承
        """
        # 1. 过滤 response 对象（避免传递整个响应对象）
        if param_name == 'response':
            return True

        # 2. 过滤 self（避免传递爬虫实例）
        if param_name == 'self':
            return True

        # 3. 过滤私有变量（以 _ 开头）
        if param_name.startswith('_'):
            return True

        # 4. 过滤函数和方法
        if callable(value):
            return True

        # 5. 过滤模块对象
        if isinstance(value, types.ModuleType):
            return True

        # 6. 过滤不可序列化的对象（文件句柄、数据库连接等）
        # 文件对象 (通过 fileno() 判断是否是真正的文件对象)
        if hasattr(value, 'fileno'):
            try:
                value.fileno()  # 真正的文件对象会有有效的文件描述符
                return True
            except (AttributeError, OSError, ValueError, TypeError):
                # AttributeError: 对象没有 fileno 方法（虽然 hasattr 检查过，但可能是属性）
                # OSError: 文件已关闭或无效
                # ValueError: 无效的文件描述符
                # TypeError: fileno() 参数错误
                pass  # 不是真正的文件对象

        # Socket 对象
        if isinstance(value, socket.socket):
            return True

        # 线程/锁对象
        if isinstance(value, _LOCK_TYPES):
            return True

        # 7. 过滤过大的对象（避免占用过多内存）
        # 检查对象大小，如果超过 1MB 则跳过并记录警告
        try:
            size = sys.getsizeof(value)
            # 对于容器类型（list, dict, set等），递归计算实际大小
            if isinstance(value, (list, tuple, set, frozenset)):
                size += sum(sys.getsizeof(item) for item in value)
            elif isinstance(value, dict):
                size += sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in value.items())

            # 如果对象大于 1MB，跳过并记录警告
            if size > 1024 * 1024:  # 1MB
                log.warning(f"[智能上下文] 跳过大对象 {param_name} (大小: {size / 1024 / 1024:.2f}MB)")
                return True
        except Exception:
            # 如果无法计算大小，不跳过（保持向后兼容）
            pass

        return False
