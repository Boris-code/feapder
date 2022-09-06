# -*- coding: utf-8 -*-
"""
Created on 2020/5/8 2:24 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import re
from os.path import dirname, join

import requests

from feapder.commands import create_builder
from feapder.commands import shell
from feapder.commands import zip

import click

with open(join(dirname(dirname(__file__)), "VERSION"), "rb") as f:
    VERSION = f.read().decode("ascii").strip()


def check_new_version():
    try:
        url = "https://pypi.org/simple/feapder/"
        resp = requests.get(url, timeout=3)
        html = resp.text

        last_version = re.findall(r"feapder-([\d.]*?).tar.gz", html)[-1]
        now_stable_version = re.sub("-beta.*", "", VERSION)

        if now_stable_version < last_version:
            return f"feapder=={last_version}"
    except:
        pass


HELP = """
███████╗███████╗ █████╗ ██████╗ ██████╗ ███████╗██████╗
██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
█████╗  █████╗  ███████║██████╔╝██║  ██║█████╗  ██████╔╝
██╔══╝  ██╔══╝  ██╔══██║██╔═══╝ ██║  ██║██╔══╝  ██╔══██╗
██║     ███████╗██║  ██║██║     ██████╔╝███████╗██║  ██║
╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝     ╚═════╝ ╚══════╝╚═╝  ╚═╝

Version: {}
Document: http://feapder.com
""".format(VERSION)

# 打印在所有其他内容之后
EPILOG = """
Use "feapder <command> -h" to see more info about a command
"""

NEW_VERSION_TIP = """
──────────────────────────────────────────────────────
\nNew version available \033[31m{version}\033[0m → \033[32m{new_version}\033[0m
Run \033[33mpip install --upgrade feapder\033[0m to update!
"""

new_version = check_new_version()
if new_version:
    version = f"feapder=={VERSION.replace('-beta', 'b')}"
    EPILOG += "\n" + NEW_VERSION_TIP.format(version=version, new_version=new_version)


@click.group(help=HELP, epilog=EPILOG, context_settings=dict(help_option_names=['-h', '--help']), no_args_is_help=True)
def execute():
    pass


execute.add_command(create_builder.main)
execute.add_command(shell.main)
execute.add_command(zip.main)

if __name__ == "__main__":
    execute()
