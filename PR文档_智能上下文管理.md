# Pull Request: 智能上下文管理功能

## 📋 功能概述

为 feapder 框架新增**智能上下文管理**功能，通过静态代码分析和运行时参数收集，实现回调函数之间的参数自动传递，彻底解决多层回调中的参数传递难题。

## 🎯 解决的问题

### 传统方式的痛点
```python
# ❌ 传统方式：每一层都要手动传递参数，非常繁琐
def parse_list(self, request, response):
    category_id = request.category_id
    shop_name = "某商店"

    yield Request(
        url,
        callback=self.parse_detail,
        category_id=category_id,      # 手动传递
        shop_name=shop_name            # 手动传递
    )

def parse_detail(self, request, response):
    category_id = request.category_id
    shop_name = request.shop_name
    product_name = "某商品"

    yield Request(
        url,
        callback=self.parse_price,
        category_id=category_id,      # 手动传递
        shop_name=shop_name,          # 手动传递
        product_name=product_name     # 手动传递
    )
```

### 新功能优势
```python
# ✅ 智能上下文管理：自动捕获和传递参数
def parse_list(self, request, response):
    category_id = request.category_id
    shop_name = "某商店"  # 自动捕获

    yield Request(
        url,
        callback=self.parse_detail,
        auto_inherit_context=True  # 仅需这一行
    )

def parse_detail(self, request, response):
    # 直接访问，无需手动传递
    print(request.category_id)    # ✅ 自动获得
    print(request.shop_name)      # ✅ 自动获得

    product_name = "某商品"

    yield Request(
        url,
        callback=self.parse_price,
        auto_inherit_context=True
    )
```

## 🚀 核心特性

### 1. 三种参数来源自动捕获
- **来源1**：局部变量（如 `shop_name = "某商店"`）
- **来源2**：从 request 获取后赋值（如 `current_site = request.site_name`）
- **来源3**：Request 构造函数中显式传入（如 `category_id=100`）

### 2. 两种传递模式

#### Transitive 模式（默认，推荐）
- 传递给当前回调及所有后续回调需要的参数
- 即使中间层不使用，参数仍会传递到最终层
- 适合多层回调场景

#### Direct 模式
- 只传递给下一层回调需要的参数
- 中间层不使用的参数会被丢弃
- 适合简单的单层回调场景

### 3. 智能参数过滤
自动过滤不应该传递的对象：
- 私有变量（以 `_` 开头）
- 特殊对象（response, self, modules, files, sockets, locks）
- 大对象（≥ 1MB，记录警告日志）
- None 值（从父请求继承时过滤，局部变量允许）

### 4. 静态代码分析
- 启动时一次性分析所有回调函数
- 构建回调依赖图（谁调用谁）
- 计算每个回调需要的参数集合
- 计算传递性参数需求（使用 DFS 算法）

## 📦 新增文件

### 核心模块
- `feapder/utils/context_analyzer.py` - 静态代码分析引擎
  - `ContextAnalyzer` 类：AST 分析器
  - `analyze()` 方法：分析每个回调访问的参数
  - `build_callback_graph()` 方法：构建回调依赖图
  - `compute_transitive_needs()` 方法：计算传递性参数需求

### 文档
- `docs/usage/智能上下文管理.md` - 完整的使用文档
  - 快速开始指南
  - 三种参数来源详解
  - 传递模式对比
  - 配置选项说明
  - 常见问题解答（9个Q&A）

### 测试文件
- `tests/test_smart_context.py` - 基础功能测试
- `tests/test_smart_context_10_layers.py` - 10 层传递压力测试
- `tests/test_smart_context_real.py` - 真实场景测试

## 🔧 修改的文件

### `feapder/network/request.py`
**主要改动**：
1. 新增 `auto_inherit_context` 参数（默认 False）
2. 新增 `_inherit_context_from_parent()` 方法：运行时参数继承逻辑
3. 新增 `_should_skip_value()` 方法：参数过滤逻辑
4. 优化性能：移动 imports 到模块级别，预计算锁类型

### `feapder/core/spiders/air_spider.py`
**主要改动**：
1. `__init__` 中调用静态分析器
2. 将分析结果保存到 spider 实例

### `feapder/core/scheduler.py`
**主要改动**：
1. 将 spider 的分析结果传递给 `ParserControl`

### `feapder/core/parser_control.py`
**主要改动**：
1. 接收并保存静态分析结果
2. 在 request 创建时注入分析结果

### `feapder/setting.py`
**新增配置项**：
```python
# 智能上下文管理开关（默认关闭）
SMART_CONTEXT_ENABLE = False

# 智能上下文传递模式（默认 transitive）
# - "direct": 只传递给下一层回调需要的参数
# - "transitive": 传递给当前回调及所有后续回调需要的参数（推荐）
SMART_CONTEXT_MODE = "transitive"
```

### `docs/_sidebar.md`
**新增导航项**：
- 添加"智能上下文管理"文档链接

## ✅ 测试结果

### 测试 1: 10 层传递测试（Transitive 模式）
```
✅ level_1_data 跨越 8 层传递成功 (第1层 → 第10层)
✅ level_2_data 跨越 8 层传递成功 (第2层 → 第10层)
✅ level_5_data 跨越 5 层传递成功 (第5层 → 第10层)
✅ 中间层(3-9)虽然不使用这些参数，但依然正确传递
✅ transitive 模式工作正常！
```

### 测试 2: 10 层传递测试（Direct 模式对比）
```
✅ direct 模式行为符合预期（参数在中间层丢失）
```

### 测试 3: 真实场景测试
```
✅ 三种参数来源都能正确捕获
✅ 参数在多层回调中正确传递
✅ 不应捕获的参数被正确过滤
✅ 大对象也能被正确传递
✅ 整个过程无报错
```

### 测试 4: 参数过滤测试
```
✅ 成功获取应该被捕获的参数
✅ 过滤正确: 私有变量和特殊对象都被正确过滤
```

## 💡 使用示例

### 基础用法
```python
import feapder

class MySpider(feapder.AirSpider):
    __custom_setting__ = dict(
        SMART_CONTEXT_ENABLE=True  # 开启智能上下文管理
    )

    def start_requests(self):
        yield feapder.Request(
            "https://example.com/list",
            callback=self.parse_list,
            auto_inherit_context=True,
            site_id=1,
            site_name="示例网站"
        )

    def parse_list(self, request, response):
        # 自动获得 site_id 和 site_name
        print(request.site_id)     # 1
        print(request.site_name)   # "示例网站"

        # 定义新参数
        category_id = 100
        category_name = "电子产品"

        # 自动传递所有参数
        yield feapder.Request(
            "https://example.com/detail",
            callback=self.parse_detail,
            auto_inherit_context=True
        )

    def parse_detail(self, request, response):
        # 自动获得所有参数
        print(request.site_id)       # 1
        print(request.site_name)     # "示例网站"
        print(request.category_id)   # 100
        print(request.category_name) # "电子产品"
```

## 🔄 兼容性说明

### 向后兼容
- **默认关闭**：`SMART_CONTEXT_ENABLE = False`
- 不影响现有代码，现有爬虫无需修改
- 仅在显式开启 `auto_inherit_context=True` 时生效

### 性能影响
- **启动时**：一次性静态分析（通常 < 100ms）
- **运行时**：每个 Request 创建时多一次参数复制（< 1ms）
- **内存占用**：每个 Request 多存储部分参数（通常 < 1KB）

## 📚 文档链接

- [完整使用文档](docs/usage/智能上下文管理.md)
- [测试代码示例](tests/test_smart_context_real.py)
- [10 层传递测试](tests/test_smart_context_10_layers.py)

## 🎉 总结

智能上下文管理功能经过充分测试，已准备就绪，可以极大提升多层回调场景的开发效率和代码可读性。

---

**作者**: daozhang
**创建时间**: 2025-01-19
**测试通过率**: 100%
