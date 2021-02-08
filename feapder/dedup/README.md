
# 大数据去重

## 功能

1. 基于redis临时去重：
    指定数据时效性，时效性之外的历史数据不参与去重
2. 基于内存去重：
    使用可扩展的bloomfilter方式，适用于程序运行到结束生命周期内去重
3. 基于redis永久去重
    使用可扩展的bloomfilter方式，永久去重海量数据  
4. 支持批量去重，输入列表数据，返回列表结果（如[0,1] 0不存在 1 已存在） 

## 使用方法

### 临时去重 

> 支持批量。速度快，一万条数据约0.26秒。 去重1亿条数据占用内存约1.43G，不适合永久去重

    from spider.dedup import Dedup
    
    datas = {
        "xxx": xxx,
        "xxxx": "xxxx",
    }
    
    dedup = Dedup('test', 3) # 表名为test 历史数据3秒有效期
    
    print(dedup) # <ExpireSet: dedup:expire_set:test>
    print(dedup.add(datas)) # 0 不存在
    print(dedup.get(datas)) # 1 存在
    
### 内存去重

> 支持批量。一万条数据约0.5秒。 去重一亿条数据占用内存约285MB
   
    from spider.dedup import Dedup

    datas = {
        "xxx": xxx,
        "xxxx": "xxxx",
    }
    
    dedup = Dedup(use_memory=True)
    
    print(dedup) # <ScalableBloomFilter: MemoryBitArray: 2396264597> （2396264597 为位数组的大小）
    print(dedup.add(datas)) # 0 不存在
    print(dedup.get(datas)) # 1 存在
    
### 永久去重

> 支持批量。 一万条数据约3.5秒。去重一亿条数据占用内存约285MB

    from spider.dedup import Dedup

    datas = {
        "xxx": xxx,
        "xxxx": "xxxx",
    }
    
    dedup = Dedup()
    
    print(dedup) # <ScalableBloomFilter: RedisBitArray: dedup:bloomfilter:bloomfilter>
    print(dedup.add(datas)) # 0 不存在
    print(dedup.get(datas)) # 1 存在