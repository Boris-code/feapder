# -*- coding: utf-8 -*-
"""
Created on 2018/12/27 11:32 AM
---------
@summary: cookie池
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import abc
import datetime
import random
import time
import warnings
from collections import Iterable
from enum import Enum, unique

import feapder.utils.tools as tools
from feapder import setting
from feapder.db.mysqldb import MysqlDB
from feapder.db.redisdb import RedisDB
from feapder.utils import metrics
from feapder.utils.log import log
from feapder.utils.redis_lock import RedisLock
from feapder.utils.tools import send_msg
from feapder.utils.webdriver import WebDriver


class CookiePoolInterface(metaclass=abc.ABCMeta):
    """
    cookie pool interface
    """

    @abc.abstractmethod
    def create_cookie(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def get_cookie(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def del_cookie(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError


class PageCookiePool(CookiePoolInterface):
    """
    由页面产生的cookie 不需要用户登陆
    """

    def __init__(
        self,
        redis_key,
        page_url=None,
        min_cookies=10000,
        must_contained_keys=(),
        keep_alive=False,
        **kwargs,
    ):
        """
        @param redis_key: 项目名
        @param page_url: 生产cookie的url
        @param min_cookies: 最小cookie数
        @param must_contained_keys: cookie 必须包含的key
        @param keep_alive: 当cookie数量足够是是否保持随时待命，生产cookie的状态。False为否，满足则退出
        ---
        @param kwargs: WebDriver的一些参数
            load_images: 是否加载图片
            user_agent_pool: user-agent池 为None时不使用
            proxies_pool: ；代理池 为None时不使用
            headless: 是否启用无头模式
            driver_type: web driver 类型
            timeout: 请求超时时间 默认16s
            window_size: 屏幕分辨率 (width, height)

        """

        self._redisdb = RedisDB()

        self._tab_cookie_pool = "{}:l_cookie_pool".format(redis_key)
        self._tab_cookie_pool_last_count = "{}:str_cookie_pool_count".format(
            redis_key
        )  # 存储上一次统计cookie 数量的时间，格式为 时间戳:数量
        self._page_url = page_url
        self._min_cookies = min_cookies
        self._must_contained_keys = must_contained_keys
        self._keep_alive = keep_alive

        self._kwargs = kwargs
        self._kwargs.setdefault("load_images", False)
        self._kwargs.setdefault("headless", True)

    def create_cookie(self):
        """
        可能会重写
        @return:
        """
        with WebDriver(**self._kwargs) as driver:
            driver.get(self._page_url)

            cookies = driver.get_cookies()

            cookies_json = {}
            for cookie in cookies:
                cookies_json[cookie["name"]] = cookie["value"]

            for key in self._must_contained_keys:
                if key not in cookies_json:
                    break
            else:
                return cookies_json

            log.error("获取cookie失败 cookies = {}".format(cookies_json))
            return None

    def add_cookies(self, cookies):
        log.info("添加cookie {}".format(cookies))
        self._redisdb.lpush(self._tab_cookie_pool, cookies)

    def run(self):
        while True:
            try:
                now_cookie_count = self._redisdb.lget_count(self._tab_cookie_pool)
                need_cookie_count = self._min_cookies - now_cookie_count

                if need_cookie_count > 0:
                    log.info(
                        "当前cookie数为 {} 小于 {}, 生产cookie".format(
                            now_cookie_count, self._min_cookies
                        )
                    )
                    try:
                        cookies = self.create_cookie()
                        if cookies:
                            self.add_cookies(cookies)
                    except Exception as e:
                        log.exception(e)
                else:
                    log.info("当前cookie数为 {} 数量足够 暂不生产".format(now_cookie_count))

                    # 判断cookie池近一分钟数量是否有变化，无变化则认为爬虫不再用了，退出
                    last_count_info = self._redisdb.strget(
                        self._tab_cookie_pool_last_count
                    )
                    if not last_count_info:
                        self._redisdb.strset(
                            self._tab_cookie_pool_last_count,
                            "{}:{}".format(time.time(), now_cookie_count),
                        )
                    else:
                        last_time, last_count = last_count_info.split(":")
                        last_time = float(last_time)
                        last_count = int(last_count)

                        if time.time() - last_time > 60:
                            if now_cookie_count == last_count:
                                log.info("近一分钟，cookie池数量无变化，判定爬虫未使用，退出生产")
                                break
                            else:
                                self._redisdb.strset(
                                    self._tab_cookie_pool_last_count,
                                    "{}:{}".format(time.time(), now_cookie_count),
                                )

                    if self._keep_alive:
                        log.info("sleep 10")
                        tools.delay_time(10)
                    else:
                        break

            except Exception as e:
                log.exception(e)
                tools.delay_time(1)

    def get_cookie(self, wait_when_null=True):
        while True:
            try:
                cookie_info = self._redisdb.rpoplpush(self._tab_cookie_pool)
                if not cookie_info and wait_when_null:
                    log.info("暂无cookie 生产中...")
                    self._keep_alive = False
                    self._min_cookies = 1
                    with RedisLock(
                        key=self._tab_cookie_pool, lock_timeout=3600, wait_timeout=5
                    ) as _lock:
                        if _lock.locked:
                            self.run()
                    continue
                return eval(cookie_info) if cookie_info else {}
            except Exception as e:
                log.exception(e)
                tools.delay_time(1)

    def del_cookie(self, cookies):
        self._redisdb.lrem(self._tab_cookie_pool, cookies)


class LoginCookiePool(CookiePoolInterface):
    """
    需要登陆的cookie池, 用户账号密码等信息用mysql保存
    """

    def __init__(
        self,
        redis_key,
        *,
        tab_userbase,
        login_state_key="login_state",
        lock_state_key="lock_state",
        username_key="username",
        password_key="password",
        login_retry_times=10,
    ):
        """
        @param redis_key: 项目名
        @param tab_userbase: 用户表名
        @param login_state_key: 登录状态列名
        @param lock_state_key: 封锁状态列名
        @param username_key: 登陆名列名
        @param password_key: 密码列名
        @param login_retry_times: 登陆失败重试次数
        """

        self._tab_cookie_pool = "{}:l_cookie_pool".format(redis_key)
        self._login_retry_times = login_retry_times
        self._tab_userbase = tab_userbase
        self._login_state_key = login_state_key
        self._lock_state_key = lock_state_key
        self._username_key = username_key
        self._password_key = password_key

        self._redisdb = RedisDB()
        self._mysqldb = MysqlDB()

        self.create_userbase()

    def create_userbase(self):
        sql = f"""
            CREATE TABLE IF NOT EXISTS `{self._tab_userbase}` (
              `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
              `{self._username_key}` varchar(50) DEFAULT NULL COMMENT '用户名',
              `{self._password_key}` varchar(255) DEFAULT NULL COMMENT '密码',
              `{self._login_state_key}` int(11) DEFAULT '0' COMMENT '登录状态（0未登录 1已登录）',
              `{self._lock_state_key}` int(11) DEFAULT '0' COMMENT '账号是否被封（0 未封 1 被封）',
              PRIMARY KEY (`id`),
              UNIQUE KEY `username` (`username`) USING BTREE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        self._mysqldb.execute(sql)

    def create_cookie(self, username, password):
        """
        创建cookie
        @param username: 用户名
        @param password: 密码
        @return: return cookie / None
        """
        raise NotImplementedError

    def get_user_info(self):
        """
        返回用户信息
        @return: yield username, password
        """

        sql = "select {username_key}, {password_key} from {tab_userbase} where {lock_state_key} != 1 and {login_state_key} != 1".format(
            username_key=self._username_key,
            password_key=self._password_key,
            tab_userbase=self._tab_userbase,
            lock_state_key=self._lock_state_key,
            login_state_key=self._login_state_key,
        )

        return self._mysqldb.find(sql)

    def handle_login_failed_user(self, username, password):
        """
        处理登录失败的user
        @param username:
        @param password:
        @return:
        """

        pass

    def handel_exception(self, e):
        """
        处理异常
        @param e:
        @return:
        """
        log.exception(e)

    def save_cookie(self, username, cookie):
        cookie_info = {"username": username, "cookie": cookie}

        self._redisdb.lpush(self._tab_cookie_pool, cookie_info)

        sql = "update {tab_userbase} set {login_state_key} = 1 where {username_key} = '{username}'".format(
            tab_userbase=self._tab_userbase,
            login_state_key=self._login_state_key,
            username_key=self._username_key,
            username=username,
        )

        self._mysqldb.update(sql)

    def get_cookie(self, wait_when_null=True):
        while True:
            try:
                cookie_info = self._redisdb.rpoplpush(self._tab_cookie_pool)
                if not cookie_info and wait_when_null:
                    log.info("暂无cookie 生产中...")
                    self.login()
                    continue
                return eval(cookie_info) if cookie_info else {}
            except Exception as e:
                log.exception(e)
                tools.delay_time(1)

    def del_cookie(self, username, cookie):
        """
        删除失效的cookie
        @param username:
        @param password:
        @return:
        """
        cookie_info = {"username": username, "cookie": cookie}
        self._redisdb.lrem(self._tab_cookie_pool, cookie_info)

        sql = "update {tab_userbase} set {login_state_key} = 0 where {username_key} = '{username}'".format(
            tab_userbase=self._tab_userbase,
            login_state_key=self._login_state_key,
            username_key=self._username_key,
            username=username,
        )

        self._mysqldb.update(sql)

    def user_is_locked(self, username):
        sql = "update {tab_userbase} set {lock_state_key} = 1 where {username_key} = '{username}'".format(
            tab_userbase=self._tab_userbase,
            lock_state_key=self._lock_state_key,
            username_key=self._username_key,
            username=username,
        )

        self._mysqldb.update(sql)

    def run(self):
        with RedisLock(
            key=self._tab_cookie_pool, lock_timeout=3600, wait_timeout=100
        ) as _lock:
            if _lock.locked:
                user_infos = self.get_user_info()
                if not isinstance(user_infos, Iterable):
                    raise ValueError("get_user_info 返回值必须可迭代")

                if not user_infos:
                    log.info("无可用用户")

                for username, password in user_infos:
                    for i in range(self._login_retry_times):
                        try:
                            cookie = self.create_cookie(username, password)
                            if cookie:
                                self.save_cookie(username, cookie)
                            else:
                                self.handle_login_failed_user(username, password)

                            break
                        except Exception as e:
                            self.handel_exception(e)

                    else:
                        self.handle_login_failed_user(username, password)

    login = run


@unique
class LimitTimesUserStatus(Enum):
    # 使用状态
    USED = "used"
    SUCCESS = "success"
    OVERDUE = "overdue"  # cookie 过期
    SLEEP = "sleep"
    EXCEPTION = "exception"
    # 登陆状态
    LOGIN_SUCCESS = "login_success"
    LOGIN_FALIED = "login_failed"


class LimitTimesUser:
    """
    有次数限制的账户
    基于本地做的缓存，不支持多进程调用
    """

    ACCOUNT_INFO_KEY = "accounts:h_account_info"  # 存储cookie的redis key
    SITE_NAME = ""  # 网站名

    redisdb = None

    def __init__(
        self,
        username,
        password,
        max_search_times,
        proxies=None,
        search_interval=0,
        **kwargs,
    ):
        """
        @param username:
        @param password:
        @param max_search_times:
        @param proxies:
        @param search_interval: 调用时间间隔。 支持元组 指定间隔的时间范围 如（5，10）即5到10秒；或直接传整数
        """
        self.__dict__.update(kwargs)
        self.username = username
        self.password = password
        self.max_search_times = max_search_times
        self.proxies = proxies
        self.search_interval = search_interval
        self.delay_use = 0  # 延时使用，用于等待解封的用户

        if isinstance(search_interval, (tuple, list)):
            if len(search_interval) != 2:
                raise ValueError("search_interval 需传递两个值的元组或列表。如（5，10）即5到10秒")

            self.used_for_time_length = (
                search_interval[1] * 5
            )  # 抢占式爬虫独享cookie时间，这段时间内其他爬虫不可抢占
        else:
            self.used_for_time_length = (
                search_interval * 5
            )  # 抢占式爬虫独享cookie时间，这段时间内其他爬虫不可抢占

        self.account_info = {
            "login_time": 0,
            "cookies": {},
            "search_times": 0,
            "last_search_time": 0,
            "used_for_spider_name": None,  # 只被某个爬虫使用 其他爬虫不可使用
            "init_search_times_time": 0,  # 初始化搜索次数的时间
        }

        if not self.__class__.redisdb:
            self.__class__.redisdb = RedisDB()

        self.sync_account_info_from_redis()

        self.__init_metrics()

    def __init_metrics(self):
        """
        初始化打点系统
        @return:
        """
        metrics.init(**setting.METRICS_OTHER_ARGS)

    def record_user_status(self, status: LimitTimesUserStatus):
        metrics.emit_counter(f"{self.username}:{status.value}", 1, classify="users")

    def __repr__(self):
        return "<LimitTimesUser {} | cookies:{}>".format(self.username, self.cookies)

    def __eq__(self, other):
        return self.username == other.username

    def sync_account_info_from_redis(self):
        account_info = self.redisdb.hget(self.ACCOUNT_INFO_KEY, self.username)
        if account_info:
            account_info = eval(account_info)
            self.account_info.update(account_info)

    @property
    def cookies(self):
        cookies = self.account_info.get("cookies")
        return cookies

    def set_cookies(self, cookies):
        self.account_info["cookies"] = cookies
        return self.redisdb.hset(
            self.ACCOUNT_INFO_KEY, self.username, self.account_info
        )

    def set_login_time(self, login_time=None):
        self.account_info["login_time"] = login_time or time.time()
        return self.redisdb.hset(
            self.ACCOUNT_INFO_KEY, self.username, self.account_info
        )

    def get_login_time(self):
        return self.account_info.get("login_time")

    def is_time_to_login(self):
        return time.time() - self.get_login_time() > 40 * 60

    def get_last_search_time(self):
        return self.account_info.get("last_search_time", 0)

    def is_time_to_search(self):
        if self.delay_use:
            is_time = time.time() - self.get_last_search_time() > self.delay_use
            if is_time:
                self.delay_use = 0

        else:
            is_time = time.time() - self.get_last_search_time() > (
                random.randint(*self.search_interval)
                if isinstance(self.search_interval, (tuple, list))
                else self.search_interval
            )

        return is_time

    @property
    def used_for_spider_name(self):
        return self.account_info.get("used_for_spider_name")

    @used_for_spider_name.setter
    def used_for_spider_name(self, spider_name):
        self.account_info["used_for_spider_name"] = spider_name

    def update_status(self):
        """
        更新search的一些状态
        @return:
        """
        self.account_info["search_times"] += 1
        self.account_info["last_search_time"] = time.time()

        return self.redisdb.hset(
            self.ACCOUNT_INFO_KEY, self.username, self.account_info
        )

    @property
    def search_times(self):
        init_search_times_time = self.account_info.get("init_search_times_time")
        current_time = time.time()
        if (
            current_time - init_search_times_time >= 86400
        ):  # 如果距离上次初始化搜索次数时间大于1天，则搜索次数清清零
            self.account_info["search_times"] = 0
            self.account_info["init_search_times_time"] = current_time

            self.redisdb.hset(self.ACCOUNT_INFO_KEY, self.username, self.account_info)

        return self.account_info["search_times"]

    def is_overwork(self):
        if self.search_times > self.max_search_times:
            log.warning("账号 {} 请求次数超限制".format(self.username))
            return True

        return False

    def is_at_work_time(self):
        if datetime.datetime.now().hour in list(range(7, 23)):
            return True

        log.warning("账号 {} 不再工作时间内".format(self.username))
        return False

    def del_cookie(self):
        self.account_info["cookies"] = {}
        return self.redisdb.hset(
            self.ACCOUNT_INFO_KEY, self.username, self.account_info
        )

    def create_cookie(self):
        """
        生产cookie 有异常需要抛出
        @return: cookie_dict
        """

        raise NotImplementedError

    def login(self):
        """
        @return: 1 成功 0 失败
        """

        try:
            # 预检查
            if not self.is_time_to_login():
                log.info("此账号尚未到登陆时间: {}".format(self.username))
                time.sleep(5)
                return 0

            cookies = self.create_cookie()
            if not cookies:
                raise Exception("登陆失败 未获取到合法cookie")

            if not isinstance(cookies, dict):
                raise Exception("cookie 必须为字典格式")

            # 保存cookie
            self.set_login_time()
            self.set_cookies(cookies)
            log.info("登录成功 {}".format(self.username))
            self.record_user_status(LimitTimesUserStatus.LOGIN_SUCCESS)
            return 1

        except Exception as e:
            log.exception(e)
            send_msg(
                msg=f"{self.SITE_NAME} {self.username} 账号登陆异常 exception: {str(e)}",
                level="error",
                message_prefix=f"{self.SITE_NAME} {self.username} 账号登陆异常",
            )

        log.info("登录失败 {}".format(self.username))
        self.record_user_status(LimitTimesUserStatus.LOGIN_FALIED)
        return 0


class LimitTimesUserPool:
    """
    限制查询次数的用户的User pool
    基于本地做的缓存，不支持多进程调用
    """

    LOAD_USER_INTERVAL = 60

    def __init__(self, *, accounts_dict, limit_user_class, support_more_client=True):
        """
        @param accounts_dic: 账户信息字典
            {
                "15011300228": {
                    "password": "300228",
                    "proxies": {},
                    "max_search_times": 500,
                    "search_interval": 1, # 使用时间间隔
                    # 其他携带信息
                }
            }
        @param limit_user_class: 用户重写的 limit_user_class
        @param support_more_client: 是否支持多客户端 即多线程 多进程模式 (可能在计数上及使用频率上有些误差)
        """
        self.accounts_dict = accounts_dict
        self.limit_user_class = limit_user_class

        self.limit_times_users = []
        self.current_user_index = -1

        self.support_more_client = support_more_client

        self.last_load_user_time = 0

    def __load_users(self, username=None):
        # 装载user
        log.info("更新可用用户")

        for _username, detail in self.accounts_dict.items():
            if username and username != _username:
                continue

            limit_times_users = self.limit_user_class(username=_username, **detail)
            if limit_times_users in self.limit_times_users:
                continue

            if limit_times_users.is_overwork():
                continue
            else:
                if (
                    limit_times_users.cookies or limit_times_users.login()
                ):  # 如果有cookie 或者登陆成功 则添加到可用的user队列
                    self.limit_times_users.append(limit_times_users)

        self.last_load_user_time = time.time()

    def get_user(
        self,
        username=None,
        used_for_spider_name=None,
        wait_when_null=True,
        not_limit_frequence=False,
    ) -> LimitTimesUser:
        """
        @params username: 获取指定的用户
        @params used_for_spider_name: 独享式使用，独享爬虫的名字。其他爬虫不可抢占
        @params wait_when_null: 无用户时是否等待
        @params not_limit_frequence: 不限制使用频率
        @return: LimitTimesUser
        """
        if not self.support_more_client:
            warnings.warn(
                "LimitTimesUserCookiePool 取查询次数等信息时基于本地做的缓存，不支持多进程或多线程",
                category=Warning,
            )
            self._is_show_warning = True

        while True:
            if (
                not self.limit_times_users
                or time.time() - self.last_load_user_time >= self.LOAD_USER_INTERVAL
            ):
                self.__load_users(username)
                if not self.limit_times_users:
                    log.warning("无可用的用户")
                    if wait_when_null:
                        time.sleep(1)
                        continue
                    else:
                        return None

            self.current_user_index += 1
            self.current_user_index = self.current_user_index % len(
                self.limit_times_users
            )

            limit_times_user = self.limit_times_users[self.current_user_index]
            if self.support_more_client:  # 需要先同步下最新数据
                limit_times_user.sync_account_info_from_redis()

            if username and limit_times_user.username != username:
                log.info(
                    "{} 为非指定用户 {}, 获取下一个用户".format(limit_times_user.username, username)
                )
                time.sleep(1)
                continue

            # 独占式使用，若为其他爬虫，检查等待使用时间是否超过独占时间，若超过则可以使用
            if (
                limit_times_user.used_for_spider_name
                and limit_times_user.used_for_spider_name != used_for_spider_name
            ):
                wait_time = time.time() - limit_times_user.get_last_search_time()
                if wait_time < limit_times_user.used_for_time_length:
                    log.info(
                        "用户{} 被 {} 爬虫独占，需等待 {} 秒后才可使用".format(
                            limit_times_user.username,
                            limit_times_user.used_for_spider_name,
                            limit_times_user.used_for_time_length - wait_time,
                        )
                    )
                    time.sleep(1)
                    continue

            if (
                not limit_times_user.is_overwork()
                and limit_times_user.is_at_work_time()
            ):
                if not limit_times_user.cookies:
                    self.limit_times_users.remove(limit_times_user)
                    continue

                if not_limit_frequence or limit_times_user.is_time_to_search():
                    limit_times_user.used_for_spider_name = used_for_spider_name

                    limit_times_user.update_status()
                    log.info("使用用户 {}".format(limit_times_user.username))
                    limit_times_user.record_user_status(LimitTimesUserStatus.USED)
                    return limit_times_user
                else:
                    log.info("{} 用户使用间隔过短 查看下一个用户".format(limit_times_user.username))
                    time.sleep(1)
                    continue
            else:
                self.limit_times_users.remove(limit_times_user)
                self.current_user_index -= 1

                if not limit_times_user.is_at_work_time():
                    log.warning("用户 {} 不在工作时间".format(limit_times_user.username))
                    if wait_when_null:
                        time.sleep(30)
                        continue
                    else:
                        return None

    def del_user(self, username):
        for limit_times_user in self.limit_times_users:
            if limit_times_user.username == username:
                limit_times_user.del_cookie()
                self.limit_times_users.remove(limit_times_user)
                limit_times_user.record_user_status(LimitTimesUserStatus.OVERDUE)
                self.__load_users(username)
                break

    def update_cookies(self, username, cookies):
        for limit_times_user in self.limit_times_users:
            if limit_times_user.username == username:
                limit_times_user.set_cookies(cookies)
                break

    def delay_use(self, username, delay_seconds):
        for limit_times_user in self.limit_times_users:
            if limit_times_user.username == username:
                limit_times_user.delay_use = delay_seconds
                limit_times_user.record_user_status(LimitTimesUserStatus.SLEEP)
                break

    def record_success_user(self, username):
        for limit_times_user in self.limit_times_users:
            if limit_times_user.username == username:
                limit_times_user.record_user_status(LimitTimesUserStatus.SUCCESS)

    def record_exception_user(self, username):
        for limit_times_user in self.limit_times_users:
            if limit_times_user.username == username:
                limit_times_user.record_user_status(LimitTimesUserStatus.EXCEPTION)
