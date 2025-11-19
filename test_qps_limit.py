# -*- coding: utf-8 -*-
"""
QPS限制功能测试脚本
测试域名级QPS限制是否正常工作
"""

import time
import feapder


class TestQpsSpider(feapder.AirSpider):
    """测试QPS限制的爬虫"""

    __custom_setting__ = dict(
        # 启用域名级QPS限制
        DOMAIN_RATE_LIMIT_ENABLE=True,
        # 默认QPS设置为2（方便观察）
        DOMAIN_RATE_LIMIT_DEFAULT=2,
        # 特定域名的QPS规则
        DOMAIN_RATE_LIMIT_RULES={
            "httpbin.org": 1,  # httpbin限制为1 QPS（每秒1个请求）
            "www.baidu.com": 2,  # 百度限制为2 QPS
        },
    )

    def start_requests(self):
        """发送测试请求"""
        print("\n========== 开始测试域名级QPS限制 ==========")
        print(f"配置: httpbin.org = 1 QPS, www.baidu.com = 2 QPS")
        print(f"测试开始时间: {time.strftime('%H:%M:%S')}\n")

        # 测试1: httpbin.org (1 QPS)
        for i in range(3):
            yield feapder.Request(
                f"https://httpbin.org/delay/0?test={i}",
                callback=self.parse_httpbin,
            )

        # 测试2: www.baidu.com (2 QPS)
        for i in range(3):
            yield feapder.Request(
                f"https://www.baidu.com/s?wd=test{i}",
                callback=self.parse_baidu,
            )

    def parse_httpbin(self, request, response):
        """解析httpbin响应"""
        current_time = time.strftime("%H:%M:%S")
        print(f"[{current_time}] ✅ httpbin请求完成: {request.url}")

    def parse_baidu(self, request, response):
        """解析百度响应"""
        current_time = time.strftime("%H:%M:%S")
        print(f"[{current_time}] ✅ 百度请求完成: {request.url}")


def test_local_token_bucket():
    """测试本地令牌桶"""
    print("\n========== 测试本地令牌桶算法 ==========")
    from feapder.utils.rate_limiter import LocalTokenBucket

    bucket = LocalTokenBucket(qps=2)  # 2 QPS
    print(f"创建令牌桶: 容量=2, QPS=2")

    # 测试1: 前2个请求应该立即通过
    print("\n测试1: 前2个请求应该立即通过")
    for i in range(2):
        wait_time = bucket.acquire()
        print(f"  请求{i+1}: 等待时间 = {wait_time:.3f}秒 {'✅ 立即通过' if wait_time == 0 else '❌ 需要等待'}")

    # 测试2: 第3个请求需要等待
    print("\n测试2: 第3个请求需要等待")
    wait_time = bucket.acquire()
    print(f"  请求3: 等待时间 = {wait_time:.3f}秒 {'❌ 立即通过' if wait_time == 0 else '✅ 需要等待'}")

    # 测试3: 等待0.5秒后补充1个令牌
    print("\n测试3: 等待0.5秒后应该补充1个令牌")
    time.sleep(0.5)
    wait_time = bucket.acquire()
    print(f"  请求4: 等待时间 = {wait_time:.3f}秒 {'✅ 立即通过' if wait_time == 0 else '❌ 需要等待'}")

    print("\n✅ 本地令牌桶测试完成")


def test_domain_extraction():
    """测试域名提取功能"""
    print("\n========== 测试域名提取功能 ==========")
    from feapder.network.request import Request

    test_urls = [
        "https://www.baidu.com/s?wd=test",
        "https://baidu.com/s?wd=test",
        "http://news.sina.com.cn/page.html",
        "https://api.example.com/v1/data",
        "https://example.com:8080/path",
    ]

    for url in test_urls:
        domain = Request._extract_domain(url)
        print(f"  {url} -> {domain}")

    print("\n✅ 域名提取测试完成")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" feapder 域名级QPS限制功能测试")
    print("=" * 60)

    # 运行单元测试
    test_domain_extraction()
    test_local_token_bucket()

    # 运行集成测试（可选，需要网络）
    print("\n" + "=" * 60)
    user_input = input("\n是否运行集成测试（需要网络连接）？[y/N]: ")
    if user_input.lower() == "y":
        TestQpsSpider(thread_count=1).start()
    else:
        print("跳过集成测试")

    print("\n" + "=" * 60)
    print(" 测试完成！")
    print("=" * 60 + "\n")
