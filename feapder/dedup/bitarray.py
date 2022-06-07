# -*- coding: utf-8 -*-
"""
Created on 2018/12/14 1:05 PM
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from __future__ import absolute_import


from feapder.db.redisdb import RedisDB


class BitArray:
    def setall(self, value):
        pass

    def __repr__(self):
        raise ImportError("this method mush be implement")

    def set(self, offsets, values):
        """
        设置字符串数字某一位的值， 返回之前的值
        @param offsets: 支持列表或单个值
        @param values: 支持列表或单个值
        @return: list / 单个值
        """
        raise ImportError("this method mush be implement")

    def get(self, offsets):
        """
        取字符串数字某一位的值
        @param offsets: 支持列表或单个值
        @return: list / 单个值
        """
        raise ImportError("this method mush be implement")

    def count(self, value=True):
        raise ImportError("this method mush be implement")


class MemoryBitArray(BitArray):
    def __init__(self, num_bits):
        try:
            import bitarray
        except Exception as e:
            raise Exception(
                "需要安装feapder完整版\ncommand: pip install feapder[all]\n若安装出错，参考：https://boris.org.cn/feapder/#/question/%E5%AE%89%E8%A3%85%E9%97%AE%E9%A2%98"
            )

        self.num_bits = num_bits
        self.bitarray = bitarray.bitarray(num_bits, endian="little")

        self.setall(0)

    def __repr__(self):
        return "MemoryBitArray: {}".format(self.num_bits)

    def setall(self, value):
        self.bitarray.setall(value)

    def set(self, offsets, values):
        """
        设置字符串数字某一位的值， 返回之前的值
        @param offsets: 支持列表或单个值
        @param values: 支持列表或单个值
        @return: list / 单个值
        """

        old_values = []

        if isinstance(offsets, list):
            if not isinstance(values, list):
                values = [values] * len(offsets)
            else:
                assert len(offsets) == len(values), "offsets值要与values值一一对应"

            for offset, value in zip(offsets, values):
                old_values.append(int(self.bitarray[offset]))
                self.bitarray[offset] = value

        else:
            old_values = int(self.bitarray[offsets])
            self.bitarray[offsets] = values

        return old_values

    def get(self, offsets):
        """
        取字符串数字某一位的值
        @param offsets: 支持列表或单个值
        @return: list / 单个值
        """
        if isinstance(offsets, list):
            return [self.bitarray[offset] for offset in offsets]
        else:
            return self.bitarray[offsets]

    def count(self, value=True):
        return self.bitarray.count(value)


class RedisBitArray(BitArray):
    """
    仿bitarray 基于redis
    """

    redis_db = None

    def __init__(self, name, redis_url=None):
        self.name = name
        self.count_cached_name = name + "_count_cached"

        if not self.__class__.redis_db:
            self.__class__.redis_db = RedisDB(url=redis_url)

    def __repr__(self):
        return "RedisBitArray: {}".format(self.name)

    def set(self, offsets, values):
        """
        设置字符串数字某一位的值， 返回之前的值
        @param offsets: 支持列表或单个值
        @param values: 支持列表或单个值
        @return: list / 单个值
        """
        return self.redis_db.setbit(self.name, offsets, values)

    def get(self, offsets):
        return self.redis_db.getbit(self.name, offsets)

    def count(self, value=True):
        # 先查redis的缓存，若没有 在统计数量
        count = self.redis_db.strget(self.count_cached_name)
        if count:
            return int(count)
        else:
            count = self.redis_db.bitcount(self.name)  # 被设置为 1 的比特位的数量
            self.redis_db.strset(self.count_cached_name, count, ex=1800)  # 半小时过期
            return count
