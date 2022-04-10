# -*- coding: utf-8 -*-
"""
Created on 2018-08-28 17:38:43
---------
@summary: 创建项目
---------
@author: Boris
@email:  boris_liu@foxmail.com
"""

import getpass
import os
import shutil

import feapder.utils.tools as tools


def deal_file_info(file):
    file = file.replace("{DATE}", tools.get_current_date())
    file = file.replace("{USER}", os.getenv("FEAPDER_USER") or getpass.getuser())

    return file


class CreateProject:
    def copy_callback(self, src, dst, *, follow_symlinks=True):
        if src.endswith(".py"):
            with open(src, "r", encoding="utf-8") as src_file, open(
                dst, "w", encoding="utf8"
            ) as dst_file:
                content = src_file.read()
                content = deal_file_info(content)
                dst_file.write(content)

        else:
            shutil.copy2(src, dst, follow_symlinks=follow_symlinks)

    def create(self, project_name):
        if os.path.exists(project_name):
            print("%s 项目已经存在" % project_name)
        else:
            template_path = os.path.abspath(
                os.path.join(__file__, "../../../templates/project_template")
            )
            shutil.copytree(
                template_path, project_name, copy_function=self.copy_callback
            )

            print("\n%s 项目生成成功" % project_name)



