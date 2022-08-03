# -*- coding: utf-8 -*-
"""
Created on 2022/2/13 12:59 上午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import argparse
import os
import re
import zipfile


def is_ignore_file(ignore_files: list, filename):
    for ignore_file in ignore_files:
        if re.search(ignore_file, filename):
            return True
    return False


def zip(dir_path, zip_name, ignore_dirs: list = None, ignore_files: list = None):
    print(f"正在压缩 {dir_path} >> {zip_name}")
    ignore_files.append(os.path.basename(zip_name))
    with zipfile.ZipFile(zip_name, "w") as file:
        dir_name = os.path.basename(dir_path)
        parent_dir = os.path.dirname(dir_path)
        if parent_dir:
            os.chdir(parent_dir)
        for path, dirs, filenames in os.walk(dir_name):
            # 修改原dirs，方式遍历忽略文件夹里的文件
            if ignore_dirs:
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for filename in filenames:
                if ignore_files and is_ignore_file(ignore_files, filename):
                    continue

                filepath = os.path.join(path, filename)
                print(f"  adding {filepath}")
                file.write(filepath)

    print(f"压缩成功 {dir_path} >> {zip_name}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="压缩文件夹, 默认排除以下文件夹及文件 .git,__pycache__,.idea,venv,.DS_Store",
        usage="feapder zip dir_path [zip_name]",
    )
    parser.add_argument("dir_path", type=str, help="文件夹路径")
    parser.add_argument("zip_name", type=str, nargs="?", help="压缩后的文件名，默认为文件夹名.zip")
    parser.add_argument("-i", help="忽略文件，逗号分隔，支持正则", metavar="")
    parser.add_argument("-I", help="忽略文件夹，逗号分隔，支持正则 ", metavar="")
    parser.add_argument("-o", help="输出路径，默认为当前目录", metavar="")

    args = parser.parse_args()
    return args


def main():
    ignore_dirs = [".git", "__pycache__", ".idea", "venv"]
    ignore_files = [".DS_Store"]
    args = parse_args()
    if args.i:
        ignore_files.extend(args.i.split(","))
    if args.I:
        ignore_dirs.extend(args.I.split(","))
    dir_path = args.dir_path
    zip_name = args.zip_name or os.path.basename(dir_path) + ".zip"
    if args.o:
        zip_name = os.path.join(args.o, os.path.basename(zip_name))

    zip(dir_path, zip_name, ignore_dirs=ignore_dirs, ignore_files=ignore_files)
