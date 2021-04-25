import requests
from hyper.contrib import HTTP20Adapter

_request = requests.Session.request


class MyHTTP20Adapter(HTTP20Adapter):
    def __init__(self, *args, **kwargs):
        super(MyHTTP20Adapter, self).__init__(*args, **kwargs)
        super(HTTP20Adapter, self).__init__(*args, **kwargs)


def request(self, method, url, http2=False, **kwargs):
    if http2:
        self.mount("https://", MyHTTP20Adapter())
    return _request(self, method=method, url=url, **kwargs)


requests.Session.request = request

if __name__ == '__main__':
    c = MyHTTP20Adapter()
    proxies = {
        "https": "http://127.0.0.1:1087"
    }
    res = requests.get("https://http2.akamai.com/", http2=True, proxies=proxies)
    print(res.headers)
    print(res.status_code)
