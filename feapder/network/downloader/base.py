import abc
from abc import ABC

from feapder.network.response import Response


class Downloader:
    @abc.abstractmethod
    def download(self, request) -> Response:
        """

        Args:
            request: feapder.Request

        Returns: feapder.Response

        """
        raise NotImplementedError

    def close(self, response: Response):
        pass


class RenderDownloader(Downloader, ABC):
    def put_back(self, driver):
        """
        释放浏览器对象
        """
        pass

    def close_all(self):
        """
        关闭所有浏览器
        """
        pass
