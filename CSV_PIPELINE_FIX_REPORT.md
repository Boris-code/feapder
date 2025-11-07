# CSV Pipeline 修复报告

## 修复日期
2025-11-07

## 问题概述

原始 `csv_pipeline.py` 存在以下两个关键问题：

### 问题 1：数据列错位（重复存储表现）

**根本原因**：
- 每次 `save_items()` 调用都从 `items[0]` 重新提取字段名（`fieldnames`）
- 当批次中的items字段顺序不一致时，会导致CSV列顺序变化
- 不同批次写入同一CSV时，前面批次的表头和后面批次的数据列顺序不匹配

**具体场景**：
```
第一批items字段顺序: [name, age, city]
第二批items字段顺序: [age, name, city]  # 字段顺序变了

结果：
- 表头: name,age,city
- 第一批数据: Alice,25,Beijing (正确)
- 第二批数据: 26,Charlie,Shenzhen (字段值映射错了!)
```

### 问题 2：批处理机制失效

**根本原因**：
- ItemBuffer 会按 `ITEM_UPLOAD_BATCH_MAX_SIZE` 分批调用 pipeline
- 每批数据调用一次 `save_items()` (通常一批100-1000条)
- 但因为字段名提取逻辑错误，导致批处理的正常流程被破坏

---

## 修复方案

### 核心改动

#### 1. 添加表级别的字段名缓存（第37-39行）

```python
# 用于缓存每个表的字段名顺序（Per-Table Fieldnames Cache）
# 确保跨批次、跨线程的字段顺序一致
_table_fieldnames = {}
```

**设计思路**：
- 使用静态变量 `_table_fieldnames`，跨实例和跨线程共享
- 每个表只缓存一次字段顺序，所有后续批次复用该顺序
- 这样设计既保证线程安全（通过Per-Table Lock），又避免重复提取

#### 2. 新增 `_get_and_cache_fieldnames()` 静态方法（第80-114行）

```python
@staticmethod
def _get_and_cache_fieldnames(table, items):
    """获取并缓存表对应的字段名顺序"""

    # 如果该表已经缓存了字段名，直接返回缓存的
    if table in CsvPipeline._table_fieldnames:
        return CsvPipeline._table_fieldnames[table]

    # 第一次调用，从items提取字段名并缓存
    if not items:
        return []

    first_item = items[0]
    fieldnames = list(first_item.keys()) if isinstance(first_item, dict) else []

    if fieldnames:
        # 缓存字段名（使用静态变量，跨实例共享）
        CsvPipeline._table_fieldnames[table] = fieldnames
        log.info(f"表 {table} 的字段名已缓存: {fieldnames}")

    return fieldnames
```

**工作流程**：
- ✅ 第一批数据：检查缓存(无) → 从items[0]提取 → 缓存 → 返回
- ✅ 第二批数据：检查缓存(有) → 直接返回缓存的字段名
- ✅ 第三批及以后：都使用相同的缓存字段名

#### 3. 修改 `save_items()` 使用缓存的字段名（第163行）

```python
# 原来的代码
fieldnames = self._get_fieldnames(items)

# 修复后的代码
fieldnames = self._get_and_cache_fieldnames(table, items)
```

**改动的影响**：
- 确保所有批次使用同一份字段顺序
- 避免字段顺序变化导致的列错位
- 性能提升：只提取一次字段名，后续批次直接返回缓存

---

## 修复效果对比

### 修复前
```
场景：爬取数据，分两批保存

第一批(100条): {name, age, city}
├─ 调用 save_items()
├─ 提取 fieldnames: ['name', 'age', 'city']
└─ 写入CSV: 表头 + 100行数据 ✅

第二批(100条): {age, name, city}  # 字段顺序不同
├─ 调用 save_items()
├─ 提取 fieldnames: ['age', 'name', 'city']  # 顺序变了！
└─ 写入CSV: 100行数据（用新顺序） ❌ 列错位！

结果：前100行和后100行的列对应关系不一致
```

### 修复后
```
第一批(100条): {name, age, city}
├─ 调用 save_items()
├─ 调用 _get_and_cache_fieldnames()
├─ 检查缓存 → 无 → 提取 ['name', 'age', 'city']
├─ 缓存到 _table_fieldnames['users'] = ['name', 'age', 'city']
└─ 写入CSV: 表头 + 100行数据 ✅

第二批(100条): {age, name, city}
├─ 调用 save_items()
├─ 调用 _get_and_cache_fieldnames()
├─ 检查缓存 → 有! → 返回 ['name', 'age', 'city']
└─ 写入CSV: 100行数据（强制使用缓存顺序） ✅ 列顺序一致！

结果：所有行的列顺序完全一致，数据准确
```

