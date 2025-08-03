# Enhanced Lineage Agent

## 概述

Enhanced Lineage Agent 是一个智能的数据血缘提取和管理系统，专门设计用于解决现有血缘提取器中的Job ID混淆和血缘数据交叉污染问题。通过引入执行上下文感知、智能验证和自动恢复机制，该系统能够确保血缘数据的准确性和一致性。

## 核心特性

### 🎯 执行上下文感知
- 自动识别执行环境（SageMaker、Airflow、独立脚本等）
- 生成唯一的执行上下文标识
- 跟踪和记录执行环境的详细信息

### 🔍 智能Job ID验证
- 多维度验证Job Run ID的正确性
- 时间匹配、参数匹配、环境匹配算法
- 置信度评分和推荐操作

### 🧠 智能日志流选择
- 替换简单的lastEventTime排序
- 基于执行上下文的智能选择算法
- 多维度评分（时间、环境、内容质量等）

### ✅ 血缘数据验证
- 验证不同来源血缘数据的兼容性
- 检测执行上下文冲突
- 提供合并建议和警告机制

### 🔄 错误处理和恢复
- 自动错误检测和分类
- 多种恢复策略（重试、降级、跳过等）
- 详细的错误报告和干预指南

### 📊 监控和可观测性
- 实时指标收集和报告
- CloudWatch集成
- 自动告警和通知

## 架构设计

```
Enhanced Lineage Agent
├── 执行上下文提取器 (Context Extractor)
├── Job ID验证器 (Job Validator)
├── 智能日志流选择器 (Log Stream Selector)
├── 上下文感知代理 (Context-Aware Agent)
├── 血缘验证器 (Lineage Validator)
├── 错误恢复管理器 (Error Recovery Manager)
├── 监控系统 (Monitoring System)
└── 集成模块 (Integration Modules)
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

```bash
# AWS配置
export AWS_REGION=us-east-1
export AWS_PROFILE=your-profile

# DynamoDB配置
export DYNAMODB_JOB_MAPPING_TABLE=enhanced-lineage-agent-job-mappings
export DYNAMODB_CONTEXT_TABLE=enhanced-lineage-agent-execution-contexts

# Bedrock配置
export BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
export BEDROCK_REGION=us-east-1
```

### 3. 部署基础设施

```bash
python enhanced_lineage_agent/deployment/deploy.py \
  --environment dev \
  --region us-east-1 \
  --alert-email your-email@example.com
```

### 4. 使用增强功能

#### 增强的Glue血缘提取

```python
from enhanced_lineage_agent.integrations.enhanced_glue_extractor import EnhancedGlueLineageExtractor
import boto3

session = boto3.Session()
extractor = EnhancedGlueLineageExtractor(
    session=session,
    lineage_output_path="s3://your-bucket/lineage/",
    enable_context_awareness=True
)

extractor.extract_and_save_lineage(
    job_name="your-glue-job",
    job_run_id="jr_abc123"
)
```

#### 增强的表血缘合并

```python
from enhanced_lineage_agent.integrations.enhanced_table_merger import EnhancedTableLineageMerger

merger = EnhancedTableLineageMerger(
    output_dir="/path/to/output",
    enable_validation=True
)

result_path = merger.process_lineage()
```

### 5. 迁移现有脚本

```bash
# 创建迁移脚本
python -m enhanced_lineage_agent.integrations.compatibility_wrapper --create-migration

# 运行迁移
python migrate_lineage_scripts.py --script-dir script
```

## 配置管理

### 配置文件结构

```yaml
# config/config.yaml
aws:
  region: us-east-1
  profile: default

dynamodb:
  region: us-east-1
  job_mapping_table: enhanced-lineage-agent-job-mappings
  context_table: enhanced-lineage-agent-execution-contexts

bedrock:
  model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
  region: us-east-1
  max_tokens: 4000
  temperature: 0.1

validation:
  min_confidence_score: 0.7
  time_tolerance_seconds: 300
  enable_parameter_validation: true
  enable_environment_validation: true

monitoring:
  namespace: EnhancedLineageAgent
  batch_size: 20
  alert_topic_arn: arn:aws:sns:us-east-1:123456789012:alerts

error_recovery:
  max_retries: 3
  retry_delay_seconds: 5
  enable_fallback: true

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

s3:
  lineage_bucket: enhanced-lineage-agent-lineage-data
  region: us-east-1
  prefix: lineage
```

### 环境特定配置

创建环境特定的配置文件：
- `config/config-dev.yaml` - 开发环境
- `config/config-test.yaml` - 测试环境
- `config/config-prod.yaml` - 生产环境

### 配置管理工具

```bash
# 查看配置摘要
python enhanced_lineage_agent/deployment/config_manager.py --environment dev --action show

# 导出环境变量
python enhanced_lineage_agent/deployment/config_manager.py --environment dev --action export --output env_vars.sh

# 验证配置
python enhanced_lineage_agent/deployment/config_manager.py --environment dev --action validate
```

## 监控和告警

### CloudWatch指标

系统自动收集以下指标：

- `ContextIdentificationSuccess` - 上下文识别成功率
- `JobIdValidationConfidence` - Job ID验证置信度
- `LineageMergeStatus` - 血缘合并状态
- `ErrorOccurrence` - 错误发生次数
- `ProcessingDuration` - 处理持续时间

### 告警配置

系统自动设置以下告警：

- 高错误率告警
- 低上下文识别成功率告警
- 低Job验证置信度告警
- Lambda函数错误告警

### 仪表板

访问CloudWatch仪表板查看系统状态：
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=enhanced-lineage-agent-{environment}
```

## 测试

### 运行所有测试

```bash
python enhanced_lineage_agent/tests/run_tests.py --type all
```

