# Enhanced Lineage Agent 文档

欢迎使用Enhanced Lineage Agent文档！本文档提供了完整的系统使用指南、API参考和故障排除信息。

## 📚 文档目录

### 🚀 快速开始
- [README](README.md) - 项目概述和快速开始指南
- [部署指南](deployment_guide.md) - 详细的部署和配置说明

### 🔧 技术文档
- [API参考](api_reference.md) - 完整的API文档和使用示例
- [故障排除](troubleshooting.md) - 常见问题诊断和解决方案

### 📖 用户指南
- [集成指南](../integrations/README.md) - 现有系统集成说明
- [配置管理](../deployment/config_manager.py) - 配置管理工具使用

### 🧪 测试文档
- [测试指南](../tests/run_tests.py) - 测试套件运行指南

## 🎯 核心功能

### 执行上下文感知
Enhanced Lineage Agent能够自动识别和跟踪执行环境，确保血缘数据的准确性：

- **环境识别**: 自动检测SageMaker、Airflow、Jupyter等执行环境
- **上下文标识**: 为每次执行生成唯一的上下文ID
- **环境隔离**: 防止不同执行环境的血缘数据混淆

### 智能Job ID验证
通过多维度验证确保Job ID的正确性：

- **时间匹配**: 验证作业启动时间与执行上下文的一致性
- **参数匹配**: 基于作业参数验证执行环境
- **置信度评分**: 提供验证结果的置信度分数

### 智能日志流选择
替换简单的时间排序，使用智能算法选择正确的日志流：

- **多维度评分**: 考虑时间、环境、内容质量等因素
- **上下文匹配**: 基于执行上下文选择最相关的日志流
- **冲突检测**: 识别和处理日志流选择冲突

### 血缘数据验证
确保血缘合并的准确性和一致性：

- **兼容性检查**: 验证不同来源血缘数据的兼容性
- **上下文匹配**: 检查血缘数据的执行上下文一致性
- **合并策略**: 提供安全、谨慎、阻止等合并策略

## 🏗️ 系统架构

```
Enhanced Lineage Agent
├── 核心工具层 (Core Tools)
│   ├── ExecutionContextExtractor    # 执行上下文提取器
│   ├── JobIDValidator              # Job ID验证器
│   ├── IntelligentLogStreamSelector # 智能日志流选择器
│   └── LineageValidator            # 血缘验证器
├── 代理层 (Agent Layer)
│   └── ContextAwareAgent           # 上下文感知代理
├── 集成层 (Integration Layer)
│   ├── EnhancedGlueExtractor       # 增强Glue提取器
│   ├── EnhancedTableMerger         # 增强表合并器
│   └── CompatibilityWrapper        # 兼容性包装器
├── 基础设施层 (Infrastructure Layer)
│   ├── ErrorRecoveryManager        # 错误恢复管理器
│   ├── SimpleMonitoring           # 监控系统
│   └── ConfigManager              # 配置管理器
└── 数据层 (Data Layer)
    ├── ExecutionContext           # 执行上下文模型
    ├── JobExecutionMapping        # Job执行映射
    └── LineageValidationResult    # 血缘验证结果
```

## 🚀 快速开始示例

### 1. 基本使用

```python
from enhanced_lineage_agent.tools.context_extractor import extract_execution_context
from enhanced_lineage_agent.tools.job_validator import validate_job_run_id

# 提取执行上下文
context = extract_execution_context()
print(f"Context ID: {context['context_id']}")

# 验证Job ID
result = validate_job_run_id("my-job", "jr_123", context)
print(f"Validation result: {result['is_valid']}")
```

### 2. 增强的血缘提取

```python
from enhanced_lineage_agent.integrations.enhanced_glue_extractor import EnhancedGlueLineageExtractor
import boto3

session = boto3.Session()
extractor = EnhancedGlueLineageExtractor(
    session=session,
    lineage_output_path="s3://my-bucket/lineage/",
    enable_context_awareness=True
)

extractor.extract_and_save_lineage(
    job_name="my-glue-job",
    job_run_id="jr_abc123"
)
```

### 3. 增强的血缘合并

```python
from enhanced_lineage_agent.integrations.enhanced_table_merger import EnhancedTableLineageMerger

merger = EnhancedTableLineageMerger(
    output_dir="/path/to/output",
    enable_validation=True
)

result_path = merger.process_lineage()
print(f"Merged lineage saved to: {result_path}")
```

## 📋 部署检查清单

### 前置条件
- [ ] Python 3.9+ 已安装
- [ ] AWS CLI 已配置
- [ ] 必要的AWS权限已设置
- [ ] 依赖包已安装

### 基础设施部署
- [ ] DynamoDB表已创建
- [ ] S3存储桶已配置
- [ ] IAM角色和策略已设置
- [ ] CloudWatch告警已配置
- [ ] SNS主题已创建

### 应用部署
- [ ] Lambda函数已部署
- [ ] 配置文件已更新
- [ ] 环境变量已设置
- [ ] 集成测试已通过

### 验证步骤
- [ ] 上下文提取功能正常
- [ ] Job ID验证功能正常
- [ ] 血缘合并功能正常
- [ ] 监控指标正常收集
- [ ] 告警机制正常工作

## 🔍 故障排除快速参考

### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 上下文识别失败 | 环境变量缺失 | 检查并设置相应的环境变量 |
| Job ID验证失败 | 时间差过大 | 调整时间容忍度配置 |
| 血缘合并被阻止 | 上下文不匹配 | 检查血缘文件的上下文信息 |
| AWS权限错误 | IAM权限不足 | 检查并更新IAM策略 |
| 性能问题 | 配置不当 | 优化配置参数 |

### 诊断命令

```bash
# 系统健康检查
python -m enhanced_lineage_agent.utils.diagnostics --full-check

# 配置验证
python enhanced_lineage_agent/deployment/config_manager.py --environment dev --action validate

# 集成验证
python -m enhanced_lineage_agent.integrations.compatibility_wrapper --verify

# 运行测试
python enhanced_lineage_agent/tests/run_tests.py --type all
```

## 📞 获取帮助

### 文档资源
- [API参考](api_reference.md) - 详细的API文档
- [部署指南](deployment_guide.md) - 完整的部署说明
- [故障排除](troubleshooting.md) - 问题诊断和解决

### 社区支持
- GitHub Issues - 报告问题和功能请求
- 技术文档 - 查看最新的技术文档
- 示例代码 - 参考实际使用示例

### 联系方式
如需技术支持，请提供以下信息：
- 环境信息（开发/测试/生产）
- 错误信息和日志
- 重现步骤
- 已尝试的解决方案

## 🔄 版本信息

- **当前版本**: 2.0_enhanced
- **兼容版本**: 1.x (传统版本)
- **Python要求**: 3.9+
- **AWS服务**: Glue, DynamoDB, S3, CloudWatch, SNS, Bedrock

## 📈 更新日志

### v2.0_enhanced
- ✅ 新增执行上下文感知功能
- ✅ 新增智能Job ID验证
- ✅ 新增智能日志流选择
- ✅ 新增血缘数据验证
- ✅ 新增错误恢复机制
- ✅ 新增监控和告警功能
- ✅ 新增兼容性包装器
- ✅ 完整的测试套件
- ✅ 详细的文档和指南

### v1.x (传统版本)
- 基本的血缘提取功能
- 简单的时间排序日志流选择
- 基础的血缘合并功能

---

**Enhanced Lineage Agent** - 让数据血缘管理更智能、更可靠！

如有任何问题或建议，请参考相应的文档章节或联系技术支持团队。