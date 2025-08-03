# 增强血缘提取器集成模块

## 概述

本模块提供了对现有血缘提取器的增强功能集成，包括：

1. **enhanced_glue_extractor.py** - 增强的Glue血缘提取器
2. **enhanced_table_merger.py** - 增强的表血缘合并器  
3. **lineage_merger_integration.py** - 血缘合并器集成工具
4. **compatibility_wrapper.py** - 兼容性包装器

## 主要功能

### 1. 上下文感知的血缘提取

- 自动识别执行环境（SageMaker、Airflow、独立脚本等）
- 生成唯一的执行上下文标识
- 智能Job ID验证和日志流选择

### 2. 血缘数据验证

- 验证不同来源血缘数据的兼容性
- 检测执行上下文冲突
- 提供合并建议和警告

### 3. 向后兼容性

- 保持与现有脚本的完全兼容
- 渐进式增强功能部署
- 自动降级到传统模式

## 使用方法

### 快速开始

```python
# 1. 验证集成
from integrations.compatibility_wrapper import CompatibilityWrapper
CompatibilityWrapper.verify_integration()

# 2. 使用增强的Glue提取器
from integrations.enhanced_glue_extractor import EnhancedGlueLineageExtractor
import boto3

session = boto3.Session()
extractor = EnhancedGlueLineageExtractor(
    session=session,
    lineage_output_path="s3://your-bucket/lineage/",
    enable_context_awareness=True
)

# 3. 使用增强的表合并器
from integrations.enhanced_table_merger import EnhancedTableLineageMerger

merger = EnhancedTableLineageMerger(
    output_dir="/path/to/output",
    enable_validation=True
)
```

### 迁移现有脚本

```bash
# 创建迁移脚本
python -m integrations.compatibility_wrapper --create-migration

# 运行迁移
python migrate_lineage_scripts.py --script-dir script
```

## 集成特性

### 增强的Glue提取器特性

- ✅ 执行上下文自动识别
- ✅ 智能Job ID验证
- ✅ 上下文感知的日志流选择
- ✅ 增强的元数据记录
- ✅ 向后兼容性保证

### 增强的表合并器特性

- ✅ 血缘数据兼容性验证
- ✅ 执行上下文匹配检查
- ✅ 智能合并策略选择
- ✅ 验证失败时的安全处理
- ✅ 详细的验证报告

### 兼容性包装器特性

- ✅ 无缝集成现有脚本
- ✅ 自动降级机制
- ✅ 迁移工具和指南
- ✅ 集成验证功能

## 配置要求

### 环境变量

```bash
# AWS配置
export AWS_REGION=us-east-1
export AWS_PROFILE=your-profile

# DynamoDB配置
export DYNAMODB_REGION=us-east-1
export DYNAMODB_JOB_MAPPING_TABLE=job-execution-mappings

# Bedrock配置
export BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
export BEDROCK_REGION=us-east-1

# 验证配置
export VALIDATION_MIN_CONFIDENCE_SCORE=0.7
export VALIDATION_TIME_TOLERANCE_SECONDS=300
```

### 依赖项

- boto3
- strands
- psutil
- pyyaml

## 部署建议

1. **测试环境验证**
   - 先在测试环境部署和验证
   - 运行集成验证工具
   - 测试各种执行场景

2. **渐进式部署**
   - 保留原始脚本作为备份
   - 逐步启用增强功能
   - 监控性能和准确性

3. **监控和维护**
   - 定期检查验证结果
   - 监控上下文识别准确性
   - 及时处理验证警告

## 故障排除

### 常见问题

1. **增强功能不可用**
   - 检查依赖是否正确安装
   - 验证配置文件是否正确
   - 查看日志文件获取详细错误信息

2. **上下文识别失败**
   - 检查执行环境是否支持
   - 验证环境变量设置
   - 查看上下文提取日志

3. **血缘合并被阻止**
   - 查看验证结果详情
   - 检查执行上下文是否匹配
   - 考虑调整验证阈值

### 日志分析

```bash
# 查看集成日志
grep "enhanced_" /var/log/lineage_agent.log

# 查看验证日志
grep "validation" /var/log/lineage_agent.log

# 查看上下文日志
grep "context" /var/log/lineage_agent.log
```

## 文件结构

```
integrations/
├── README.md                          # 本文件
├── enhanced_glue_extractor.py          # 增强的Glue提取器
├── enhanced_table_merger.py            # 增强的表合并器
├── lineage_merger_integration.py       # 合并器集成工具
└── compatibility_wrapper.py            # 兼容性包装器
```

## 版本信息

- 当前版本: 2.0_enhanced
- 兼容版本: 1.x (传统版本)
- 最后更新: 2025-01-03

## 支持

如需技术支持或有改进建议，请：
1. 查看日志文件获取详细信息
2. 运行集成验证工具
3. 参考故障排除指南
4. 联系开发团队