### 运行特定类型的测试

```bash
# 单元测试
python enhanced_lineage_agent/tests/run_tests.py --type unit

# 集成测试
python enhanced_lineage_agent/tests/run_tests.py --type integration

# 性能测试
python enhanced_lineage_agent/tests/run_tests.py --type performance
```

### 覆盖率分析

```bash
python enhanced_lineage_agent/tests/run_tests.py --coverage
```

## 故障排除

### 常见问题

#### 1. 上下文识别失败

**症状**: 系统无法正确识别执行环境

**解决方案**:
```bash
# 检查环境变量
env | grep -E "(SAGEMAKER|AIRFLOW|JPY)"

# 查看上下文提取日志
grep "context_extractor" /var/log/lineage_agent.log

# 手动测试上下文提取
python -c "
from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor
extractor = ExecutionContextExtractor()
context = extractor.extract_context()
print(f'Context ID: {context.context_id}')
print(f'Environment: {context.environment_type.value}')
"
```

#### 2. Job ID验证失败

**症状**: Job ID验证置信度低或失败

**解决方案**:
```bash
# 检查Glue作业是否存在
aws glue get-job --job-name your-job-name

# 检查Job Run是否存在
aws glue get-job-run --job-name your-job-name --run-id your-run-id

# 调整验证阈值
export VALIDATION_MIN_CONFIDENCE_SCORE=0.5
export VALIDATION_TIME_TOLERANCE_SECONDS=600
```

#### 3. 血缘合并被阻止

**症状**: 血缘合并过程被验证器阻止

**解决方案**:
```bash
# 查看验证详情
grep "validation" /var/log/lineage_agent.log

# 检查执行上下文匹配
python -c "
from enhanced_lineage_agent.tools.lineage_validator import LineageValidator
validator = LineageValidator()
# 手动验证血缘文件
"

# 临时禁用验证（仅用于调试）
export VALIDATION_ENABLE_PARAMETER_VALIDATION=false
```

#### 4. AWS权限问题

**症状**: AWS API调用失败

**解决方案**:
```bash
# 检查AWS凭证
aws sts get-caller-identity

# 检查IAM权限
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:role/enhanced-lineage-agent-role \
  --action-names glue:GetJobRun dynamodb:PutItem s3:GetObject \
  --resource-arns "*"

# 验证DynamoDB表访问
aws dynamodb describe-table --table-name enhanced-lineage-agent-job-mappings
```

### 日志分析

#### 日志位置
- 应用日志: `/var/log/lineage_agent.log`
- Lambda日志: CloudWatch Logs `/aws/lambda/enhanced-lineage-agent-*`
- 系统日志: `/var/log/syslog`

#### 有用的日志查询

```bash
# 查看错误日志
grep "ERROR" /var/log/lineage_agent.log | tail -20

# 查看上下文相关日志
grep -E "(context|Context)" /var/log/lineage_agent.log

# 查看验证相关日志
grep -E "(validation|Validation)" /var/log/lineage_agent.log

# 查看性能相关日志
grep -E "(duration|performance)" /var/log/lineage_agent.log
```

### 性能优化

#### 1. 上下文提取优化

```python
# 缓存上下文信息
from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor

# 使用单例模式避免重复提取
extractor = ExecutionContextExtractor()
context = extractor.extract_context()  # 只提取一次
```

#### 2. 批量处理优化

```python
# 批量处理血缘事件
from enhanced_lineage_agent.monitoring.simple_monitoring import SimpleMonitoring

monitoring = SimpleMonitoring()
# 设置较大的批量大小
monitoring.config.monitoring['batch_size'] = 50
```

#### 3. 缓存策略

```bash
# 启用DynamoDB缓存
export DYNAMODB_ENABLE_CACHE=true
export DYNAMODB_CACHE_TTL=300
```

## API参考

### 核心工具

#### ExecutionContextExtractor

```python
from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor

extractor = ExecutionContextExtractor()
context = extractor.extract_context()
```

#### JobIDValidator

```python
from enhanced_lineage_agent.tools.job_validator import JobIDValidator

validator = JobIDValidator()
result = validator.validate_job_run_id(job_name, job_run_id, context)
```

#### IntelligentLogStreamSelector

```python
from enhanced_lineage_agent.tools.log_stream_selector import IntelligentLogStreamSelector

selector = IntelligentLogStreamSelector()
result = selector.select_log_stream(job_name, context, available_streams)
```

### Strands工具

```python
from enhanced_lineage_agent.tools.context_extractor import extract_execution_context
from enhanced_lineage_agent.tools.job_validator import validate_job_run_id
from enhanced_lineage_agent.tools.log_stream_selector import intelligent_log_stream_selection

# 提取执行上下文
context = extract_execution_context()

# 验证Job ID
validation_result = validate_job_run_id(job_name, job_run_id, context)

# 智能日志流选择
selection_result = intelligent_log_stream_selection(job_name, context, streams)
```

## 贡献指南

### 开发环境设置

```bash
# 克隆项目
git clone <repository-url>
cd enhanced-lineage-agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -r requirements-dev.txt

# 安装pre-commit钩子
pre-commit install
```

### 代码规范

- 使用Python 3.9+
- 遵循PEP 8代码风格
- 使用类型提示
- 编写单元测试
- 添加文档字符串

### 提交流程

1. 创建功能分支
2. 编写代码和测试
3. 运行测试套件
4. 提交代码审查
5. 合并到主分支

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

## 支持

如需技术支持或有问题反馈，请：

1. 查看文档和故障排除指南
2. 搜索已知问题
3. 创建新的Issue
4. 联系开发团队

---

**Enhanced Lineage Agent** - 让数据血缘管理更智能、更可靠！