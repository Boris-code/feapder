# -*- coding: utf-8 -*-
"""
Created on 2020/5/8 2:24 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import sys
from os.path import dirname, join

from feapder.commands import create_builder
from feapder.commands import shell
from feapder.commands import zip

HELP = """
███████╗███████╗ █████╗ ██████╗ ██████╗ ███████╗██████╗
██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
█████╗  █████╗  ███████║██████╔╝██║  ██║█████╗  ██████╔╝
██╔══╝  ██╔══╝  ██╔══██║██╔═══╝ ██║  ██║██╔══╝  ██╔══██╗
██║     ███████╗██║  ██║██║     ██████╔╝███████╗██║  ██║
╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝     ╚═════╝ ╚══════╝╚═╝  ╚═╝

Version: {version}
Document: http://feapder.com

Usage:
  feapder <command> [options] [args]
      
Available commands:
"""


def _print_commands():
    with open(join(dirname(dirname(__file__)), "VERSION"), "rb") as f:
        version = f.read().decode("ascii").strip()

    print(HELP.rstrip().format(version=version))
    cmds = {
        "create": "create project、spider、item and so on",
        "shell": "debug response",
        "zip": "zip project",
    }
    for cmdname, cmdclass in sorted(cmds.items()):
        print("  %-13s %s" % (cmdname, cmdclass))

    print('\nUse "feapder <command> -h" to see more info about a command')


def execute():
    args = sys.argv
    if len(args) < 2:
        _print_commands()
        return

    command = args.pop(1)
    if command == "create":
        create_builder.main()
    elif command == "shell":
        shell.main()
    elif command == "zip":
        zip.main()
    else:
        _print_commands()


if __name__ == "__main__":
    execute()