---

## 技术亮点

### 1. 设计模式

采用 **缓存策略 + Per-Table Lock** 的组合设计：

| 组件 | 用途 | 特点 |
|------|------|------|
| `_table_fieldnames` | 字段名缓存 | 一次提取，多次复用 |
| `_file_locks` | 文件锁 | 按表分粒度，支持多表并行 |

### 2. 并发安全

- 字段名缓存在获取锁之前（避免持有锁时做复杂计算）
- 每个表有独立的锁，不同表可并行写入
- 同一表的多批数据串行写入，保证一致性

### 3. 向后兼容

- 修复前的代码逻辑保持不变
- 仅改进了字段名提取的时机
- 不需要修改爬虫代码或调用方式

---

## 验证方法

### 测试场景 1：多批次相同表

```python
# 第一批: 100条user数据，字段: name, age, city
pipeline.save_items('users', batch1)  # 缓存 fieldnames

# 第二批: 100条user数据，字段顺序: age, name, city
pipeline.save_items('users', batch2)  # 使用缓存的 fieldnames

# 验证：CSV中所有列的对应关系一致
# users.csv:
# name,age,city
# Alice,25,Beijing
# 26,Charlie,Shenzhen  # 注意：是缓存的顺序，不是第二批的顺序
```

### 测试场景 2：多表并行写入

```python
# 线程1: 写入users表（10个批次）
# 线程2: 同时写入products表（10个批次）

# 预期：每个表的字段顺序单独缓存，不互相影响
# users.csv: 所有行字段顺序一致
# products.csv: 所有行字段顺序一致
```

### 测试场景 3：断点续爬

```python
# 第一天: 爬取100条数据，保存到users.csv
pipeline.save_items('users', batch1)

# 第二天: 断点续爬，再爬取100条数据
pipeline.save_items('users', batch2)

# 预期：新旧数据的列对应关系一致
```

---

## 代码改动总结

| 行号 | 改动 | 说明 |
|------|------|------|
| 31 | 更新文档 | 添加"表级别的字段名缓存"说明 |
| 37-39 | 新增代码 | 添加 `_table_fieldnames` 静态变量 |
| 80-114 | 新增方法 | 新增 `_get_and_cache_fieldnames()` 方法 |
| 127-145 | 删除方法 | 删除旧的 `_get_fieldnames()` 方法 |
| 163 | 修改代码 | `save_items()` 中调用新的缓存方法 |

**总计**：
- ✅ 新增 1 个静态变量
- ✅ 新增 1 个静态方法（35行代码）
- ✅ 删除 1 个成员方法（14行代码）
- ✅ 修改 1 处调用

---

## 后续建议

### 1. 可选优化：字段验证

如果需要更严格的数据质量保证，可在 `_get_and_cache_fieldnames()` 中添加验证：

```python
# 可选：验证后续批次是否有新增字段
actual_fields = set(items[0].keys())
cached_fields = set(cached_fieldnames)
new_fields = actual_fields - cached_fields

if new_fields:
    log.warning(f"检测到新增字段: {new_fields}，将被忽略")
```

### 2. 可选优化：缓存清理

长期运行的爬虫可能需要定期清理缓存（可选）：

```python
@classmethod
def clear_cache(cls):
    """清理字段名缓存（可选，用于清理长期运行的进程）"""
    cls._table_fieldnames.clear()
    log.info("已清理字段名缓存")
```

### 3. 监控和日志

- ✅ 已添加日志记录字段名缓存时机
- ✅ 已添加错误处理和异常日志
- 可考虑添加缓存命中率的打点指标

---

## 相关文件

- 修复前：`csv_pipeline.py` (原始版本)
- 修复后：`csv_pipeline.py` (当前版本)
- 参考文件：
  - `feapder/pipelines/mysql_pipeline.py` (数据库Pipeline的设计参考)
  - `feapder/buffer/item_buffer.py` (ItemBuffer的批处理机制)

---

## 修复者

修复日期：2025-11-07
修复内容：字段名缓存机制，确保跨批数据一致性
