# -*- coding: utf-8 -*-
# @FileName: compress_response_content.py

import zlib
from hashlib import sha1
import os


def default_generate_save_path_method(url: str, base_dir: str) -> str:
    """
    默认生成存贮文件路径函数(采用对URL取sha1, 然后分别取[9, 19], [29, 39]位作为路径分散存储, 目的是防止单个路径下存储过多文件)
    """
    url_hash = sha1(url.encode('utf-8')).hexdigest()
    hash_dir_path = os.path.join('%s%s' % (url_hash[9], url_hash[19]), '%s%s' % (url_hash[29], url_hash[39]))
    dir_path = (os.path.join(base_dir, hash_dir_path))
    # 如果这个路径不存在，创建新的
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    filename = url_hash + '.zlib'
    return os.path.join(dir_path, filename)


def default_compress_algorithm(content: bytes) -> bytes:
    """
    默认response压缩算法(zlib)
    """
    return zlib.compress(content)


def compress_response(url: str, content: bytes, base_dir: str, get_path=None, compress_algorithm=None) -> str:
    """
    压缩并存储返回内容, 返回保存的路径
    get_path: 获取存储的路径(入参为请求的URL), 如需自定义, 必须为callable
    compress_algorithm: 压缩算法(入参为response.content), 如需自定义, 必须为callable
    """
    if get_path is None:
        get_path = default_generate_save_path_method
    # 默认采用zlib压缩
    if compress_algorithm is None:
        compress_algorithm = default_compress_algorithm
    # 检测callable
    assert hasattr(get_path, '__call__')
    assert hasattr(compress_algorithm, '__call__')

    save_path = get_path(url, base_dir)
    compress_data = compress_algorithm(content)
    with open(save_path, 'wb') as f:
        f.write(compress_data)
    return save_path
