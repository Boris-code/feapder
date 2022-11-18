# -*- coding: utf-8 -*-
"""
Created on 2022/11/18 12:33 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import argparse

from feapder.core.handle_failed_items import HandleFailedItems
from feapder.core.handle_failed_requests import HandleFailedRequests


def retry_failed_requests(redis_key):
    handle_failed_requests = HandleFailedRequests(redis_key)
    handle_failed_requests.reput_failed_requests_to_requests()


def retry_failed_items(redis_key):
    handle_failed_items = HandleFailedItems(redis_key)
    handle_failed_items.reput_failed_items_to_db()
    handle_failed_items.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="重试失败的请求或入库失败的item",
        usage="usage: feapder retry [options] [args]",
    )
    parser.add_argument(
        "-r",
        "--request",
        help="重试失败的request 如 feapder retry --request <redis_key>",
        metavar="",
    )
    parser.add_argument(
        "-i", "--item", help="重试失败的item 如 feapder retry --item <redis_key>", metavar=""
    )
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    if args.request:
        retry_failed_requests(args.request)
    if args.item:
        retry_failed_items(args.item)


if __name__ == "__main__":
    main()
