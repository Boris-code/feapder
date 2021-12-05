# -*- coding: utf-8 -*-
"""
    	*************************** 
    	--------description-------- 
 	 @Date : 2021-12-04
 	 @Author: 沈瑞祥
     @contact: ruixiang.shen@outlook.com
 	 @LastEditTime: 2021-12-04 14:42
 	 @FilePath: feapder/db/pgsqldb.py
     @Project: feapder

    	***************************
"""
import datetime
import json
from urllib import parse
from typing import List, Dict

import psycopg2
from dbutils.pooled_db import PooledDB

import feapder.setting as setting
from feapder.utils.log import log
from feapder.utils.pgsql_tool import make_insert_sql, make_update_sql, make_batch_sql


def auto_retry(func):
    def wapper(*args, **kwargs):
        for i in range(3):
            try:
                return func(*args, **kwargs)
            except (psycopg2.Error.InterfaceError, psycopg2.Error.OperationalError) as e:
                log.error(
                    """
                    error:%s
                    sql:  %s
                    """
                    % (e, kwargs.get("sql") or args[1])
                )

    return wapper


class PgsqlDB:
    def __init__(
        self, ip=None, port=None, db=None, user_name=None, user_pass=None, **kwargs
    ):
        # 可能会改setting中的值，所以此处不能直接赋值为默认值，需要后加载赋值
        if not ip:
            ip = setting.PGSQL_IP
        if not port:
            port = setting.PGSQL_PORT
        if not db:
            db = setting.PGSQL_DB
        if not user_name:
            user_name = setting.PGSQL_USER_NAME
        if not user_pass:
            user_pass = setting.PGSQL_USER_PASS

        try:
            log.debug(
                "Begin to create {0} postgresql pool on：{1}.\n".format(
                    ip, datetime.datetime.now()
                )
            )
            self.connect_pool = PooledDB(
                creator=psycopg2,
                mincached=1,
                maxcached=100,
                maxconnections=100,
                blocking=True,
                ping=7,
                host=ip,
                port=port,
                user=user_name,
                password=user_pass,
                database=db,
            )

        except Exception as e:
            log.error(
                """
            连接数据失败：
            ip: {}
            port: {}
            db: {}
            user_name: {}
            user_pass: {}
            exception: {}
            """.format(
                    ip, port, db, user_name, user_pass, e
                )
            )
        else:
            log.debug("成功连接到postgresql数据库 %s : %s" % (ip, db))

    @classmethod
    def from_url(cls, url, **kwargs):
        # postgresql://user_name:user_passwd@ip:port/db?charset=utf8
        url_parsed = parse.urlparse(url)

        db_type = url_parsed.scheme.strip()
        if db_type != "postgresql":
            raise Exception(
                "url error, expect postgresql://username:ip:port/db?charset=utf8, but get {}".format(
                    url
                )
            )

        connect_params = {"ip": url_parsed.hostname.strip(), "port": url_parsed.port,
                          "user_name": url_parsed.username.strip(), "user_pass": url_parsed.password.strip(),
                          "db": url_parsed.path.strip("/").strip()}

        connect_params.update(kwargs)

        return cls(**connect_params)

    @staticmethod
    def unescape_string(value):
        if not isinstance(value, str):
            return value

        value = value.replace("\\0", "\0")
        value = value.replace("\\\\", "\\")
        value = value.replace("\\n", "\n")
        value = value.replace("\\r", "\r")
        value = value.replace("\\Z", "\032")
        value = value.replace('\\"', '"')
        value = value.replace("\\'", "'")

        return value

    def get_connection(self):
        conn = self.connect_pool.connection(shareable=False)
        # cursor = conn.cursor(cursors.SSCursor)
        cursor = conn.cursor()

        return conn, cursor

    def close_connection(self, conn, cursor):
        cursor.close()
        conn.close()

    def size_of_connections(self):
        """
        当前活跃的连接数
        @return:
        """
        return self.connect_pool._connections

    def size_of_connect_pool(self):
        """
        池子里一共有多少连接
        @return:
        """
        return len(self.connect_pool._idle_cache)

    @auto_retry
    def find(self, sql, limit=0, to_json=False):
        """
        @summary:
        无数据： 返回()
        有数据： 若limit == 1 则返回 (data1, data2)
                否则返回 ((data1, data2),)
        ---------
        @param sql:
        @param limit:
        @param to_json 是否将查询结果转为json
        ---------
        @result:
        """
        conn, cursor = self.get_connection()

        cursor.execute(sql)

        if limit == 1:
            result = cursor.fetchone()  # 全部查出来，截取 不推荐使用
        elif limit > 1:
            result = cursor.fetchmany(limit)  # 全部查出来，截取 不推荐使用
        else:
            result = cursor.fetchall()

        if to_json:
            columns = [i[0] for i in cursor.description]

            # 处理数据
            def convert(col):
                if isinstance(col, (datetime.date, datetime.time)):
                    return str(col)
                elif isinstance(col, str) and (
                    col.startswith("{") or col.startswith("[")
                ):
                    try:
                        # col = self.unescape_string(col)
                        return json.loads(col)
                    except:
                        return col
                else:
                    # col = self.unescape_string(col)
                    return col

            if limit == 1:
                result = [convert(col) for col in result]
                result = dict(zip(columns, result))
            else:
                result = [[convert(col) for col in row] for row in result]
                result = [dict(zip(columns, r)) for r in result]

        self.close_connection(conn, cursor)

        return result

    def add(self, sql, exception_callfunc=None):
        """

        Args:
            sql:
            exception_callfunc: 异常回调

        Returns: 添加行数

        """
        affect_count = None

        try:
            conn, cursor = self.get_connection()
            affect_count = cursor.execute(sql)
            conn.commit()

        except Exception as e:
            log.error(
                """
                error:%s
                sql:  %s
            """
                % (e, sql)
            )
            if exception_callfunc:
                exception_callfunc(e)
        finally:
            self.close_connection(conn, cursor)

        return affect_count

    def add_smart(self, table, data: Dict, **kwargs):
        """
        添加数据, 直接传递json格式的数据，不用拼sql
        Args:
            table: 表名
            data: 字典 {"xxx":"xxx"}
            **kwargs:

        Returns: 添加行数

        """
        sql = make_insert_sql(table, data, **kwargs)
        return self.add(sql)

    def add_batch(self, sql, datas: List[Dict]):
        """
        @summary: 批量添加数据
        ---------
        @ param sql: insert into (xxx,xxx) values (%s, %s, %s)
        # param datas: 列表 [{}, {}, {}]
        ---------
        @result: 添加行数
        """
        affect_count = None

        try:
            conn, cursor = self.get_connection()
            cursor.executemany(sql, datas)
            affect_count = cursor.rowcount
            conn.commit()

        except Exception as e:
            log.error(
                """
                error:%s
                sql:  %s
                """
                % (e, sql)
            )
        finally:
            self.close_connection(conn, cursor)

        return affect_count

    def add_batch_smart(self, table, datas: List[Dict], **kwargs):
        """
        批量添加数据, 直接传递list格式的数据，不用拼sql
        Args:
            table: 表名
            datas: 列表 [{}, {}, {}]
            **kwargs:

        Returns: 添加行数

        """
        sql, datas = make_batch_sql(table, datas, **kwargs)
        return self.add_batch(sql, datas)

    def update(self, sql):
        try:
            conn, cursor = self.get_connection()
            cursor.execute(sql)
            conn.commit()

        except Exception as e:
            log.error(
                """
                error:%s
                sql:  %s
            """
                % (e, sql)
            )
            return False
        else:
            return True
        finally:
            self.close_connection(conn, cursor)

    def update_smart(self, table, data: Dict, condition):
        """
        更新, 不用拼sql
        Args:
            table: 表名
            data: 数据 {"xxx":"xxx"}
            condition: 更新条件 where后面的条件，如 condition='status=1'

        Returns: True / False

        """
        sql = make_update_sql(table, data, condition)
        return self.update(sql)

    def delete(self, sql):
        """
        删除
        Args:
            sql:

        Returns: True / False

        """
        try:
            conn, cursor = self.get_connection()
            cursor.execute(sql)
            conn.commit()

        except Exception as e:
            log.error(
                """
                error:%s
                sql:  %s
            """
                % (e, sql)
            )
            return False
        else:
            return True
        finally:
            self.close_connection(conn, cursor)

    def execute(self, sql):
        try:
            conn, cursor = self.get_connection()
            cursor.execute(sql)
            conn.commit()

        except Exception as e:
            log.error(
                """
                error:%s
                sql:  %s
            """
                % (e, sql)
            )
            return False
        else:
            return True
        finally:
            self.close_connection(conn, cursor)
