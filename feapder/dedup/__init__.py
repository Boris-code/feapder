# -*- coding: utf-8 -*-
"""
Created on 2018-12-13 21:08
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

import copy
from typing import Any, List, Union, Optional, Tuple, Callable

from feapder.utils.tools import get_md5
from .bloomfilter import BloomFilter, ScalableBloomFilter
from .expirefilter import ExpireFilter


class Dedup:
    BloomFilter = 1
    MemoryFilter = 2
    ExpireFilter = 3

    def __init__(self, filter_type: int = BloomFilter, to_md5: bool = True, **kwargs):
        """
        去重过滤器 集成BloomFilter、MemoryFilter、ExpireFilter
        Args:
            filter_type: 过滤器类型 BloomFilter
            name: 过滤器名称 该名称会默认以dedup作为前缀 dedup:expire_set:[name]/dedup:bloomfilter:[name]。 默认ExpireFilter name=过期时间; BloomFilter name=dedup:bloomfilter:bloomfilter
            absolute_name: 过滤器绝对名称 不会加dedup前缀
            expire_time: ExpireFilter的过期时间 单位为秒，其他两种过滤器不用指定
            error_rate: BloomFilter/MemoryFilter的误判率 默认为0.00001
            to_md5: 去重前是否将数据转为MD5，默认是
            redis_url: redis://[[username]:[password]]@localhost:6379/0
                       BloomFilter 与 ExpireFilter 使用
                       默认会读取setting中的redis配置，若无setting，则需要专递redis_url
            **kwargs:
        """

        if filter_type == Dedup.ExpireFilter:
            try:
                expire_time = kwargs["expire_time"]
            except:
                raise ValueError("需传参数 expire_time")

            name = kwargs.get("absolute_name") or "dedup:expire_set:%s" % kwargs.get(
                "name", expire_time
            )
            expire_time_record_key = "dedup:expire_set:expire_time"

            self.dedup = ExpireFilter(
                name=name,
                expire_time=expire_time,
                expire_time_record_key=expire_time_record_key,
                redis_url=kwargs.get("redis_url"),
            )

        else:
            initial_capacity = kwargs.get("initial_capacity", 100000000)
            error_rate = kwargs.get("error_rate", 0.00001)
            name = kwargs.get("absolute_name") or "dedup:bloomfilter:" + kwargs.get(
                "name", "bloomfilter"
            )
            if filter_type == Dedup.BloomFilter:
                self.dedup = ScalableBloomFilter(
                    name=name,
                    initial_capacity=initial_capacity,
                    error_rate=error_rate,
                    bitarray_type=ScalableBloomFilter.BASE_REDIS,
                    redis_url=kwargs.get("redis_url"),
                )
            elif filter_type == Dedup.MemoryFilter:
                self.dedup = ScalableBloomFilter(
                    name=name,
                    initial_capacity=initial_capacity,
                    error_rate=error_rate,
                    bitarray_type=ScalableBloomFilter.BASE_MEMORY,
                )
            else:
                raise ValueError(
                    "filter_type 类型错误，仅支持 Dedup.BloomFilter、Dedup.MemoryFilter、Dedup.ExpireFilter"
                )

        self._to_md5 = to_md5

    def __repr__(self):
        return str(self.dedup)

    def _deal_datas(self, datas):
        if self._to_md5:
            if isinstance(datas, list):
                keys = [get_md5(data) for data in datas]
            else:
                keys = get_md5(datas)
        else:
            keys = copy.deepcopy(datas)

        return keys

    def add(
        self, datas: Union[List[Any], Any], skip_check: bool = False
    ) -> Union[List[Any], Any]:
        """
        添加数据
        @param datas: list / 单个值
        @param skip_check: 是否直接添加，不检查是否存在 适用于bloomfilter，加快add速度
        @return: list / 单个值 (如果数据已存在 返回 0 否则返回 1, 可以理解为是否添加成功)
        """

        keys = self._deal_datas(datas)
        is_added = self.dedup.add(keys, skip_check)

        return is_added

    def get(self, datas: Union[List[Any], Any]) -> Union[List[Any], Any]:
        """
        检查数据是否存在
        @param datas: list / 单个值
        @return: list / 单个值 （存在返回1 不存在返回0)
        """
        keys = self._deal_datas(datas)
        is_exists = self.dedup.get(keys)

        return is_exists

    def filter_exist_data(
        self,
        datas: List[Any],
        *,
        datas_fingerprints: Optional[List] = None,
        callback: Callable[[Any], None] = None
    ) -> Union[Tuple[List[Any], List[Any]], List[Any]]:
        """
        过滤掉已存在的数据
        *** 直接修改原来的数据 使用完此方法后 datas, datas_fingerprints 里面的值为去重后的数据
        @param datas_fingerprints: 数据的唯一指纹 列表
        @param datas: 数据 列表
        @param callback: 数据已存在时的回调 callback(data)
        @return: None
        """

        is_exists = self.get(datas_fingerprints or datas)

        dedup_datas = []

        if datas_fingerprints:
            dedup_datas_fingerprints = []
            while is_exists:
                data = datas.pop(0)
                is_exist = is_exists.pop(0)
                data_fingerprint = datas_fingerprints.pop(0)

                if not is_exist:
                    dedup_datas.append(data)
                    dedup_datas_fingerprints.append(data_fingerprint)
                else:
                    if callback:
                        callback(data)

            datas_fingerprints.extend(dedup_datas_fingerprints)
            datas.extend(dedup_datas)
            return datas, datas_fingerprints

        else:
            while is_exists:
                data = datas.pop(0)
                is_exist = is_exists.pop(0)

                if not is_exist:
                    dedup_datas.append(data)
                else:
                    if callback:
                        callback(data)

            datas.extend(dedup_datas)
            return datas
