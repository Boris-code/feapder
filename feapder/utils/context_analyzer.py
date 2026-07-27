# -*- coding: utf-8 -*-
"""
Created on 2025-01-19
---------
@summary: 智能上下文管理 - 静态代码分析模块
---------
@author: daozhang
"""

import ast
import inspect
from typing import Dict, Set, Type

from feapder.utils.log import log


class ContextAnalyzer:
    """
    静态分析爬虫类，检测每个回调函数访问了 request 的哪些属性

    工作原理：
    1. 使用 Python AST 解析爬虫类的源代码
    2. 遍历每个方法，查找 request.xxx 的属性访问
    3. 返回每个回调函数需要的参数集合

    示例：
        analyzer = ContextAnalyzer(MySpider)
        result = analyzer.analyze()
        # 返回: {'parse_list': {'category_id', 'shop_name'}, ...}
    """

    # 框架保留字段，不应该被自动继承
    _RESERVED_ATTRS = {
        'url', 'callback', 'method', 'params', 'data', 'json',
        'headers', 'cookies', 'meta', 'encoding', 'priority',
        'dont_filter', 'errback', 'flags', 'cb_kwargs',
        'parser_name', 'request_sync', 'download_midware',
        'is_abandoned', 'retry_times', 'filter_repeat',
        'auto_inherit_context', 'render', 'render_time',
        'use_session', 'random_user_agent', 'proxies',
        'download_timeout', 'verify'
    }

    def __init__(self, spider_class: Type):
        """
        初始化分析器

        Args:
            spider_class: 爬虫类（如 MySpider）
        """
        self.spider_class = spider_class

    def analyze(self) -> Dict[str, Set[str]]:
        """
        分析爬虫类，返回每个回调函数需要的参数

        Returns:
            Dict[str, Set[str]]: 回调函数名 -> 需要的参数集合
            例如: {'parse_list': {'category_id', 'shop_name'}}
        """
        try:
            # 获取源代码
            source = inspect.getsource(self.spider_class)

            # 解析 AST
            tree = ast.parse(source)

            # 查找目标类的定义节点（通过类名匹配，而不是第一个遇到的类）
            class_node = None
            target_class_name = self.spider_class.__name__
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == target_class_name:
                    class_node = node
                    break

            if not class_node:
                log.warning(f"[智能上下文] 无法找到类定义: {target_class_name}")
                return {}

            # 分析每个方法
            result = {}
            for node in class_node.body:
                if isinstance(node, ast.FunctionDef):
                    method_name = node.name
                    # 跳过私有方法和特殊方法
                    if method_name.startswith('_'):
                        continue

                    # 分析方法中访问的 request 属性
                    used_attrs = self._analyze_method(node)

                    if used_attrs:
                        result[method_name] = used_attrs

            return result

        except Exception as e:
            log.warning(f"[智能上下文] 静态分析失败: {e}")
            return {}

    def build_callback_graph(self) -> Dict[str, Set[str]]:
        """
        构建回调依赖关系图

        Returns:
            Dict[str, Set[str]]: 回调函数名 -> yield 的回调函数集合
            例如: {'parse_list': {'parse_detail', 'parse_product'}}
        """
        try:
            # 获取源代码
            source = inspect.getsource(self.spider_class)

            # 解析 AST
            tree = ast.parse(source)

            # 查找目标类的定义节点（通过类名匹配，而不是第一个遇到的类）
            class_node = None
            target_class_name = self.spider_class.__name__
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == target_class_name:
                    class_node = node
                    break

            if not class_node:
                return {}

            # 分析每个方法的 yield 语句
            graph = {}
            for node in class_node.body:
                if isinstance(node, ast.FunctionDef):
                    method_name = node.name
                    # 跳过私有方法和特殊方法
                    if method_name.startswith('_'):
                        continue

                    # 分析方法中 yield 的回调
                    yielded_callbacks = self._analyze_yields(node)

                    if yielded_callbacks:
                        graph[method_name] = yielded_callbacks

            return graph

        except Exception as e:
            log.warning(f"[智能上下文] 构建回调依赖图失败: {e}")
            return {}

    def compute_transitive_needs(
        self, callback_graph: Dict[str, Set[str]], param_needs: Dict[str, Set[str]]
    ) -> Dict[str, Set[str]]:
        """
        递归计算每个回调需要传递的所有参数（包括后续回调需要的）

        Args:
            callback_graph: 回调依赖图
            param_needs: 每个回调自己需要的参数

        Returns:
            Dict[str, Set[str]]: 回调函数名 -> 传递性参数需求
        """
        transitive_needs = {}

        def dfs(callback_name: str, visited: Set[str]) -> Set[str]:
            """
            深度优先搜索计算传递性需求

            Args:
                callback_name: 当前回调名
                visited: 已访问的回调集合（用于循环检测）

            Returns:
                Set[str]: 当前回调需要传递的所有参数
            """
            # 循环检测：如果已访问过，说明遇到循环依赖
            if callback_name in visited:
                # 返回当前回调自己需要的参数（而不是空集合）
                # 这样可以确保循环依赖中每个回调至少能获得自己需要的参数
                return param_needs.get(callback_name, set()).copy()

            # 如果已计算过，直接返回缓存结果
            if callback_name in transitive_needs:
                return transitive_needs[callback_name]

            # 标记为已访问
            visited.add(callback_name)

            # 1. 当前回调自己需要的参数
            current_needs = param_needs.get(callback_name, set()).copy()

            # 2. 递归获取所有后续回调需要的参数
            next_callbacks = callback_graph.get(callback_name, set())
            for next_callback in next_callbacks:
                # 递归计算后续回调的需求（传递同一个 visited 以正确检测循环）
                next_needs = dfs(next_callback, visited)
                # 取并集（处理条件分支）
                current_needs.update(next_needs)

            # 保存结果
            transitive_needs[callback_name] = current_needs
            return current_needs

        # 收集所有出现过的回调名（包括被 yield 的回调）
        all_callbacks = set()
        all_callbacks.update(param_needs.keys())
        all_callbacks.update(callback_graph.keys())
        # 添加所有被 yield 的回调（可能不在 param_needs 或 callback_graph 的键中）
        for yielded_set in callback_graph.values():
            all_callbacks.update(yielded_set)

        # 对每个回调进行 DFS
        # 注意: 每次 DFS 调用使用独立的 visited 集合，因为：
        # 1. visited 用于检测单次 DFS 中的循环依赖（A→B→C→A）
        # 2. transitive_needs 缓存避免了重复计算
        # 3. 共享 visited 会导致后续 DFS 误判为循环（因为节点已在全局 visited 中）
        for callback_name in all_callbacks:
            if callback_name not in transitive_needs:
                dfs(callback_name, set())  # 每次使用新的 visited 集合

        return transitive_needs

    def _analyze_method(self, method_node: ast.FunctionDef) -> Set[str]:
        """
        分析单个方法，检测访问了 request 的哪些属性

        Args:
            method_node: 方法的 AST 节点

        Returns:
            Set[str]: 访问的属性名集合
        """
        used_attrs = set()

        # 遍历方法中的所有节点
        for node in ast.walk(method_node):
            # 查找属性访问节点（如 request.category_id）
            if isinstance(node, ast.Attribute):
                # 检查是否是 request.xxx 的访问形式
                if self._is_request_attribute(node):
                    attr_name = node.attr

                    # 过滤保留字段
                    if not self._is_reserved_attr(attr_name):
                        used_attrs.add(attr_name)

        return used_attrs

    def _analyze_yields(self, method_node: ast.FunctionDef) -> Set[str]:
        """
        分析单个方法中 yield 了哪些回调函数

        Args:
            method_node: 方法的 AST 节点

        Returns:
            Set[str]: yield 的回调函数名集合
        """
        yielded_callbacks = set()

        # 遍历方法中的所有节点
        for node in ast.walk(method_node):
            # 查找 yield 语句
            if isinstance(node, (ast.Yield, ast.YieldFrom)):
                if node.value and isinstance(node.value, ast.Call):
                    # 情况1: 查找 callback= 关键字参数（推荐方式）
                    for keyword in node.value.keywords:
                        if keyword.arg == 'callback':
                            # 获取回调函数名
                            callback_name = self._extract_callback_name(keyword.value)
                            if callback_name:
                                yielded_callbacks.add(callback_name)

                    # 情况2: 检查位置参数（不推荐，但理论上可能存在）
                    # Request 构造函数签名: __init__(url, retry_times, priority, parser_name, callback, ...)
                    # callback 是第5个位置参数（索引4）
                    if len(node.value.args) >= 5:
                        callback_arg = node.value.args[4]  # 第5个位置参数
                        callback_name = self._extract_callback_name(callback_arg)
                        if callback_name:
                            yielded_callbacks.add(callback_name)

        return yielded_callbacks

    def _extract_callback_name(self, node) -> str:
        """
        从 AST 节点中提取回调函数名

        Args:
            node: AST 节点

        Returns:
            str: 回调函数名，如果无法提取则返回 None

        注意:
            本方法只支持简单的回调引用形式：
            - self.parse_detail (推荐)
            - parse_detail (直接函数名)

            不支持复杂表达式：
            - lambda 函数: lambda r: ...
            - 条件表达式: self.parse_a if xxx else self.parse_b
            - 变量引用: callback = self.parse; yield Request(url, callback=callback)

            这是静态分析的固有局限性，实际使用中这些复杂形式很少见。
        """
        # 情况1: self.parse_detail (最常见)
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == 'self':
                return node.attr

        # 情况2: 直接的函数名（不常见）
        if isinstance(node, ast.Name):
            return node.id

        # 其他复杂形式无法静态分析
        return None

    def _is_request_attribute(self, node: ast.Attribute) -> bool:
        """
        判断一个属性访问节点是否是 request.xxx 的形式

        Args:
            node: AST 属性节点

        Returns:
            bool: 是否是 request.xxx
        """
        # 检查 node.value 是否是名为 'request' 的变量
        if isinstance(node.value, ast.Name):
            return node.value.id == 'request'
        return False

    def _is_reserved_attr(self, attr_name: str) -> bool:
        """
        判断属性名是否是框架保留字段

        Args:
            attr_name: 属性名

        Returns:
            bool: 是否是保留字段
        """
        # 保留字段
        if attr_name in self._RESERVED_ATTRS:
            return True

        # 私有属性（以 _ 开头）
        if attr_name.startswith('_'):
            return True

        return False
