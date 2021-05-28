# -*- coding: utf-8 -*-
"""
Created on 2020/5/9 12:37 AM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import json
import re
import sys

import IPython

from feapder import Request


def request(**kwargs):
    kwargs.setdefault("proxies", None)
    response = Request(**kwargs).get_response()
    print(response)

    IPython.embed(header="now you can use response")


def fetch_url(url):
    request(url=url)


def fetch_curl(curl_args):
    """
    解析及抓取curl请求
    :param curl_args:
    [url, '-H', 'xxx', '-H', 'xxx', '--data-binary', '{"xxx":"xxx"}', '--compressed']
    :return:
    """
    url = curl_args[0]
    curl_args.pop(0)

    headers = {}
    data = {}
    for i in range(0, len(curl_args), 2):
        if curl_args[i] == "-H":
            regex = "([^:\s]*)[:|\s]*(.*)"
            result = re.search(regex, curl_args[i + 1], re.S).groups()
            if result[0] in headers:
                headers[result[0]] = headers[result[0]] + "&" + result[1]
            else:
                headers[result[0]] = result[1].strip()

        elif curl_args[i] == "--data-binary":
            data = json.loads(curl_args[i + 1])

    request(url=url, data=data, headers=headers)


def usage():
    """
下载调试器

usage: feapder shell [options] [args]

optional arguments:
  -u, --url     抓取指定url
  -c, --curl    抓取curl格式的请求

    """
    print(usage.__doc__)
    sys.exit()


def main():
    args = sys.argv
    if len(args) < 3:
        usage()

    elif args[1] in ("-h", "--help"):
        usage()

    elif args[1] in ("-u", "--url"):
        fetch_url(args[2])

    elif args[1] in ("-c", "--curl"):
        fetch_curl(args[2:])

    else:
        usage()


if __name__ == "__main__":
    main()
