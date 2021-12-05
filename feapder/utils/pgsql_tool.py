# -*- coding: utf-8 -*-
"""
    	*************************** 
    	--------description-------- 
 	 @Date : 2021-12-05
 	 @Author: 沈瑞祥
     @contact: ruixiang.shen@outlook.com
 	 @LastEditTime: 2021-12-05 12:52
 	 @FilePath: feapder/utils/pgsql_tool.py
     @Project: feapder

    	***************************
"""
from feapder.utils.tools import list2str, format_sql_value


# PostgreSQL数据库相关
def get_indexes_col_sql(table):
    """
    @summary: 适用于PostgreSQL
    ---------
    @param table:

    ---------
    @result:
    """
    sql = """
    select column_names from(
        select
            t.relname as table_name,
            i.relname as index_name,
            array_to_string(array_agg(a.attname), ', ') as column_names
        from
            pg_class t,
            pg_class i,
            pg_index ix,
            pg_attribute a
        where
            t.oid = ix.indrelid
            and i.oid = ix.indexrelid
            and a.attrelid = t.oid
            and a.attnum = ANY(ix.indkey)
            and t.relkind = 'r'
            and t.relname like '%'
        group by
            t.relname,
            i.relname
        order by
            t.relname,
            i.relname) as res
    where table_name = '{table}';
    """
    sql = sql.format(table=table).replace("None", "null")
    return sql


def get_constraint_name_sql(table):
    """
    @summary: 适用于PostgreSQL
    ---------
    @param table:tablename
    ---------
    @result:
    """
    sql = "SELECT indexname FROM pg_indexes WHERE tablename = '{table}'"
    sql = sql.format(table=table).replace("None", "null")
    return sql


def make_insert_sql(
    table, data, auto_update=False, update_columns=(), insert_ignore=False, indexes_cols=()
):
    """
    @summary: 适用于PostgreSQL
    ---------
    @param table:
    @param data: 表数据 json格式
    @param auto_update: 使用的是replace into， 为完全覆盖已存在的数据
    @param update_columns: 需要更新的列 默认全部，当指定值时，auto_update设置无效，当duplicate key冲突时更新指定的列
    @param insert_ignore: 数据存在忽略
    @param indexes_cols: 索引列
    ---------
    @result:
    """

    keys = ["{}".format(key) for key in data.keys()]
    keys = list2str(keys).replace("'", "")

    values = [format_sql_value(value) for value in data.values()]
    values = list2str(values)

    if update_columns:
        if not isinstance(update_columns, (tuple, list)):
            update_columns = [update_columns]
        update_columns_ = ", ".join(
            ["{key}=excluded.{key}".format(key=key) for key in update_columns]
        )
        sql = (
            "insert into {table} {keys} values {values} on conflict({indexes_cols}) DO UPDATE SET %s"
            % update_columns_
        )

    elif auto_update:
        update_all_columns_ = ", ".join(
            ["{key}=excluded.{key}".format(key=key) for key in keys]
        )
        sql = "insert into {table} {keys} values {values} on conflict({indexes_cols}) DO UPDATE SET %s" % update_all_columns_
    else:
        sql = "insert into {table} {keys} values {values} on conflict({indexes_cols}) DO NOTHING"

    sql = sql.format(table=table, keys=keys, values=values, indexes_cols=indexes_cols).replace("None", "null")
    return sql


def make_update_sql(table, data, condition):
    """
    @summary: 适用于PostgreSQL
    ---------
    @param table:
    @param data: 表数据 json格式
    @param condition: where 条件
    ---------
    @result:
    """
    key_values = []

    for key, value in data.items():
        value = format_sql_value(value)
        if isinstance(value, str):
            key_values.append("{}={}".format(key, repr(value)))
        elif value is None:
            key_values.append("{}={}".format(key, "null"))
        else:
            key_values.append("{}={}".format(key, value))

    key_values = ", ".join(key_values)

    sql = "update {table} set {key_values} where {condition}"
    sql = sql.format(table=table, key_values=key_values, condition=condition)
    return sql


def make_batch_sql(
    table, datas, auto_update=False, update_columns=(), update_columns_value=(), indexes_cols=()
):
    """
    @summary: 生产批量的sql
    ---------
    @param table:
    @param datas: 表数据 [{...}]
    @param auto_update: 使用的是replace into， 为完全覆盖已存在的数据
    @param update_columns: 需要更新的列 默认全部，当指定值时，auto_update设置无效，当duplicate key冲突时更新指定的列
    @param update_columns_value: 需要更新的列的值 默认为datas里边对应的值, 注意 如果值为字符串类型 需要主动加单引号， 如 update_columns_value=("'test'",)
    @param indexes_cols: 索引列 str
    ---------
    @result:
    """
    if not datas:
        return

    keys = list(datas[0].keys())
    values_placeholder = ["%s"] * len(keys)

    values = []
    for data in datas:
        value = []
        for key in keys:
            current_data = data.get(key)
            current_data = format_sql_value(current_data)

            value.append(current_data)

        values.append(value)

    keys = ["{}".format(key) for key in keys]
    keys = list2str(keys).replace("'", "")

    values_placeholder = list2str(values_placeholder).replace("'", "")

    if update_columns:
        if not isinstance(update_columns, (tuple, list)):
            update_columns = [update_columns]
        if update_columns_value:
            update_columns_ = ", ".join(
                [
                    "{key}=excluded.{value}".format(key=key, value=value)
                    for key, value in zip(update_columns, update_columns_value)
                ]
            )
        else:
            update_columns_ = ", ".join(
                ["{key}=excluded.{key}".format(key=key) for key in update_columns]
            )
        sql = "insert into {table} {keys} values {values_placeholder} ON CONFLICT({indexes_cols}) DO UPDATE SET {update_columns}".format(
            table=table,
            keys=keys,
            values_placeholder=values_placeholder,
            update_columns=update_columns_,
            indexes_cols=indexes_cols
        )
    elif auto_update:
        update_all_columns_ = ", ".join(
            ["{key}=excluded.{key}".format(key=key) for key in keys]
        )
        sql = "insert into {table} {keys} values {values_placeholder} on conflict({indexes_cols}) DO UPDATE SET {update_all_columns_}".format(
            table=table, keys=keys, values_placeholder=values_placeholder, indexes_cols=indexes_cols, update_all_columns_=update_all_columns_
        )
    else:
        sql = "insert into {table} {keys} values {values_placeholder} on conflict({indexes_cols}) do nothing".format(
            table=table, keys=keys, values_placeholder=values_placeholder, indexes_cols=indexes_cols
        )

    return sql, values
