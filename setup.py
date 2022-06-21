# -*- coding: utf-8 -*-
"""
Created on 2020/4/22 10:45 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from os.path import dirname, join
from sys import version_info

import setuptools

if version_info < (3, 6, 0):
    raise SystemExit("Sorry! feapder requires python 3.6.0 or later.")

with open(join(dirname(__file__), "feapder/VERSION"), "rb") as fh:
    version = fh.read().decode("ascii").strip()

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("slogan.txt", "r") as fh:
    slogan = fh.read()

packages = setuptools.find_packages()
packages.extend(
    [
        "feapder",
        "feapder.templates",
        "feapder.templates.project_template",
        "feapder.templates.project_template.spiders",
        "feapder.templates.project_template.items",
    ]
)

requires = [
    "better-exceptions>=0.2.2",
    "DBUtils>=2.0",
    "parsel>=1.5.2",
    "PyMySQL>=0.9.3",
    "redis>=2.10.6,<4.0.0",
    "requests>=2.22.0",
    "bs4>=0.0.1",
    "ipython>=7.14.0",
    "redis-py-cluster>=2.1.0",
    "cryptography>=3.3.2",
    "selenium>=3.141.0",
    "pymongo>=3.10.1",
    "urllib3>=1.25.8",
    "loguru>=0.5.3",
    "influxdb>=5.3.1",
    "pyperclip>=1.8.2",
    "webdriver-manager>=3.5.3",
]

extras_requires = ["bitarray>=1.5.3", "PyExecJS>=1.5.1"]

setuptools.setup(
    name="feapder",
    version=version,
    author="Boris",
    license="MIT",
    author_email="feapder@qq.com",
    python_requires=">=3.6",
    description="feapder是一款支持分布式、批次采集、任务防丢、报警丰富的python爬虫框架",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=requires,
    extras_require={"all": extras_requires},
    entry_points={"console_scripts": ["feapder = feapder.commands.cmdline:execute"]},
    url="https://github.com/Boris-code/feapder.git",
    packages=packages,
    include_package_data=True,
    classifiers=["Programming Language :: Python :: 3"],
)

print("\n" + slogan)
