import abc
import json

from feapder.utils.tools import get_md5


class GuestUser:
    def __init__(self, user_agent=None, proxies=None, cookies=None, **kwargs):
        self.user_agent = user_agent
        self.proxies = proxies
        self.cookies = cookies
        self.__dict__.update(kwargs)
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


class NormalUserPool(GuestUser):
    def __init__(self, username=None, password=None, **kwargs):
        self.username = username
        self.password = password
        super().__init__(**kwargs)


class UserPoolInterface(metaclass=abc.ABCMeta):
    """
    cookie pool interface
    """

    @abc.abstractmethod
    def create_user(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def add_user(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def get_user(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def del_user(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError
