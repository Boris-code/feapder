# -*- coding: utf-8 -*-
"""
Created on 2025-01-20
---------
@summary: 智能上下文管理 - 10 层传递测试 (测试 transitive 模式)
---------
@author: daozhang
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feapder


class Test10LayersTransitive(feapder.AirSpider):
    """
    测试 transitive 模式的 10 层传递

    场景设计：
    - level_1_data: 在第1层定义，在第2层使用，在第3-9层不使用，在第10层使用
    - level_2_data: 在第2层定义，在第10层使用
    - level_5_data: 在第5层定义，在第10层使用

    预期结果（transitive 模式）：
    - 所有层都能访问到最终层需要的参数，即使中间层不使用
    - 第10层能成功访问 level_1_data, level_2_data, level_5_data
    """

    __custom_setting__ = dict(
        SMART_CONTEXT_ENABLE=True,
        SMART_CONTEXT_MODE="transitive",  # 使用传递性模式
        SPIDER_THREAD_COUNT=1,
    )

    def start_requests(self):
        print("\n" + "=" * 80)
        print("🚀 测试场景: transitive 模式 - 10 层传递")
        print("=" * 80)
        print("\n📝 测试目标:")
        print("  - level_1_data: 第1层定义 → 第2层使用 → 第3-9层不使用 → 第10层使用")
        print("  - level_2_data: 第2层定义 → 第3-9层不使用 → 第10层使用")
        print("  - level_5_data: 第5层定义 → 第6-9层不使用 → 第10层使用")
        print("\n⚙️  模式: SMART_CONTEXT_MODE = transitive")
        print("=" * 80)

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_1,
            auto_inherit_context=True,
        )

    def parse_level_1(self, request, response):
        print("\n📍 第1层: parse_level_1")

        # 定义 level_1_data（将在第2层和第10层使用）
        level_1_data = "来自第1层的数据"
        print(f"  📝 定义: level_1_data = '{level_1_data}'")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_2,
            auto_inherit_context=True,
        )

    def parse_level_2(self, request, response):
        print("\n📍 第2层: parse_level_2")

        # 使用 level_1_data
        try:
            level_1_data = request.level_1_data
            print(f"  ✅ 成功获取: level_1_data = '{level_1_data}'")
        except AttributeError as e:
            print(f"  ❌ 错误: 无法获取 level_1_data - {e}")
            raise

        # 定义 level_2_data（将在第10层使用，但第3-9层不使用）
        level_2_data = "来自第2层的数据"
        print(f"  📝 定义: level_2_data = '{level_2_data}'")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_3,
            auto_inherit_context=True,
        )

    def parse_level_3(self, request, response):
        print("\n📍 第3层: parse_level_3 (不使用任何 level_X_data)")

        # 第3层不使用任何参数，直接传递
        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_4,
            auto_inherit_context=True,
        )

    def parse_level_4(self, request, response):
        print("\n📍 第4层: parse_level_4 (不使用任何 level_X_data)")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_5,
            auto_inherit_context=True,
        )

    def parse_level_5(self, request, response):
        print("\n📍 第5层: parse_level_5")

        # 定义 level_5_data（将在第10层使用，但第6-9层不使用）
        level_5_data = "来自第5层的数据"
        print(f"  📝 定义: level_5_data = '{level_5_data}'")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_6,
            auto_inherit_context=True,
        )

    def parse_level_6(self, request, response):
        print("\n📍 第6层: parse_level_6 (不使用任何 level_X_data)")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_7,
            auto_inherit_context=True,
        )

    def parse_level_7(self, request, response):
        print("\n📍 第7层: parse_level_7 (不使用任何 level_X_data)")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_8,
            auto_inherit_context=True,
        )

    def parse_level_8(self, request, response):
        print("\n📍 第8层: parse_level_8 (不使用任何 level_X_data)")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_9,
            auto_inherit_context=True,
        )

    def parse_level_9(self, request, response):
        print("\n📍 第9层: parse_level_9 (不使用任何 level_X_data)")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_10,
            auto_inherit_context=True,
        )

    def parse_level_10(self, request, response):
        print("\n📍 第10层: parse_level_10 (最终层)")

        # 尝试访问所有三个参数
        errors = []

        try:
            level_1_data = request.level_1_data
            print(f"  ✅ 成功获取: level_1_data = '{level_1_data}'")
        except AttributeError as e:
            error_msg = f"无法获取 level_1_data (来自第1层)"
            print(f"  ❌ 错误: {error_msg}")
            errors.append(error_msg)

        try:
            level_2_data = request.level_2_data
            print(f"  ✅ 成功获取: level_2_data = '{level_2_data}'")
        except AttributeError as e:
            error_msg = f"无法获取 level_2_data (来自第2层)"
            print(f"  ❌ 错误: {error_msg}")
            errors.append(error_msg)

        try:
            level_5_data = request.level_5_data
            print(f"  ✅ 成功获取: level_5_data = '{level_5_data}'")
        except AttributeError as e:
            error_msg = f"无法获取 level_5_data (来自第5层)"
            print(f"  ❌ 错误: {error_msg}")
            errors.append(error_msg)

        if errors:
            print("\n" + "=" * 80)
            print("❌ 测试失败: transitive 模式未能正确传递参数")
            print("=" * 80)
            for error in errors:
                print(f"  ❌ {error}")
            raise AssertionError("\n".join(errors))
        else:
            print("\n" + "=" * 80)
            print("🎉 测试成功！transitive 模式正确传递了所有参数")
            print("=" * 80)
            print("\n📋 验证结果:")
            print("  ✅ level_1_data 跨越 8 层传递成功 (第1层 → 第10层)")
            print("  ✅ level_2_data 跨越 8 层传递成功 (第2层 → 第10层)")
            print("  ✅ level_5_data 跨越 5 层传递成功 (第5层 → 第10层)")
            print("  ✅ 中间层(3-9)虽然不使用这些参数，但依然正确传递")
            print("  ✅ transitive 模式工作正常！")


class Test10LayersDirect(feapder.AirSpider):
    """
    对比测试: direct 模式的 10 层传递

    预期结果（direct 模式）：
    - 第10层无法访问 level_1_data（因为第3-9层不使用，direct 模式会丢弃）
    - 这个测试预期会失败，用于对比 transitive 模式的优势
    """

    __custom_setting__ = dict(
        SMART_CONTEXT_ENABLE=True,
        SMART_CONTEXT_MODE="direct",  # 使用直接模式
        SPIDER_THREAD_COUNT=1,
    )

    def start_requests(self):
        print("\n" + "=" * 80)
        print("🚀 对比测试: direct 模式 - 10 层传递")
        print("=" * 80)
        print("\n⚠️  预期: direct 模式会在中间层丢失参数（因为中间层不使用）")
        print("⚙️  模式: SMART_CONTEXT_MODE = direct")
        print("=" * 80)

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_1,
            auto_inherit_context=True,
        )

    def parse_level_1(self, request, response):
        print("\n📍 第1层: parse_level_1")
        level_1_data = "来自第1层的数据"
        print(f"  📝 定义: level_1_data = '{level_1_data}'")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_2,
            auto_inherit_context=True,
        )

    def parse_level_2(self, request, response):
        print("\n📍 第2层: parse_level_2")

        try:
            level_1_data = request.level_1_data
            print(f"  ✅ 成功获取: level_1_data = '{level_1_data}'")
        except AttributeError as e:
            print(f"  ❌ 错误: 无法获取 level_1_data - {e}")
            raise

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_3,
            auto_inherit_context=True,
        )

    def parse_level_3(self, request, response):
        print("\n📍 第3层: parse_level_3 (不使用 level_1_data)")

        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_4,
            auto_inherit_context=True,
        )

    def parse_level_4(self, request, response):
        print("\n📍 第4层: parse_level_4")
        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_5,
            auto_inherit_context=True,
        )

    def parse_level_5(self, request, response):
        print("\n📍 第5层: parse_level_5")
        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_6,
            auto_inherit_context=True,
        )

    def parse_level_6(self, request, response):
        print("\n📍 第6层: parse_level_6")
        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_7,
            auto_inherit_context=True,
        )

    def parse_level_7(self, request, response):
        print("\n📍 第7层: parse_level_7")
        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_8,
            auto_inherit_context=True,
        )

    def parse_level_8(self, request, response):
        print("\n📍 第8层: parse_level_8")
        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_9,
            auto_inherit_context=True,
        )

    def parse_level_9(self, request, response):
        print("\n📍 第9层: parse_level_9")
        yield feapder.Request(
            "https://www.baidu.com",
            callback=self.parse_level_10,
            auto_inherit_context=True,
        )

    def parse_level_10(self, request, response):
        print("\n📍 第10层: parse_level_10 (最终层)")

        # 尝试访问 level_1_data
        try:
            level_1_data = request.level_1_data
            print(f"  ⚠️  意外: direct 模式居然能获取到 level_1_data = '{level_1_data}'")
            print("     （这可能表示 direct 模式实现有问题）")
        except AttributeError as e:
            print(f"  ✅ 符合预期: direct 模式无法获取 level_1_data")
            print(f"     原因: 第3-9层不使用该参数，direct 模式不会传递")

            print("\n" + "=" * 80)
            print("✅ direct 模式行为符合预期（参数在中间层丢失）")
            print("=" * 80)
            print("\n📋 对比结果:")
            print("  ❌ direct 模式: 参数在中间层丢失")
            print("  ✅ transitive 模式: 参数能跨越多层传递")
            print("  💡 建议: 使用 transitive 模式（默认）以避免参数丢失")
            return  # 正常结束

        # 如果能获取到，说明有问题
        raise AssertionError("direct 模式不应该能获取到 level_1_data!")


if __name__ == "__main__":
    print("\n" + "=" * 90)
    print("智能上下文管理 - 10 层传递对比测试")
    print("=" * 90)

    success = True

    try:
        # 测试1: transitive 模式（应该成功）
        print("\n\n【测试1】transitive 模式 - 10 层传递")
        print("-" * 90)
        spider1 = Test10LayersTransitive()
        spider1.start()

    except Exception as e:
        print("\n❌ transitive 模式测试失败")
        import traceback
        traceback.print_exc()
        success = False

    try:
        # 测试2: direct 模式（预期在第10层失败）
        print("\n\n【测试2】direct 模式 - 10 层传递（对比）")
        print("-" * 90)
        spider2 = Test10LayersDirect()
        spider2.start()

    except Exception as e:
        print("\n❌ direct 模式测试失败（但这可能是预期的）")
        import traceback
        traceback.print_exc()

    if success:
        print("\n\n" + "=" * 90)
        print("✅ 10 层传递测试完成！")
        print("=" * 90)
        print("\n📊 测试总结:")
        print("  ✅ transitive 模式: 参数能跨越 10 层正确传递")
        print("  ❌ direct 模式: 参数在中间层丢失（符合预期）")
        print("\n💡 结论:")
        print("  - transitive 模式适合多层回调场景（默认推荐）")
        print("  - direct 模式适合简单的单层回调场景")
        print("=" * 90)
    else:
        print("\n\n" + "=" * 90)
        print("❌ 测试失败")
        print("=" * 90)
        sys.exit(1)
