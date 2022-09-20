# -*- coding: utf-8 -*-
"""
Created on 2022/9/7 4:27 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import abc

from feapder import setting


class WebDriver:
    def __init__(
        self,
        load_images=True,
        user_agent=None,
        proxy=None,
        headless=False,
        driver_type=None,
        timeout=16,
        window_size=(1024, 800),
        executable_path=None,
        custom_argument=None,
        xhr_url_regexes: list = None,
        download_path=None,
        auto_install_driver=True,
        use_stealth_js=True,
        **kwargs,
    ):
        """
        webdirver 封装，支持chrome、phantomjs 和 firefox
        Args:
            load_images: 是否加载图片
            user_agent: 字符串 或 无参函数，返回值为user_agent
            proxy: xxx.xxx.xxx.xxx:xxxx 或 无参函数，返回值为代理地址
            headless: 是否启用无头模式
            driver_type: CHROME 或 PHANTOMJS,FIREFOX
            timeout: 请求超时时间
            window_size: # 窗口大小
            executable_path: 浏览器路径，默认为默认路径
            custom_argument: 自定义参数 用于webdriver.Chrome(options=chrome_options, **kwargs)
            xhr_url_regexes: 拦截xhr接口，支持正则，数组类型
            download_path: 文件下载保存路径；如果指定，不再出现“保留”“放弃”提示，仅对Chrome有效
            auto_install_driver: 自动下载浏览器驱动 支持chrome 和 firefox
            use_stealth_js: 使用stealth.min.js隐藏浏览器特征
            **kwargs:
        """
        self._load_images = load_images
        self._user_agent = user_agent or setting.DEFAULT_USERAGENT
        self._proxy = proxy
        self._headless = headless
        self._timeout = timeout
        self._window_size = window_size
        self._executable_path = executable_path
        self._custom_argument = custom_argument
        self._xhr_url_regexes = xhr_url_regexes
        self._download_path = download_path
        self._auto_install_driver = auto_install_driver
        self._use_stealth_js = use_stealth_js
        self._driver_type = driver_type
        self._kwargs = kwargs

    @abc.abstractmethod
    def quit(self):
        pass
