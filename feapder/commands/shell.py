# -*- coding: utf-8 -*-
"""
Created on 2020/5/9 12:37 AM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import argparse
import re
import shlex

import IPython
import pyperclip

from feapder import Request
from feapder.utils import tools

import click


def parse_curl(curl_str):
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("target_url", type=str, nargs="?")
    parser.add_argument("-X", "--request", type=str, nargs=1, default="")
    parser.add_argument("-H", "--header", nargs=1, action="append", default=[])
    parser.add_argument("-d", "--data", nargs=1, action="append", default=[])
    parser.add_argument("--data-ascii", nargs=1, action="append", default=[])
    parser.add_argument("--data-binary", nargs=1, action="append", default=[])
    parser.add_argument("--data-urlencode", nargs=1, action="append", default=[])
    parser.add_argument("--data-raw", nargs=1, action="append", default=[])
    parser.add_argument("-F", "--form", nargs=1, action="append", default=[])
    parser.add_argument("--digest", action="store_true")
    parser.add_argument("--ntlm", action="store_true")
    parser.add_argument("--anyauth", action="store_true")
    parser.add_argument("-e", "--referer", type=str)
    parser.add_argument("-G", "--get", action="store_true", default=False)
    parser.add_argument("-I", "--head", action="store_true")
    parser.add_argument("-k", "--insecure", action="store_true")
    parser.add_argument("-o", "--output", type=str)
    parser.add_argument("-O", "--remote_name", action="store_true")
    parser.add_argument("-r", "--range", type=str)
    parser.add_argument("-u", "--user", type=str)
    parser.add_argument("--url", type=str)
    parser.add_argument("-A", "--user-agent", type=str)
    parser.add_argument("--compressed", action="store_true", default=False)

    curl_split = shlex.split(curl_str)
    try:
        args = parser.parse_known_args(curl_split[1:])[0]
    except:
        raise ValueError("Could not parse arguments.")

    # 请求地址
    url = args.target_url

    # # 请求方法
    # try:
    #     method = args.request.lower()
    # except AttributeError:
    #     method = args.request[0].lower()

    # 请求头
    headers = {
        h[0].split(":", 1)[0]: ("".join(h[0].split(":", 1)[1]).strip())
        for h in args.header
    }
    if args.user_agent:
        headers["User-Agent"] = args.user_agent
    if args.referer:
        headers["Referer"] = args.referer
    if args.range:
        headers["Range"] = args.range

    # Cookie
    cookie_str = headers.pop("Cookie", "") or headers.pop("cookie", "")
    cookies = tools.get_cookies_from_str(cookie_str) if cookie_str else {}

    # params
    url, params = tools.parse_url_params(url)

    # data
    data = "".join(
        [
            "".join(d)
            for d in args.data
                     + args.data_ascii
                     + args.data_binary
                     + args.data_raw
                     + args.form
        ]
    )
    if data:
        data = re.sub(r"^\$", "", data)

    # method
    if args.head:
        method = "head"
    elif args.get:
        method = "get"
        params.update(data)
    elif args.request:
        method = (
            args.request[0].lower()
            if isinstance(args.request, list)
            else args.request.lower()
        )
    elif data:
        method = "post"
    else:
        method = "get"
        params.update(data)

    username = None
    password = None
    if args.user:
        u = args.user
        if ":" in u:
            username, password = u.split(":")
        else:
            username = u
            password = input(f"请输入用户{username}的密码")

    auth = None
    if args.digest:
        auth = "digest"
    elif args.ntlm:
        auth = "ntlm"
    elif username:
        auth = "basic"

    insecure = args.insecure

    return dict(
        url=url,
        method=method,
        cookies=cookies,
        headers=headers,
        params=params,
        data=data,
        insecure=insecure,
        username=username,
        password=password,
        auth=auth,
    )


def request(**kwargs):
    kwargs.setdefault("proxies", None)
    response = Request(**kwargs).get_response()
    print(response)

    IPython.embed(header="now you can use response")


def fetch_url(url):
    request(url=url)


def fetch_curl():
    input("请复制请求为cURL (bash)，复制后按任意键读取剪切板内容\n")
    curl = pyperclip.paste()
    if curl:
        kwargs = parse_curl(curl)
        request(**kwargs)


def parse_args():
    parser = argparse.ArgumentParser(
        description="测试请求",
        usage="usage: feapder shell [options] [args]",
    )
    parser.add_argument(
        "-u",
        "--url",
        help="请求指定地址, 如 feapder shell --url http://www.spidertools.cn/",
        metavar="",
    )
    parser.add_argument("-c", "--curl", help="执行curl，调试响应", action="store_true")

    args = parser.parse_args()
    return parser, args


@click.command(name="shell", short_help="debug response", context_settings=dict(help_option_names=['-h', '--help']), no_args_is_help=True)
@click.option("-u", "--url", help="请求指定地址, 如 feapder shell --url http://www.spidertools.cn/", metavar="")
@click.option("-c", "--curl", help="执行curl，调试响应", is_flag=True)
def main(**kwargs):
    """
    测试请求
    """

    if kwargs.get("url", ""):
        fetch_url(kwargs["url"])
    elif kwargs.get("curl", ""):
        fetch_curl()


if __name__ == "__main__":
    main()
