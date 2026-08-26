# -*- coding: utf-8 -*-
"""
Created on 2025-01-19
---------
@summary: 智能上下文管理 - 真实运行测试
---------
@author: daozhang
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feapder


class RealTestSpider(feapder.AirSpider):
    """
    真实运行测试：验证参数确实被传递且不报错
    """

    __custom_setting__ = dict(
        SMART_CONTEXT_ENABLE=True,
        SPIDER_THREAD_COUNT=1,  # 单线程便于观察
    )

    def start_requests(self):
        print("\n" + "=" * 60)
        print("🚀 开始测试：验证三种参数来源")
        print("=" * 60)

        # 【来源3】在 Request 中显式传入
        yield feapder.Request(
            "https://www.baidu.com",  # 使用一个真实可访问的URL
            callback=self.parse_level1,
            auto_inherit_context=True,
            site_id=1,
            site_name="百度",
        )

    def parse_level1(self, request, response):
        print("\n📍 第1层: parse_level1")

        # 验证能访问到 start_requests 传入的参数
        try:
            site_id = request.site_id
            site_name = request.site_name
            print(f"  ✅ 【来源3】从 start_requests 获取:")
            print(f"     - site_id = {site_id}")
            print(f"     - site_name = {site_name}")
        except AttributeError as e:
            print(f"  ❌ 错误: {e}")
            raise

        # 【来源1】直接定义的局部变量
        category_name = "新闻分类"
        category_level = 1
        print(f"  📝 【来源1】定义局部变量:")
        print(f"     - category_name = {category_name}")
        print(f"     - category_level = {category_level}")

        # 【来源2】从 request 获取后赋值
        current_site = request.site_name
        print(f"  📝 【来源2】从 request 获取:")
        print(f"     - current_site = {current_site}")

        # 完全不需要手动传参数
        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level2,
            auto_inherit_context=True,
            # 【来源3】新增参数
            category_id=100,
        )

    def parse_level2(self, request, response):
        print("\n📍 第2层: parse_level2")

        # 验证能访问到所有参数
        try:
            site_id = request.site_id
            site_name = request.site_name
            category_id = request.category_id
            category_name = request.category_name
            category_level = request.category_level
            current_site = request.current_site

            print(f"  ✅ 成功获取所有参数:")
            print(f"     - site_id = {site_id} (从 start_requests)")
            print(f"     - site_name = {site_name} (从 start_requests)")
            print(f"     - category_id = {category_id} (从 parse_level1 【来源3】)")
            print(f"     - category_name = {category_name} (从 parse_level1 【来源1】)")
            print(f"     - category_level = {category_level} (从 parse_level1 【来源1】)")
            print(f"     - current_site = {current_site} (从 parse_level1 【来源2】)")
        except AttributeError as e:
            print(f"  ❌ 错误: 缺少参数 {e}")
            raise

        # 【来源1】新的局部变量
        shop_name = "百度商店"
        shop_level = 5
        print(f"  📝 【来源1】定义新局部变量:")
        print(f"     - shop_name = {shop_name}")
        print(f"     - shop_level = {shop_level}")

        # 【来源2】从 request 获取
        parent_category = request.category_name
        print(f"  📝 【来源2】从 request 获取:")
        print(f"     - parent_category = {parent_category}")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level3,
            auto_inherit_context=True,
            shop_id=200,  # 【来源3】
        )

    def parse_level3(self, request, response):
        print("\n📍 第3层: parse_level3")

        # 验证能访问到所有需要的参数
        try:
            site_id = request.site_id
            site_name = request.site_name
            category_id = request.category_id
            category_name = request.category_name
            shop_id = request.shop_id
            shop_name = request.shop_name
            shop_level = request.shop_level
            parent_category = request.parent_category

            print(f"  ✅ 成功获取所有参数:")
            print(f"     - site_id = {site_id}")
            print(f"     - site_name = {site_name}")
            print(f"     - category_id = {category_id}")
            print(f"     - category_name = {category_name}")
            print(f"     - shop_id = {shop_id}")
            print(f"     - shop_name = {shop_name}")
            print(f"     - shop_level = {shop_level}")
            print(f"     - parent_category = {parent_category}")

            print("\n" + "=" * 60)
            print("🎉 测试成功！所有参数都正确传递，无报错！")
            print("=" * 60)

        except AttributeError as e:
            print(f"  ❌ 错误: 缺少参数 {e}")
            raise


class TestParameterFiltering(feapder.AirSpider):
    """
    测试参数过滤：验证不应该被捕获的参数确实被过滤了
    """

    __custom_setting__ = dict(
        SMART_CONTEXT_ENABLE=True,
        SPIDER_THREAD_COUNT=1,
    )

    def start_requests(self):
        print("\n" + "=" * 60)
        print("🧪 测试参数过滤")
        print("=" * 60)

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_with_filters,
            auto_inherit_context=True,
            valid_param="应该被捕获",
        )

    def parse_with_filters(self, request, response):
        print("\n📍 parse_with_filters")

        # 【应该捕获】
        category_id = 123
        valid_param = request.valid_param
        large_text = "这是一个很长的文本" * 1000  # 大对象也应该被捕获

        # 【不应该捕获】
        _private_var = "私有变量"
        self_ref = self
        request_ref = request
        response_ref = response

        print(f"  📝 局部变量:")
        print(f"     - category_id = {category_id}")
        print(f"     - valid_param = {valid_param}")
        print(f"     - large_text 长度 = {len(large_text)}")
        print(f"     - _private_var = {_private_var}")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.check_filtered,
            auto_inherit_context=True,
        )

    def check_filtered(self, request, response):
        print("\n📍 check_filtered - 验证过滤结果")

        # 应该有的参数
        try:
            category_id = request.category_id
            valid_param = request.valid_param
            large_text = request.large_text
            print(f"  ✅ 成功获取应该被捕获的参数:")
            print(f"     - category_id = {category_id}")
            print(f"     - valid_param = {valid_param}")
            print(f"     - large_text 长度 = {len(large_text)}")
        except AttributeError as e:
            print(f"  ❌ 错误: 应该被捕获的参数丢失 {e}")
            raise

        # 不应该有的参数
        errors = []
        if hasattr(request, "_private_var"):
            errors.append("_private_var 不应该被捕获")
        if hasattr(request, "self_ref"):
            errors.append("self_ref 不应该被捕获")
        if hasattr(request, "request_ref"):
            errors.append("request_ref 不应该被捕获")
        if hasattr(request, "response_ref"):
            errors.append("response_ref 不应该被捕获")

        if errors:
            print(f"  ❌ 过滤失败:")
            for error in errors:
                print(f"     - {error}")
            raise AssertionError("\n".join(errors))
        else:
            print(f"  ✅ 过滤正确: 私有变量和特殊对象都被正确过滤")

        print("\n" + "=" * 60)
        print("🎉 参数过滤测试成功！")
        print("=" * 60)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("开始真实运行测试")
    print("=" * 70)

    try:
        # 测试1: 三种参数来源
        print("\n【测试1】三种参数来源的自动捕获")
        spider1 = RealTestSpider()
        spider1.start()

        # 测试2: 参数过滤
        print("\n\n【测试2】参数过滤机制")
        spider2 = TestParameterFiltering()
        spider2.start()

        print("\n" + "=" * 70)
        print("✅ 所有真实运行测试通过！")
        print("=" * 70)
        print("\n📋 验证结果:")
        print("  ✅ 三种参数来源都能正确捕获")
        print("  ✅ 参数在多层回调中正确传递")
        print("  ✅ 不应捕获的参数被正确过滤")
        print("  ✅ 大对象也能被正确传递")
        print("  ✅ 整个过程无报错")

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ 测试失败")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
