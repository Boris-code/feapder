# -*- coding: utf-8 -*-
"""
    	*************************** 
    	--------description-------- 
 	 @Date : 2021-12-04
 	 @Author: 沈瑞祥
     @contact: ruixiang.shen@outlook.com
 	 @LastEditTime: 2021-12-04 17:15
 	 @FilePath: tests/test_pgsqldb.py
     @Project: feapder

    	***************************
"""
from feapder.db.pgsqldb import PgsqlDB


db = PgsqlDB(
    ip="localhost", port=5432, db="postgres", user_name="postgres", user_pass="Srx20130126."
)

# postgresql://user_name:user_passwd@ip:port/db?charset=utf8
PgsqlDB.from_url("postgresql://postgres:Srx20130126.@localhost:5432/postgres?charset=utf8")