# -*- coding: utf-8 -*-
"""
Created on 2016-11-16 16:25
---------
@summary: 操作oracle数据库
---------
@author: Boris
@email: boris@bzkj.tech
"""
import datetime
import json
from urllib import parse

import pymysql
from DBUtils.PooledDB import PooledDB
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
            log.debug("连接到mysql数据库 %s : %s" % (ip, db))

    @classmethod
    def from_url(cls, url, **kwargs):
        # mysql://username:ip:port/db?charset=utf8mb4
        url_parsed = parse.urlparse(url)

        db_type = url_parsed.scheme.strip()
        if db_type != "mysql":
            raise Exception(
                "url error, expect mysql://username:ip:port/db?charset=utf8mb4, but get {}".format(
                    url
                )
            )

        connect_params = {}
        connect_params["ip"] = url_parsed.hostname.strip()
        connect_params["port"] = url_parsed.port
        connect_params["user_name"] = url_parsed.username.strip()
        connect_params["user_pass"] = url_parsed.password.strip()
        connect_params["db"] = url_parsed.path.strip("/").strip()

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
    def find(self, sql, limit=0, to_json=False, cursor=None):
        """
        @summary:
        无数据： 返回()
        有数据： 若limit == 1 则返回 (data1, data2)
                否则返回 ((data1, data2),)
        ---------
        @param sql:
        @param limit:
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
            def fix_lob(row):
                def convert(col):
                    if isinstance(col, (datetime.date, datetime.time)):
                        return str(col)
                    elif isinstance(col, str) and (
                        col.startswith("{") or col.startswith("[")
                    ):
                        try:
                            col = self.unescape_string(col)
                            return json.loads(col)
                        except:
                            return col
                    else:
                        col = self.unescape_string(col)
                        return col

                return [convert(c) for c in row]

            result = [fix_lob(row) for row in result]
            result = [dict(zip(columns, r)) for r in result]

        self.close_connection(conn, cursor)

        return result

    def add(self, sql, exception_callfunc=""):
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

    def add2(self, table, data, **kwargs):
        sql = make_insert_sql(table, data, **kwargs)
        return self.add(sql)

    def add_batch(self, sql, datas):
        """
        @summary:
        ---------
        @ param sql: insert ignore into (xxx,xxx) values (%s, %s, %s)
        # param datas:[[..], [...]]
        ---------
        @result:
        """
        affect_count = None

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

    def add_batch2(self, table, datas, **kwargs):
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

    def update2(self, table, data, condition):
        sql = make_update_sql(table, data, condition)
        return self.update(sql)

    def delete(self, sql):
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

    def set_unique_key(self, table, key):
        try:
            sql = "alter table %s add unique (%s)" % (table, key)

            conn, cursor = self.get_connection()
            cursor.execute(sql)
            conn.commit()

        except Exception as e:
            log.error(table + " " + str(e) + " key = " + key)
            return False
        else:
            log.debug("%s表创建唯一索引成功 索引为 %s" % (table, key))
            return True
        finally:
            self.close_connection(conn, cursor)
