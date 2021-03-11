# -*- coding: utf-8 -*-
"""
Created on 2018/12/13 4:11 PM
---------
@summary:
---------
@author: Boris
@email: boris@bzkj.tech
"""

import hashlib
import math
import threading
import time
from struct import unpack, pack

from feapder.db.redisdb import RedisDB
from feapder.utils.redis_lock import RedisLock
from . import bitarray


def make_hashfuncs(num_slices, num_bits):
    if num_bits >= (1 << 31):
        fmt_code, chunk_size = "Q", 8
    elif num_bits >= (1 << 15):
        fmt_code, chunk_size = "I", 4
    else:
        fmt_code, chunk_size = "H", 2
    total_hash_bits = 8 * num_slices * chunk_size
    if total_hash_bits > 384:
        hashfn = hashlib.sha512
    elif total_hash_bits > 256:
        hashfn = hashlib.sha384
    elif total_hash_bits > 160:
        hashfn = hashlib.sha256
    elif total_hash_bits > 128:
        hashfn = hashlib.sha1
    else:
        hashfn = hashlib.md5
    fmt = fmt_code * (hashfn().digest_size // chunk_size)
    num_salts, extra = divmod(num_slices, len(fmt))
    if extra:
        num_salts += 1
    salts = tuple(hashfn(hashfn(pack("I", i)).digest()) for i in range(num_salts))

    def _make_hashfuncs(key):
        if isinstance(key, str):
            key = key.encode("utf-8")
        else:
            key = str(key).encode("utf-8")

        i = 0
        for salt in salts:
            h = salt.copy()
            h.update(key)
            for uint in unpack(fmt, h.digest()):
                yield uint % num_bits
                i += 1
                if i >= num_slices:
                    return

    return _make_hashfuncs


class BloomFilter(object):
    BASE_MEMORY = 1
    BASE_REDIS = 2

    def __init__(
        self,
        capacity: int,
        error_rate: float = 0.00001,
        bitarray_type=BASE_REDIS,
        name=None,
        redis_url=None,
    ):
        if not (0 < error_rate < 1):
            raise ValueError("Error_Rate must be between 0 and 1.")
        if not capacity > 0:
            raise ValueError("Capacity must be > 0")

        # given M = num_bits, k = num_slices, P = error_rate, n = capacity
        # k = log2(1/P)
        # solving for m = bits_per_slice
        # n ~= M * ((ln(2) ** 2) / abs(ln(P)))
        # n ~= (k * m) * ((ln(2) ** 2) / abs(ln(P)))
        # m ~= n * abs(ln(P)) / (k * (ln(2) ** 2))
        num_slices = int(math.ceil(math.log(1.0 / error_rate, 2)))
        bits_per_slice = int(
            math.ceil(
                (capacity * abs(math.log(error_rate)))
                / (num_slices * (math.log(2) ** 2))
            )
        )
        self._setup(error_rate, num_slices, bits_per_slice, capacity)

        if bitarray_type == BloomFilter.BASE_MEMORY:
            self.bitarray = bitarray.MemoryBitArray(self.num_bits)
            self.bitarray.setall(False)
        elif bitarray_type == BloomFilter.BASE_REDIS:
            assert name, "name can't be None "
            self.bitarray = bitarray.RedisBitArray(name, redis_url)
        else:
            raise ValueError("not support this bitarray type")

    def _setup(self, error_rate, num_slices, bits_per_slice, capacity):
        self.error_rate = error_rate
        self.num_slices = num_slices
        self.bits_per_slice = bits_per_slice
        self.capacity = capacity
        self.num_bits = num_slices * bits_per_slice
        self.make_hashes = make_hashfuncs(self.num_slices, self.bits_per_slice)

        self._is_at_capacity = False
        self._check_capacity_time = 0

    def __repr__(self):
        return "<BloomFilter: {}>".format(self.bitarray)

    def get(self, keys, to_list=False):
        is_list = isinstance(keys, list)
        keys = keys if is_list else [keys]
        is_exists = []

        offsets = []
        for key in keys:
            hashes = self.make_hashes(key)
            offset = 0
            for k in hashes:
                offsets.append(offset + k)
                offset += self.bits_per_slice

        old_values = self.bitarray.get(offsets)
        for i in range(0, len(old_values), self.num_slices):
            is_exists.append(int(all(old_values[i : i + self.num_slices])))

        if to_list:
            return is_exists
        else:
            return is_exists if is_list else is_exists[0]

    @property
    def is_at_capacity(self):
        """
        是否容量已满, 1的个数满位数组的一半的时，则看做已满
        比较耗时 半小时检查一次
        @return:
        """
        # if self._is_at_capacity:
        #     return self._is_at_capacity
        #
        # if not self._check_capacity_time or time.time() - self._check_capacity_time > 1800:
        #     bit_count = self.bitarray.count()
        #     if bit_count and bit_count / self.num_bits > 0.5:
        #         self._is_at_capacity = True
        #
        #     self._check_capacity_time = time.time()
        #
        # return self._is_at_capacity

        if self._is_at_capacity:
            return self._is_at_capacity

        bit_count = self.bitarray.count()
        if bit_count and bit_count / self.num_bits > 0.5:
            self._is_at_capacity = True

        return self._is_at_capacity

    def add(self, keys):
        """
        Adds a key to this bloom filter. If the key already exists in this
        filter it will return False. Otherwise True. keys support list
        @param keys: list or one key
        @return:
        """
        if self.is_at_capacity:
            raise IndexError("BloomFilter is at capacity")

        is_list = isinstance(keys, list)

        keys = keys if is_list else [keys]
        is_added = []

        offsets = []
        for key in keys:
            hashes = self.make_hashes(key)
            offset = 0
            for k in hashes:
                offsets.append(offset + k)
                offset += self.bits_per_slice

        old_values = self.bitarray.set(offsets, 1)
        for i in range(0, len(old_values), self.num_slices):
            is_added.append(1 ^ int(all(old_values[i : i + self.num_slices])))

        return is_added if is_list else is_added[0]


class ScalableBloomFilter(object):
    """
    自动扩展空间的bloomfilter, 当一个filter满一半的时候，创建下一个
    """

    BASE_MEMORY = BloomFilter.BASE_MEMORY
    BASE_REDIS = BloomFilter.BASE_REDIS

    def __init__(
        self,
        initial_capacity: int = 100000000,
        error_rate: float = 0.00001,
        bitarray_type=BASE_REDIS,
        name=None,
        redis_url=None,
    ):

        if not error_rate or error_rate < 0:
            raise ValueError("Error_Rate must be a decimal less than 0.")

        self._setup(
            initial_capacity, error_rate, name, bitarray_type, redis_url=redis_url
        )

    def _setup(self, initial_capacity, error_rate, name, bitarray_type, redis_url):
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate
        self.name = name
        self.bitarray_type = bitarray_type
        self.redis_url = redis_url

        self.filters = []

        self.filters.append(self.create_filter())
        self._thread_lock = threading.RLock()
        self._check_capacity_time = 0

    def __repr__(self):
        return "<ScalableBloomFilter: {}>".format(self.filters[-1].bitarray)

    def create_filter(self):
        filter = BloomFilter(
            capacity=self.initial_capacity,
            error_rate=self.error_rate,
            bitarray_type=self.bitarray_type,
            name=self.name + str(len(self.filters)) if self.name else self.name,
            redis_url=self.redis_url,
        )

        return filter

    def check_filter_capacity(self):
        """
        检测filter状态，如果已满，加载新的filter
        @return:
        """
        if (
            not self._check_capacity_time
            or time.time() - self._check_capacity_time > 1800
        ):
            if self.bitarray_type == ScalableBloomFilter.BASE_MEMORY:
                with self._thread_lock:
                    while True:
                        if self.filters[-1].is_at_capacity:
                            self.filters.append(self.create_filter())
                        else:
                            break

                    self._check_capacity_time = time.time()
            else:
                with RedisLock(
                    key="ScalableBloomFilter",
                    timeout=300,
                    wait_timeout=300,
                    redis_cli=RedisDB(url=self.redis_url).get_redis_obj(),
                ) as lock:  # 全局锁 同一时间只有一个进程在真正的创建新的filter，等这个进程创建完，其他进程只是把刚创建的filter append进来
                    if lock.locked:
                        while True:
                            if self.filters[-1].is_at_capacity:
                                self.filters.append(self.create_filter())
                            else:
                                break

                        self._check_capacity_time = time.time()

    def add(self, keys, skip_check=False):
        """
        Adds a key to this bloom filter. If the key already exists in this
        filter it will return False. Otherwise True. keys support list
        @param keys: list or one key
        @param skip_check: add directly，not check if is exist in bloomfilters
        @return:
        """

        self.check_filter_capacity()

        current_filter = self.filters[-1]

        if skip_check:
            return current_filter.add(keys)

        else:
            is_list = isinstance(keys, list)

            keys = keys if is_list else [keys]
            not_exist_keys = list(set(keys))

            # 检查之前的bloomfilter是否存在
            # 记录下每级filter存在的key，不存在的key继续向下检查
            for filter in reversed(self.filters):
                current_filter_is_exists = filter.get(
                    not_exist_keys, to_list=True
                )  # 当前的filter是否存在

                not_exist_keys_temp = []

                for key, is_exist in zip(not_exist_keys, current_filter_is_exists):
                    if not is_exist:  # 当前filter不存在的key 需要继续向下检查
                        not_exist_keys_temp.append(key)

                not_exist_keys = not_exist_keys_temp

                if not not_exist_keys:
                    break

            # 仍有不存在的关键词，记录该关键词
            if not_exist_keys:
                current_filter.add(not_exist_keys)

            # 比较key是否已存在, 内部重复的key 若不存在啊则只留其一算为不存在，其他看作已存在
            for i, key in enumerate(keys):
                for j, not_exist_key in enumerate(not_exist_keys):
                    if key == not_exist_key:
                        keys[i] = 1
                        not_exist_keys.pop(j)
                        break
                else:
                    keys[i] = 0

            is_added = keys
            return is_added if is_list else is_added[0]

    def get(self, keys):
        self.check_filter_capacity()

        is_list = isinstance(keys, list)

        keys = keys if is_list else [keys]  # 最终会修改为 [0, 1, ...] 0表示不存在 1 已存在
        not_exist_keys = list(set(keys))

        # 检查之前的bloomfilter是否存在
        # 记录下每级filter存在的key，不存在的key继续向下检查
        for filter in reversed(self.filters):
            current_filter_is_exists = filter.get(
                not_exist_keys, to_list=True
            )  # 当前的filter是否存在

            not_exist_keys_temp = []

            for checked_key, is_exist in zip(not_exist_keys, current_filter_is_exists):
                if not is_exist:  # 当前filter不存在的key 需要继续向下检查
                    not_exist_keys_temp.append(checked_key)

            not_exist_keys = not_exist_keys_temp

            if not not_exist_keys:
                break

        # 比较key是否已存在, 内部重复的key 若不存在啊则只留其一算为不存在，其他看作已存在
        for i, key in enumerate(keys):
            for j, not_exist_key in enumerate(not_exist_keys):
                if key == not_exist_key:
                    keys[i] = 0
                    not_exist_keys.pop(j)
                    break
            else:
                keys[i] = 1

        is_exists = keys
        return is_exists if is_list else is_exists[0]

    @property
    def capacity(self):
        """Returns the total capacity for all filters in this SBF"""
        return sum(f.capacity for f in self.filters)
