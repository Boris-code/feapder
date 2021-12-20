import abc
import json
import random
import time
from datetime import datetime

from feapder.db.redisdb import RedisDB
from feapder.utils.log import log
from feapder.utils.tools import get_md5, timestamp_to_date


class GuestUser:
    def __init__(self, user_agent=None, proxies=None, cookies=None, **kwargs):
        self.__dict__.update(kwargs)
        self.user_agent = user_agent
        self.proxies = proxies
        self.cookies = cookies
        self.user_id = kwargs.get("user_id") or get_md5(user_agent, proxies, cookies)

    def __str__(self):
        return f"<{self.__class__.__name__}>: " + json.dumps(
            self.to_dict(), indent=4, ensure_ascii=False
        )

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        data = {}
        for key, value in self.__dict__.items():
            if value is not None:
                data[key] = value
        return data

    def from_dict(cls, data):
        return cls.__init__(**data)


class NormalUser(GuestUser):
    def __init__(self, username, password, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.password = password
        self.user_id = kwargs.get("user_id") or self.username  # 用户名作为user_id


class GoldUser(NormalUser):
    """
    昂贵的账号
    """

    redisdb: RedisDB = None
    redis_key: str = None

    def __init__(
        self,
        max_use_times,
        use_interval=0,
        work_time=(7, 23),
        login_interval=30 * 60,
        exclusive_time=None,
        **kwargs,
    ):
        """
        @param max_use_times:
        @param use_interval: 使用时间间隔。 支持元组 指定间隔的时间范围 如（5，10）即5到10秒；或直接传整数
        @param work_time: 工作时间，默认 7点到23点
        @param login_interval: 登录时间间隔 防止频繁登录 导致账号被封
        @param exclusive_time: 独占时长
        """
        super().__init__(**kwargs)
        self.max_use_times = max_use_times
        self.use_interval = use_interval
        self.work_time = work_time
        self.login_interval = login_interval
        self.exclusive_time = exclusive_time or (
            use_interval[-1] * 5
            if isinstance(use_interval, (tuple, list))
            else use_interval * 5
        )

        self._delay_use = kwargs.get("_delay_use", 0)  # 延时使用，用于等待解封的用户
        self._login_time = kwargs.get("_login_time", 0)
        self._use_times = kwargs.get("_use_times", 0)
        self._last_use_time = kwargs.get("_last_use_time", 0)
        self._used_for_spider_name = kwargs.get("_used_for_spider_name")
        self._reset_use_times_date = kwargs.get("_reset_use_times_date")

    def __eq__(self, other):
        return self.username == other.username

    def update(self, ohter):
        self.__dict__.update(ohter.to_dict())

    def sycn_to_redis(self):
        self.redisdb.hset(self.redis_key, self.user_id, self.to_dict())

    def set_delay_use(self, seconds):
        self._delay_use = seconds
        self.sycn_to_redis()

    def set_cookies(self, cookies):
        self.cookies = cookies
        self.sycn_to_redis()

    def set_login_time(self, _login_time=None):
        self._login_time = _login_time or time.time()
        self.sycn_to_redis()

    def get_login_time(self):
        return self._login_time

    def get_last_use_time(self):
        return self._last_use_time

    def get_used_for_spider_name(self):
        return self._used_for_spider_name

    def set_used_for_spider_name(self, name):
        self._used_for_spider_name = name
        self._use_times += 1
        self._last_use_time = time.time()
        self.sycn_to_redis()

    def is_time_to_login(self):
        return time.time() - self.get_login_time() > self.login_interval

    def next_login_time(self):
        return timestamp_to_date(int(self.login_interval + self.get_login_time()))

    def is_time_to_use(self):
        if self._delay_use:
            is_time = time.time() - self._last_use_time > self._delay_use
            if is_time:
                self._delay_use = 0  # 不用同步了，使用用户时会同步

        else:
            is_time = time.time() - self._last_use_time > (
                random.randint(*self.use_interval)
                if isinstance(self.use_interval, (tuple, list))
                else self.use_interval
            )

        return is_time

    def reset_use_times(self):
        self._use_times = 0
        self._reset_use_times_date = datetime.now().strftime("%Y-%m-%d")
        self.sycn_to_redis()

    @property
    def get_use_times(self):
        current_date = datetime.now().strftime("%Y-%m-%d")
        if current_date != self._reset_use_times_date:
            self.reset_use_times()

        return self._use_times

    def is_overwork(self):
        if self._use_times > self.max_use_times:
            log.info("账号 {} 请求次数超限制".format(self.username))
            return True

        return False

    def is_at_work_time(self):
        if datetime.now().hour in list(range(*self.work_time)):
            return True

        log.info("账号 {} 不再工作时间内".format(self.username))
        return False


class UserPoolInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def login(self, *args, **kwargs):
        """
        登录 生产cookie
        Args:
            *args:
            **kwargs:

        Returns:

        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_user(self, *args, **kwargs):
        """
        将带有cookie的用户添加到用户池
        Args:
            *args:
            **kwargs:

        Returns:

        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_user(self, block=True):
        """
        获取用户使用
        Args:
            block: 无用户时是否等待

        Returns:

        """
        raise NotImplementedError

    @abc.abstractmethod
    def del_user(self, *args, **kwargs):
        """
        删除用户
        Args:
            *args:
            **kwargs:

        Returns:

        """
        raise NotImplementedError

    @abc.abstractmethod
    def run(self):
        """
        维护一定数量的用户
        Returns:

        """
        raise NotImplementedError
