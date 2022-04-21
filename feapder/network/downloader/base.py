import abc

from feapder.network.response import Response


class Downloader:
    @abc.abstractmethod
    def download(self, method, url, **kwargs) -> Response:
        raise NotImplementedError
