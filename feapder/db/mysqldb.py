# -*- coding: utf-8 -*-
"""
Created on 2016-11-16 16:25
---------
@summary: 操作mysql数据库
---------
@author: Boris
@email: boris_liu@foxmail.com
"""
import datetime
import json
from urllib import parse
from typing import List, Dict

import pymysql
from dbutils.pooled_db import PooledDB
from pymysql import cursors
from pymysql import err

import feapder.setting as setting
from feapder.utils.log import log
from feapder.utils.tools import make_insert_sql, make_batch_sql, make_update_sql


def auto_retry(func):
    def wapper(*args, **kwargs):
        for i in range(3):
            try:
                return func(*args, **kwargs)
            except (err.InterfaceError, err.OperationalError) as e:
                log.error(
                    """
                    error:%s
                    sql:  %s
                    """
                    % (e, kwargs.get("sql") or args[1])
                )

    return wapper


class MysqlDB:
    def __init__(
        self, ip=None, port=None, db=None, user_name=None, user_pass=None, **kwargs
    ):
        # 可能会改setting中的值，所以此处不能直接赋值为默认值，需要后加载赋值
        if not ip:
            ip = setting.MYSQL_IP
        if not port:
            port = setting.MYSQL_PORT
        if not db:
            db = setting.MYSQL_DB
        if not user_name:
            user_name = setting.MYSQL_USER_NAME
        if not user_pass:
            user_pass = setting.MYSQL_USER_PASS

        try:
            self.connect_pool = PooledDB(
                creator=pymysql,
                mincached=1,
                maxcached=100,
                maxconnections=100,
                blocking=True,
                ping=7,
                host=ip,
                port=port,
                user=user_name,
                passwd=user_pass,
                db=db,
                charset="utf8mb4",
                cursorclass=cursors.SSCursor,
            )  # cursorclass 使用服务的游标，默认的在多线程下大批量插入数据会使内存递增

        except Exception as e:
            log.error(
                """
            连接失败：
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
            log.debug("连接到mysql数据库 %s : %s" % (ip, db))

    @classmethod
    def from_url(cls, url, **kwargs):
        """

        Args:
            url: mysql://username:password@ip:port/db?charset=utf8mb4
            **kwargs:

        Returns:

        """
        url_parsed = parse.urlparse(url)

        db_type = url_parsed.scheme.strip()
        if db_type != "mysql":
            raise Exception(
                "url error, expect mysql://username:ip:port/db?charset=utf8mb4, but get {}".format(
                    url
                )
            )

        connect_params = {
            "ip": url_parsed.hostname.strip(),
            "port": url_parsed.port,
            "user_name": url_parsed.username.strip(),
            "user_pass": url_parsed.password.strip(),
            "db": url_parsed.path.strip("/").strip(),
        }

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
        if conn:
            conn.close()
        if cursor:
            cursor.close()

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
    def find(self, sql, limit=0, to_json=False, conver_col=True):
        """
        @summary:
        无数据： 返回()
        有数据： 若limit == 1 则返回 (data1, data2)
                否则返回 ((data1, data2),)
        ---------
        @param sql:
        @param limit:
        @param to_json 是否将查询结果转为json
        @param conver_col 是否处理查询结果，如date类型转字符串，json字符串转成json。仅当to_json=True时生效
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
                if conver_col:
                    result = [convert(col) for col in result]
                result = dict(zip(columns, result))
            else:
                if conver_col:
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
        conn, cursor = None, None

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
        @ param sql: insert ignore into (xxx,xxx) values (%s, %s, %s)
        # param datas: 列表 [{}, {}, {}]
        ---------
        @result: 添加行数
        """
        affect_count = None
        conn, cursor = None, None

        try:
            conn, cursor = self.get_connection()
            affect_count = cursor.executemany(sql, datas)
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
        conn, cursor = None, None

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
        conn, cursor = None, None
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
        conn, cursor = None, None
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
