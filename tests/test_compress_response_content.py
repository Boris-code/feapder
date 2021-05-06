# -*- coding: utf-8 -*-
# @FileName: test_compress_response_content.py

import os

from feapder.utils.compress_response_content import compress_response

test_url = 'https://www.baidu.com'

test_content = b"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>TITLE</title>
</head>
<body>

</body>
</html
"""


def test_compress_response_content_success():
    saved_path = compress_response(test_url, test_content, './')
    assert os.path.exists(saved_path)
    # 清理测试保存的文件
    os.remove(saved_path)
    os.rmdir('./c3/41')
    os.rmdir('./c3')


def no_compress(content: bytes) -> bytes:
    return content


def test_compress_response_content_with_custom_compress_alg_success():
    saved_path = compress_response(test_url, test_content, './', compress_algorithm=no_compress)
    assert os.path.exists(saved_path)
    with open(saved_path, 'rb') as f:
        compressed_content = f.read()
    assert compressed_content == test_content
    # 清理测试保存的文件
    os.remove(saved_path)
    os.rmdir('./c3/41')
    os.rmdir('./c3')


def custom_get_path_method(api: str, base_dir: str) -> str:
    return './test.html'


def test_compress_content_with_custom_path_success():
    target_path = './test.html'
    saved_path = compress_response(test_url, test_content, './', get_path=custom_get_path_method)
    assert target_path == saved_path
    os.remove(saved_path)


if __name__ == '__main__':
    test_compress_response_content_success()
    test_compress_response_content_with_custom_compress_alg_success()
    test_compress_content_with_custom_path_success()
