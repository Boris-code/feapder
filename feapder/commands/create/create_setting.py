# -*- coding: utf-8 -*-
"""
Created on 2021/4/23 13:20
---------
@summary: 生成配置文件
---------
@author: mkdir700
@email:  mkdir700@gmail.com
"""

import os
import shutil


class CreateSetting:
    
    def create(self):
        if os.path.exists('setting.py'):
            print("配置文件已存在")
        else:
            template_file_path = os.path.abspath(
                os.path.join(__file__, "../../../templates/project_template/setting.py")
            )
            shutil.copy2(template_file_path, './', follow_symlinks=False)
            print("配置文件生成成功")
            