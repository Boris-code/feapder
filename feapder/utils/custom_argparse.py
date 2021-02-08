# -*- coding: utf-8 -*-
"""
Created on 2018-10-15 14:32:12
---------
@summary: 封装ArgumentParser， 使其支持function， 调用start自动执行
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import argparse


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        self.functions = {}

        super(ArgumentParser, self).__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs):
        function = kwargs.pop("function") if "function" in kwargs else None
        key = self._get_optional_kwargs(*args, **kwargs).get("dest")
        self.functions[key] = function

        return super(ArgumentParser, self).add_argument(*args, **kwargs)

    def start(self, args=None, namespace=None):
        args = self.parse_args(args=args, namespace=namespace)
        for key, value in vars(args).items():  # vars() 函数返回对象object的属性和属性值的字典对象
            if value not in (None, False):
                if callable(self.functions[key]):
                    if value != True:
                        if isinstance(value, list) and len(value) == 1:
                            value = value[0]
                        self.functions[key](value)
                    else:
                        self.functions[key]()

    def run(self, args, values=None):
        if args in self.functions:
            if values:
                self.functions[args](values)
            else:
                self.functions[args]()

        else:
            raise Exception(f"无此方法: {args}")


if __name__ == "__main__":

    def test():
        print("test not args func")

    def test2(args):
        print("test args func", args)

    parser = ArgumentParser(description="测试")

    parser.add_argument("--test2", type=int, nargs=1, help="(1|2）", function=test2)
    parser.add_argument("--test", action="store_true", help="", function=test)

    parser.start()
