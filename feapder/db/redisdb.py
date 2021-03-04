# -*- coding: utf-8 -*-
"""
Created on 2016-11-16 16:25
---------
@summary: 操作redis数据库
---------
@author: Boris
"""

import redis
from redis.sentinel import Sentinel
from rediscluster import RedisCluster

import feapder.setting as setting
from feapder.utils.log import log


class Singleton(object):
    def __init__(self, cls):
        self._cls = cls
        self._instance = {}

    def __call__(self, *args, **kwargs):
        if self._cls not in self._instance:
            self._instance[self._cls] = self._cls(*args, **kwargs)
        return self._instance[self._cls]


@Singleton
class RedisDB:
    def __init__(
        self,
        ip_ports=None,
        db=None,
        user_pass=None,
        url=None,
        decode_responses=True,
        service_name=None,
        max_connections=32,
        **kwargs
    ):
        """
        redis的封装
        Args:
            ip_ports: ip:port 多个可写为列表或者逗号隔开 如 ip1:port1,ip2:port2 或 ["ip1:port1", "ip2:port2"]
            db:
            user_pass:
            url:
            decode_responses:
            service_name: 适用于redis哨兵模式
        """

        # 可能会改setting中的值，所以此处不能直接赋值为默认值，需要后加载赋值
        if ip_ports is None:
            ip_ports = setting.REDISDB_IP_PORTS
        if db is None:
            db = setting.REDISDB_DB
        if user_pass is None:
            user_pass = setting.REDISDB_USER_PASS
        if service_name is None:
            service_name = setting.REDISDB_SERVICE_NAME

        self._is_redis_cluster = False

        try:
            if not url:
                ip_ports = (
                    ip_ports if isinstance(ip_ports, list) else ip_ports.split(",")
                )
                if len(ip_ports) > 1:
                    startup_nodes = []
                    for ip_port in ip_ports:
                        ip, port = ip_port.split(":")
                        startup_nodes.append({"host": ip, "port": port})

                    if service_name:
                        log.debug("使用redis哨兵模式")
                        hosts = [(node["host"], node["port"]) for node in startup_nodes]
                        sentinel = Sentinel(hosts, socket_timeout=3, **kwargs)
                        self._redis = sentinel.master_for(
                            service_name,
                            password=user_pass,
                            db=db,
                            redis_class=redis.StrictRedis,
                            decode_responses=decode_responses,
                            max_connections=max_connections,
                            **kwargs
                        )

                    else:
                        log.debug("使用redis集群模式")
                        self._redis = RedisCluster(
                            startup_nodes=startup_nodes,
                            decode_responses=decode_responses,
                            password=user_pass,
                            max_connections=max_connections,
                            **kwargs
                        )

                    self._is_redis_cluster = True
                else:
                    ip, port = ip_ports[0].split(":")
                    self._redis = redis.StrictRedis(
                        host=ip,
                        port=port,
                        db=db,
                        password=user_pass,
                        decode_responses=decode_responses,
                        max_connections=max_connections,
                        **kwargs
                    )
            else:
                self._redis = redis.StrictRedis.from_url(
                    url, decode_responses=decode_responses
                )

        except Exception as e:
            raise
        else:
            if not url:
                log.debug("连接到redis数据库 %s db%s" % (ip_ports, db))
            else:
                log.debug("连接到redis数据库 %s" % (url))

        self._ip_ports = ip_ports
        self._db = db
        self._user_pass = user_pass
        self._url = url

    def __repr__(self):
        if self._url:
            return "<Redisdb url:{}>".format(self._url)

        return "<Redisdb ip_ports: {} db:{} user_pass:{}>".format(
            self._ip_ports, self._db, self._user_pass
        )

    @classmethod
    def from_url(cls, url):
        return cls(url=url)

    def sadd(self, table, values):
        """
        @summary: 使用无序set集合存储数据， 去重
        ---------
        @param table:
        @param values: 值； 支持list 或 单个值
        ---------
        @result: 若库中存在 返回0，否则入库，返回1。 批量添加返回None
        """

        if isinstance(values, list):
            pipe = self._redis.pipeline(
                transaction=True
            )  # redis-py默认在执行每次请求都会创建（连接池申请连接）和断开（归还连接池）一次连接操作，如果想要在一次请求中指定多个命令，则可以使用pipline实现一次请求指定多个命令，并且默认情况下一次pipline 是原子性操作。

            if not self._is_redis_cluster:
                pipe.multi()
            for value in values:
                pipe.sadd(table, value)
            pipe.execute()

        else:
            return self._redis.sadd(table, values)

    def sget(self, table, count=1, is_pop=True):
        """
        返回 list 如 ['1'] 或 []
        @param table:
        @param count:
        @param is_pop:
        @return:
        """
        datas = []
        if is_pop:
            count = count if count <= self.sget_count(table) else self.sget_count(table)
            if count:
                if count > 1:
                    pipe = self._redis.pipeline(
                        transaction=True
                    )  # redis-py默认在执行每次请求都会创建（连接池申请连接）和断开（归还连接池）一次连接操作，如果想要在一次请求中指定多个命令，则可以使用pipline实现一次请求指定多个命令，并且默认情况下一次pipline 是原子性操作。

                    if not self._is_redis_cluster:
                        pipe.multi()
                    while count:
                        pipe.spop(table)
                        count -= 1
                    datas = pipe.execute()

                else:
                    datas.append(self._redis.spop(table))

        else:
            datas = self._redis.srandmember(table, count)

        return datas

    def srem(self, table, values):
        """
        @summary: 移除集合中的指定元素
        ---------
        @param table:
        @param values: 一个或者列表
        ---------
        @result:
        """
        if isinstance(values, list):
            pipe = self._redis.pipeline(
                transaction=True
            )  # redis-py默认在执行每次请求都会创建（连接池申请连接）和断开（归还连接池）一次连接操作，如果想要在一次请求中指定多个命令，则可以使用pipline实现一次请求指定多个命令，并且默认情况下一次pipline 是原子性操作。

            if not self._is_redis_cluster:
                pipe.multi()
            for value in values:
                pipe.srem(table, value)
            pipe.execute()
        else:
            self._redis.srem(table, values)

    def sget_count(self, table):
        return self._redis.scard(table)

    def sdelete(self, table):
        """
        @summary: 删除set集合的大键（数据量大的表）
        删除大set键，使用sscan命令，每次扫描集合中500个元素，再用srem命令每次删除一个键
        若直接用delete命令，会导致Redis阻塞，出现故障切换和应用程序崩溃的故障。
        ---------
        @param table:
        ---------
        @result:
        """
        # 当 SCAN 命令的游标参数被设置为 0 时， 服务器将开始一次新的迭代， 而当服务器向用户返回值为 0 的游标时， 表示迭代已结束
        cursor = "0"
        while cursor != 0:
            cursor, data = self._redis.sscan(table, cursor=cursor, count=500)
            for item in data:
                # pipe.srem(table, item)
                self._redis.srem(table, item)

            # pipe.execute()

    def sismember(self, table, key):
        "Return a boolean indicating if ``value`` is a member of set ``name``"
        return self._redis.sismember(table, key)

    def zadd(self, table, values, prioritys=0):
        """
        @summary: 使用有序set集合存储数据， 去重(值存在更新)
        ---------
        @param table:
        @param values: 值； 支持list 或 单个值
        @param prioritys: 优先级； double类型，支持list 或 单个值。 根据此字段的值来排序, 值越小越优先。 可不传值，默认value的优先级为0
        ---------
        @result:若库中存在 返回0，否则入库，返回1。 批量添加返回 [0, 1 ...]
        """
        if isinstance(values, list):
            if not isinstance(prioritys, list):
                prioritys = [prioritys] * len(values)
            else:
                assert len(values) == len(prioritys), "values值要与prioritys值一一对应"

            pipe = self._redis.pipeline(transaction=True)

            if not self._is_redis_cluster:
                pipe.multi()
            for value, priority in zip(values, prioritys):
                pipe.execute_command(
                    "ZADD", table, priority, value
                )  # 为了兼容2.x与3.x版本的redis
            return pipe.execute()

        else:
            return self._redis.execute_command(
                "ZADD", table, prioritys, values
            )  # 为了兼容2.x与3.x版本的redis

    def zget(self, table, count=1, is_pop=True):
        """
        @summary: 从有序set集合中获取数据 优先返回分数小的（优先级高的）
        ---------
        @param table:
        @param count: 数量 -1 返回全部数据
        @param is_pop:获取数据后，是否在原set集合中删除，默认是
        ---------
        @result: 列表
        """
        start_pos = 0  # 包含
        end_pos = count - 1 if count > 0 else count

        pipe = self._redis.pipeline(
            transaction=True
        )  # redis-py默认在执行每次请求都会创建（连接池申请连接）和断开（归还连接池）一次连接操作，如果想要在一次请求中指定多个命令，则可以使用pipline实现一次请求指定多个命令，并且默认情况下一次pipline 是原子性操作。

        if not self._is_redis_cluster:
            pipe.multi()  # 标记事务的开始 参考 http://www.runoob.com/redis/redis-transactions.html
        pipe.zrange(table, start_pos, end_pos)  # 取值
        if is_pop:
            pipe.zremrangebyrank(table, start_pos, end_pos)  # 删除
        results, *count = pipe.execute()
        return results

    def zremrangebyscore(self, table, priority_min, priority_max):
        """
        根据分数移除成员 闭区间
        @param table:
        @param priority_min:
        @param priority_max:
        @return: 被移除的成员个数
        """
        return self._redis.zremrangebyscore(table, priority_min, priority_max)

    def zrangebyscore(self, table, priority_min, priority_max, count=None, is_pop=True):
        """
        @summary: 返回指定分数区间的数据 闭区间
        ---------
        @param table:
        @param priority_min: 优先级越小越优先
        @param priority_max:
        @param count: 获取的数量，为空则表示分数区间内的全部数据
        @param is_pop: 是否删除
        ---------
        @result:
        """

        # 使用lua脚本， 保证操作的原子性
        lua = """
            local key = KEYS[1]
            local min_score = ARGV[2]
            local max_score = ARGV[3]
            local is_pop = ARGV[4]
            local count = ARGV[5]

            -- 取值
            local datas = nil
            if count then
                datas = redis.call('zrangebyscore', key, min_score, max_score, 'limit', 0, count)
            else
                datas = redis.call('zrangebyscore', key, min_score, max_score)
            end

            -- 删除redis中刚取到的值
            if (is_pop) then
                for i=1, #datas do
                    redis.call('zrem', key, datas[i])
                end
            end


            return datas

        """
        cmd = self._redis.register_script(lua)
        if count:
            res = cmd(
                keys=[table], args=[table, priority_min, priority_max, is_pop, count]
            )
        else:
            res = cmd(keys=[table], args=[table, priority_min, priority_max, is_pop])

        return res

    def zrangebyscore_increase_score(
        self, table, priority_min, priority_max, increase_score, count=None
    ):
        """
        @summary: 返回指定分数区间的数据 闭区间， 同时修改分数
        ---------
        @param table:
        @param priority_min: 最小分数
        @param priority_max: 最大分数
        @param increase_score: 分数值增量 正数则在原有的分数上叠加，负数则相减
        @param count: 获取的数量，为空则表示分数区间内的全部数据
        ---------
        @result:
        """

        # 使用lua脚本， 保证操作的原子性
        lua = """
            local key = KEYS[1]
            local min_score = ARGV[1]
            local max_score = ARGV[2]
            local increase_score = ARGV[3]
            local count = ARGV[4]

            -- 取值
            local datas = nil
            if count then
                datas = redis.call('zrangebyscore', key, min_score, max_score, 'limit', 0, count)
            else
                datas = redis.call('zrangebyscore', key, min_score, max_score)
            end

            --修改优先级
            for i=1, #datas do
                redis.call('zincrby', key, increase_score, datas[i])
            end

            return datas

        """
        cmd = self._redis.register_script(lua)
        if count:
            res = cmd(
                keys=[table], args=[priority_min, priority_max, increase_score, count]
            )
        else:
            res = cmd(keys=[table], args=[priority_min, priority_max, increase_score])

        return res

    def zrangebyscore_set_score(
        self, table, priority_min, priority_max, score, count=None
    ):
        """
        @summary: 返回指定分数区间的数据 闭区间， 同时修改分数
        ---------
        @param table:
        @param priority_min: 最小分数
        @param priority_max: 最大分数
        @param score: 分数值
        @param count: 获取的数量，为空则表示分数区间内的全部数据
        ---------
        @result:
        """

        # 使用lua脚本， 保证操作的原子性
        lua = """
            local key = KEYS[1]
            local min_score = ARGV[1]
            local max_score = ARGV[2]
            local set_score = ARGV[3]
            local count = ARGV[4]

            -- 取值
            local datas = nil
            if count then
                datas = redis.call('zrangebyscore', key, min_score, max_score, 'withscores','limit', 0, count)
            else
                datas = redis.call('zrangebyscore', key, min_score, max_score, 'withscores')
            end

            local real_datas = {} -- 数据
            --修改优先级
            for i=1, #datas, 2 do
               local data = datas[i]
               local score = datas[i+1]

               table.insert(real_datas, data) -- 添加数据

               redis.call('zincrby', key, set_score - score, datas[i])
            end

            return real_datas

        """
        cmd = self._redis.register_script(lua)
        if count:
            res = cmd(keys=[table], args=[priority_min, priority_max, score, count])
        else:
            res = cmd(keys=[table], args=[priority_min, priority_max, score])

        return res

    def zget_count(self, table, priority_min=None, priority_max=None):
        """
        @summary: 获取表数据的数量
        ---------
        @param table:
        @param priority_min:优先级范围 最小值（包含）
        @param priority_max:优先级范围 最大值（包含）
        ---------
        @result:
        """

        if priority_min != None and priority_max != None:
            return self._redis.zcount(table, priority_min, priority_max)
        else:
            return self._redis.zcard(table)

    def zrem(self, table, values):
        """
        @summary: 移除集合中的指定元素
        ---------
        @param table:
        @param values: 一个或者列表
        ---------
        @result:
        """
        if isinstance(values, list):
            pipe = self._redis.pipeline(
                transaction=True
            )  # redis-py默认在执行每次请求都会创建（连接池申请连接）和断开（归还连接池）一次连接操作，如果想要在一次请求中指定多个命令，则可以使用pipline实现一次请求指定多个命令，并且默认情况下一次pipline 是原子性操作。

            if not self._is_redis_cluster:
                pipe.multi()
            for value in values:
                pipe.zrem(table, value)
            pipe.execute()
        else:
            self._redis.zrem(table, values)

    def zexists(self, table, values):
        """
        利用zscore判断某元素是否存在
        @param values:
        @return:
        """
        is_exists = []

        if isinstance(values, list):
            pipe = self._redis.pipeline(
                transaction=True
            )  # redis-py默认在执行每次请求都会创建（连接池申请连接）和断开（归还连接池）一次连接操作，如果想要在一次请求中指定多个命令，则可以使用pipline实现一次请求指定多个命令，并且默认情况下一次pipline 是原子性操作。
            pipe.multi()
            for value in values:
                pipe.zscore(table, value)
            is_exists_temp = pipe.execute()
            for is_exist in is_exists_temp:
                if is_exist != None:
                    is_exists.append(1)
                else:
                    is_exists.append(0)

        else:
            is_exists = self._redis.zscore(table, values)
            is_exists = 1 if is_exists != None else 0

        return is_exists

    def lpush(self, table, values):
        if isinstance(values, list):
            pipe = self._redis.pipeline(
                transaction=True
            )  # redis-py默认在执行每次请求都会创建（连接池申请连接）和断开（归还连接池）一次连接操作，如果想要在一次请求中指定多个命令，则可以使用pipline实现一次请求指定多个命令，并且默认情况下一次pipline 是原子性操作。

            if not self._is_redis_cluster:
                pipe.multi()
            for value in values:
                pipe.rpush(table, value)
            pipe.execute()

        else:
            return self._redis.rpush(table, values)

    def lpop(self, table, count=1):
        """
        @summary:
        ---------
        @param table:
        @param count:
        ---------
        @result: count>1时返回列表
        """
        datas = None

        count = count if count <= self.lget_count(table) else self.lget_count(table)

        if count:
            if count > 1:
                pipe = self._redis.pipeline(
                    transaction=True
                )  # redis-py默认在执行每次请求都会创建（连接池申请连接）和断开（归还连接池）一次连接操作，如果想要在一次请求中指定多个命令，则可以使用pipline实现一次请求指定多个命令，并且默认情况下一次pipline 是原子性操作。

                if not self._is_redis_cluster:
                    pipe.multi()
                while count:
                    pipe.lpop(table)
                    count -= 1
                datas = pipe.execute()

            else:
                datas = self._redis.lpop(table)

        return datas

    def rpoplpush(self, from_table, to_table=None):
        """
        将列表 from_table 中的最后一个元素(尾元素)弹出，并返回给客户端。
        将 from_table 弹出的元素插入到列表 to_table ，作为 to_table 列表的的头元素。
        如果 from_table 和 to_table 相同，则列表中的表尾元素被移动到表头，并返回该元素，可以把这种特殊情况视作列表的旋转(rotation)操作
        @param from_table:
        @param to_table:
        @return:
        """

        if not to_table:
            to_table = from_table

        return self._redis.rpoplpush(from_table, to_table)

    def lget_count(self, table):
        return self._redis.llen(table)

    def lrem(self, table, value, num=0):
        return self._redis.lrem(table, num, value)

    def hset(self, table, key, value):
        """
        @summary:
        如果 key 不存在，一个新的哈希表被创建并进行 HSET 操作。
        如果域 field 已经存在于哈希表中，旧值将被覆盖
        ---------
        @param table:
        @param key:
        @param value:
        ---------
        @result: 1 新插入； 0 覆盖
        """

        return self._redis.hset(table, key, value)

    def hset_batch(self, table, datas):
        """
        批量插入
        Args:
            datas:
                [[key, value]]
        Returns:

        """
        pipe = self._redis.pipeline(transaction=True)

        if not self._is_redis_cluster:
            pipe.multi()
        for key, value in datas:
            pipe.hset(table, key, value)
        return pipe.execute()

    def hincrby(self, table, key, increment):
        return self._redis.hincrby(table, key, increment)

    def hget(self, table, key, is_pop=False):
        if not is_pop:
            return self._redis.hget(table, key)
        else:
            lua = """
                local key = KEYS[1]
                local field = ARGV[1]

                -- 取值
                local datas = redis.call('hget', key, field)
                -- 删除值
                redis.call('hdel', key, field)

                return datas

                    """
            cmd = self._redis.register_script(lua)
            res = cmd(keys=[table], args=[key])

            return res

    def hgetall(self, table):
        return self._redis.hgetall(table)

    def hexists(self, table, key):
        return self._redis.hexists(table, key)

    def hdel(self, table, *keys):
        """
        @summary: 删除对应的key 可传多个
        ---------
        @param table:
        @param *keys:
        ---------
        @result:
        """

        self._redis.hdel(table, *keys)

    def hget_count(self, table):
        return self._redis.hlen(table)

    def setbit(self, table, offsets, values):
        """
        设置字符串数组某一位的值， 返回之前的值
        @param table:
        @param offsets: 支持列表或单个值
        @param values: 支持列表或单个值
        @return: list / 单个值
        """
        if isinstance(offsets, list):
            if not isinstance(values, list):
                values = [values] * len(offsets)
            else:
                assert len(offsets) == len(values), "offsets值要与values值一一对应"

            pipe = self._redis.pipeline(
                transaction=True
            )  # redis-py默认在执行每次请求都会创建（连接池申请连接）和断开（归还连接池）一次连接操作，如果想要在一次请求中指定多个命令，则可以使用pipline实现一次请求指定多个命令，并且默认情况下一次pipline 是原子性操作。
            pipe.multi()

            for offset, value in zip(offsets, values):
                pipe.setbit(table, offset, value)

            return pipe.execute()

        else:
            return self._redis.setbit(table, offsets, values)

    def getbit(self, table, offsets):
        """
        取字符串数组某一位的值
        @param table:
        @param offsets: 支持列表
        @return: list / 单个值
        """
        if isinstance(offsets, list):
            pipe = self._redis.pipeline(
                transaction=True
            )  # redis-py默认在执行每次请求都会创建（连接池申请连接）和断开（归还连接池）一次连接操作，如果想要在一次请求中指定多个命令，则可以使用pipline实现一次请求指定多个命令，并且默认情况下一次pipline 是原子性操作。
            pipe.multi()
            for offset in offsets:
                pipe.getbit(table, offset)

            return pipe.execute()

        else:
            return self._redis.getbit(table, offsets)

    def bitcount(self, table):
        return self._redis.bitcount(table)

    def strset(self, table, value, **kwargs):
        return self._redis.set(table, value, **kwargs)

    def str_incrby(self, table, value):
        return self._redis.incrby(table, value)

    def strget(self, table):
        return self._redis.get(table)

    def strlen(self, table):
        return self._redis.strlen(table)

    def getkeys(self, regex):
        return self._redis.keys(regex)

    def exists_key(self, key):
        return self._redis.exists(key)

    def set_expire(self, key, seconds):
        """
        @summary: 设置过期时间
        ---------
        @param key:
        @param seconds: 秒
        ---------
        @result:
        """

        self._redis.expire(key, seconds)

    def clear(self, table):
        try:
            self._redis.delete(table)
        except Exception as e:
            log.error(e)

    def get_redis_obj(self):
        return self._redis
