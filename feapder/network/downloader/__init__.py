from feapder.network.response import Response
import abc


class Downloader:
    @abc.abstractmethod
    def download(self, method, url, **kwargs) -> Response:
        raise NotImplementedError
