import abc
import json

from feapder.utils.tools import get_md5


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
        return self.__dict__

    def from_dict(cls, data):
        return cls.__init__(**data)


class NormalUser(GuestUser):
    def __init__(self, username=None, password=None, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.password = password
        self.user_id = kwargs.get("user_id") or get_md5(username, password)


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
