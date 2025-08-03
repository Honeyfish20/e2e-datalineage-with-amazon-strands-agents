# 故障排除指南

## 概述

本指南提供了Enhanced Lineage Agent常见问题的诊断和解决方案，帮助用户快速识别和解决系统问题。

## 诊断工具

### 1. 系统健康检查

```bash
# 运行完整的系统健康检查
python -m enhanced_lineage_agent.utils.diagnostics --full-check

# 检查特定组件
python -m enhanced_lineage_agent.utils.diagnostics --component context_extractor
python -m enhanced_lineage_agent.utils.diagnostics --component job_validator
python -m enhanced_lineage_agent.utils.diagnostics --component lineage_validator
```

### 2. 配置验证

```bash
# 验证配置文件
python enhanced_lineage_agent/deployment/config_manager.py \
  --environment dev --action validate

# 检查环境变量
python -c "
import os
from enhanced_lineage_agent.config import get_config
config = get_config()
print('Configuration loaded successfully')
print(f'AWS Region: {config.aws_region}')
print(f'DynamoDB Table: {config.dynamodb.job_mapping_table}')
"
```

### 3. 连接测试

```bash
# 测试AWS连接
aws sts get-caller-identity

# 测试DynamoDB连接
aws dynamodb describe-table --table-name enhanced-lineage-agent-job-mappings-dev

# 测试S3连接
aws s3 ls enhanced-lineage-agent-lineage-data-dev-$(aws sts get-caller-identity --query Account --output text)

# 测试Bedrock连接
aws bedrock list-foundation-models --region us-east-1
```

## 常见问题和解决方案

### 1. 上下文识别问题

#### 问题：上下文识别失败或不准确

**症状**：
- 系统无法识别执行环境
- 上下文类型显示为"unknown"
- 上下文ID生成失败

**诊断步骤**：

```bash
# 1. 检查环境变量
env | grep -E "(SAGEMAKER|AIRFLOW|JPY|SM_|AIRFLOW_CTX)"

# 2. 检查进程信息
ps aux | grep python

# 3. 手动测试上下文提取
python -c "
from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor
extractor = ExecutionContextExtractor()
try:
    context = extractor.extract_context()
    print(f'Context ID: {context.context_id}')
    print(f'Environment: {context.environment_type.value}')
    print(f'Process ID: {context.process_id}')
    print(f'Working Dir: {context.working_directory}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
"

# 4. 检查日志
grep -i "context" /var/log/lineage_agent.log | tail -20
```

**解决方案**：

1. **SageMaker环境识别失败**：
```bash
# 确保SageMaker环境变量存在
export SM_CURRENT_INSTANCE_TYPE=ml.t3.medium
export SAGEMAKER_NOTEBOOK_INSTANCE_NAME=your-notebook-name

# 或在代码中手动设置
python -c "
import os
os.environ['SM_CURRENT_INSTANCE_TYPE'] = 'ml.t3.medium'
from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor
extractor = ExecutionContextExtractor()
context = extractor.extract_context()
print(f'Environment: {context.environment_type.value}')
"
```

2. **Airflow环境识别失败**：
```bash
# 确保Airflow环境变量存在
export AIRFLOW_CTX_DAG_ID=your_dag_id
export AIRFLOW_CTX_TASK_ID=your_task_id
export AIRFLOW_CTX_EXECUTION_DATE=2024-01-01T00:00:00+00:00
```

3. **权限问题**：
```bash
# 检查psutil权限
python -c "
import psutil
try:
    process = psutil.Process()
    print(f'Process name: {process.name()}')
    print(f'Parent process: {process.parent()}')
except Exception as e:
    print(f'Permission error: {e}')
"
```

### 2. Job ID验证问题

#### 问题：Job ID验证失败或置信度低

**症状**：
- Job ID验证返回False
- 置信度分数低于阈值
- 验证过程抛出异常

**诊断步骤**：

```bash
# 1. 检查Job是否存在
aws glue get-job --job-name your-job-name

# 2. 检查Job Run是否存在
aws glue get-job-run --job-name your-job-name --run-id your-run-id

# 3. 手动测试验证
python -c "
from enhanced_lineage_agent.tools.job_validator import JobIDValidator
from enhanced_lineage_agent.models.execution_context import ExecutionContext, EnvironmentType
from datetime import datetime, timezone

# 创建测试上下文
context = ExecutionContext(
    context_id='test_context',
    environment_type=EnvironmentType.STANDALONE_SCRIPT,
    timestamp=datetime.now(timezone.utc),
    process_id=12345,
    command_line='python test.py',
    working_directory='/test'
)

validator = JobIDValidator()
try:
    result = validator.validate_job_run_id('your-job-name', 'your-run-id', context)
    print(f'Valid: {result[\"is_valid\"]}')
    print(f'Confidence: {result[\"confidence_score\"]}')
    print(f'Recommendation: {result[\"recommendation\"]}')
    if 'reason' in result:
        print(f'Reason: {result[\"reason\"]}')
except Exception as e:
    print(f'Validation error: {e}')
    import traceback
    traceback.print_exc()
"

# 4. 检查时间差
python -c "
import boto3
from datetime import datetime, timezone
glue = boto3.client('glue')
try:
    response = glue.get_job_run(JobName='your-job-name', RunId='your-run-id')
    job_start = response['JobRun']['StartedOn']
    now = datetime.now(timezone.utc)
    time_diff = abs((job_start - now).total_seconds())
    print(f'Job started: {job_start}')
    print(f'Current time: {now}')
    print(f'Time difference: {time_diff} seconds')
except Exception as e:
    print(f'Error: {e}')
"
```

**解决方案**：

1. **Job不存在**：
```bash
# 检查Job名称是否正确
aws glue list-jobs --query 'JobNames' | grep your-job-name

# 检查Job Run ID是否正确
aws glue get-job-runs --job-name your-job-name --query 'JobRuns[0].Id'
```

2. **时间差过大**：
```bash
# 调整时间容忍度
export VALIDATION_TIME_TOLERANCE_SECONDS=600  # 10分钟

# 或在配置文件中调整
echo "validation:
  time_tolerance_seconds: 600" >> enhanced_lineage_agent/config/config-dev.yaml
```

3. **置信度阈值过高**：
```bash
# 降低置信度阈值
export VALIDATION_MIN_CONFIDENCE_SCORE=0.5

# 或临时禁用验证
export VALIDATION_ENABLE_PARAMETER_VALIDATION=false
export VALIDATION_ENABLE_ENVIRONMENT_VALIDATION=false
```

4. **AWS权限问题**：
```bash
# 检查Glue权限
aws iam simulate-principal-policy \
  --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
  --action-names glue:GetJob glue:GetJobRun \
  --resource-arns "*"
```

### 3. 日志流选择问题

#### 问题：无法找到或选择正确的日志流

**症状**：
- 找不到日志流
- 选择了错误的日志流
- 日志流选择超时

**诊断步骤**：

```bash
# 1. 检查日志组是否存在
aws logs describe-log-groups --log-group-name-prefix /aws-glue/jobs

# 2. 检查日志流
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/logs-v2 \
  --log-stream-name-prefix your-job-run-id

# 3. 手动测试日志流选择
python -c "
from enhanced_lineage_agent.tools.log_stream_selector import IntelligentLogStreamSelector
from enhanced_lineage_agent.models.execution_context import ExecutionContext, EnvironmentType
from datetime import datetime, timezone

# 创建测试上下文
context = ExecutionContext(
    context_id='test_context',
    environment_type=EnvironmentType.STANDALONE_SCRIPT,
    timestamp=datetime.now(timezone.utc),
    process_id=12345,
    command_line='python test.py',
    working_directory='/test'
)

# 模拟可用的日志流
available_streams = [
    {
        'logGroup': '/aws-glue/jobs/logs-v2',
        'logStreamName': 'your-job-run-id-driver',
        'lastEventTime': int(datetime.now(timezone.utc).timestamp() * 1000),
        'storedBytes': 1024
    }
]

selector = IntelligentLogStreamSelector()
try:
    result = selector.select_log_stream('your-job-name', context, available_streams)
    print(f'Selected stream: {result[\"selected_stream\"][\"logStreamName\"]}')
    print(f'Score: {result[\"score\"]}')
    print(f'Confidence: {result[\"confidence\"]}')
    print(f'Reasons: {result[\"reasons\"]}')
except Exception as e:
    print(f'Selection error: {e}')
    import traceback
    traceback.print_exc()
"
```

**解决方案**：

1. **日志组不存在**：
```bash
# 检查Glue作业是否已运行
aws glue get-job-runs --job-name your-job-name --max-results 5

# 检查CloudWatch Logs权限
aws iam simulate-principal-policy \
  --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
  --action-names logs:DescribeLogGroups logs:DescribeLogStreams logs:FilterLogEvents \
  --resource-arns "*"
```

2. **日志流命名不匹配**：
```bash
# 检查实际的日志流命名模式
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/logs-v2 \
  --order-by LastEventTime \
  --descending \
  --max-items 10

# 调整日志流模式匹配
python -c "
# 检查不同的命名模式
patterns = ['{job_run_id}-driver', '{job_run_id}', 'driver-{job_run_id}']
job_run_id = 'your-job-run-id'
for pattern in patterns:
    expected_name = pattern.format(job_run_id=job_run_id)
    print(f'Pattern: {pattern} -> {expected_name}')
"
```

3. **时间窗口问题**：
```bash
# 扩大时间搜索窗口
python script/glue/extract-lineage-to-s3.py \
  --job-name your-job-name \
  --job-run-id your-job-run-id \
  --start-time $(date -d '2 hours ago' --iso-8601) \
  --region us-east-1 \
  --output-path s3://your-bucket/test/
```

### 4. 血缘合并问题

#### 问题：血缘合并被阻止或失败

**症状**：
- 血缘验证失败
- 合并过程被阻止
- 上下文不匹配错误

**诊断步骤**：

```bash
# 1. 检查血缘文件
aws s3 ls s3://your-bucket/lineage-reports/glue-jobs/ --recursive | tail -5
aws s3 ls s3://your-bucket/lineage/redshift/ --recursive | tail -5

# 2. 下载并检查血缘文件内容
aws s3 cp s3://your-bucket/lineage-reports/glue-jobs/latest.json /tmp/glue_lineage.json
aws s3 cp s3://your-bucket/lineage/redshift/latest.json /tmp/redshift_lineage.json

# 检查上下文信息
python -c "
import json

# 检查Glue血缘文件
with open('/tmp/glue_lineage.json', 'r') as f:
    glue_data = json.load(f)

print('Glue Lineage Context:')
if 'metadata' in glue_data and 'execution_context' in glue_data['metadata']:
    ctx = glue_data['metadata']['execution_context']
    print(f'  Context ID: {ctx.get(\"context_id\", \"Not found\")}')
    print(f'  Environment: {ctx.get(\"environment_type\", \"Not found\")}')
    print(f'  Timestamp: {ctx.get(\"timestamp\", \"Not found\")}')
else:
    print('  No execution context found in metadata')

# 检查事件中的上下文
events_with_context = 0
for event in glue_data.get('events', []):
    if '_metadata' in event and 'execution_context' in event['_metadata']:
        events_with_context += 1

print(f'  Events with context: {events_with_context}/{len(glue_data.get(\"events\", []))}')

# 检查Redshift血缘文件
with open('/tmp/redshift_lineage.json', 'r') as f:
    redshift_data = json.load(f)

print('\\nRedshift Lineage Context:')
if 'metadata' in redshift_data and 'execution_context' in redshift_data['metadata']:
    ctx = redshift_data['metadata']['execution_context']
    print(f'  Context ID: {ctx.get(\"context_id\", \"Not found\")}')
    print(f'  Environment: {ctx.get(\"environment_type\", \"Not found\")}')
    print(f'  Timestamp: {ctx.get(\"timestamp\", \"Not found\")}')
else:
    print('  No execution context found in metadata')
"

# 3. 手动测试血缘验证
python -c "
from enhanced_lineage_agent.integrations.enhanced_table_merger import EnhancedTableLineageMerger
import json

merger = EnhancedTableLineageMerger(enable_validation=True)

# 加载血缘数据
with open('/tmp/glue_lineage.json', 'r') as f:
    glue_data = json.load(f)
with open('/tmp/redshift_lineage.json', 'r') as f:
    redshift_data = json.load(f)

try:
    validation_result = merger.validate_lineage_compatibility(glue_data, redshift_data)
    print(f'Validation result: {validation_result[\"is_valid\"]}')
    print(f'Confidence: {validation_result[\"confidence_score\"]}')
    if 'issues' in validation_result:
        print(f'Issues: {validation_result[\"issues\"]}')
    if 'recommendations' in validation_result:
        print(f'Recommendations: {validation_result[\"recommendations\"]}')
except Exception as e:
    print(f'Validation error: {e}')
    import traceback
    traceback.print_exc()
"
```

**解决方案**：

1. **上下文信息缺失**：
```bash
# 重新运行血缘提取，确保启用上下文感知
python script/glue/extract-lineage-to-s3.py \
  --job-name your-job-name \
  --job-run-id your-job-run-id \
  --region us-east-1 \
  --output-path s3://your-bucket/lineage/ \
  --enable-context-awareness  # 如果支持此参数
```

2. **上下文不匹配**：
```bash
# 检查时间差
python -c "
from datetime import datetime
import json

with open('/tmp/glue_lineage.json', 'r') as f:
    glue_data = json.load(f)
with open('/tmp/redshift_lineage.json', 'r') as f:
    redshift_data = json.load(f)

glue_time = glue_data['metadata']['execution_context']['timestamp']
redshift_time = redshift_data['metadata']['execution_context']['timestamp']

glue_dt = datetime.fromisoformat(glue_time.replace('Z', '+00:00'))
redshift_dt = datetime.fromisoformat(redshift_time.replace('Z', '+00:00'))

time_diff = abs((glue_dt - redshift_dt).total_seconds())
print(f'Time difference: {time_diff} seconds')

if time_diff > 3600:  # 1小时
    print('WARNING: Large time difference between lineage files')
    print('Consider adjusting time tolerance or re-extracting lineage data')
"

# 临时调整验证阈值
export VALIDATION_MIN_CONFIDENCE_SCORE=0.3
```

3. **强制合并（仅用于调试）**：
```bash
# 临时禁用验证
python -c "
from enhanced_lineage_agent.integrations.enhanced_table_merger import EnhancedTableLineageMerger

# 创建禁用验证的合并器
merger = EnhancedTableLineageMerger(enable_validation=False)
result_path = merger.process_lineage()
print(f'Merge completed without validation: {result_path}')
"
```

### 5. AWS服务连接问题

#### 问题：无法连接到AWS服务

**症状**：
- AWS API调用失败
- 权限被拒绝错误
- 网络连接超时

**诊断步骤**：

```bash
# 1. 检查AWS凭证
aws sts get-caller-identity

# 2. 检查网络连接
curl -I https://dynamodb.us-east-1.amazonaws.com
curl -I https://s3.us-east-1.amazonaws.com
curl -I https://bedrock-runtime.us-east-1.amazonaws.com

# 3. 检查区域设置
echo $AWS_DEFAULT_REGION
aws configure get region

# 4. 测试各个服务
aws dynamodb list-tables --region us-east-1
aws s3 ls --region us-east-1
aws glue list-jobs --region us-east-1 --max-results 1
aws bedrock list-foundation-models --region us-east-1
```

**解决方案**：

1. **凭证问题**：
```bash
# 重新配置AWS凭证
aws configure

# 或使用IAM角色
export AWS_ROLE_ARN=arn:aws:iam::123456789012:role/your-role
export AWS_WEB_IDENTITY_TOKEN_FILE=/path/to/token

# 检查凭证有效期
aws sts get-session-token
```

2. **权限问题**：
```bash
# 检查当前用户权限
aws iam get-user
aws iam list-attached-user-policies --user-name your-username
aws iam list-user-policies --user-name your-username

# 检查角色权限（如果使用角色）
aws iam get-role --role-name your-role-name
aws iam list-attached-role-policies --role-name your-role-name
```

3. **网络问题**：
```bash
# 检查VPC端点（如果在VPC中）
aws ec2 describe-vpc-endpoints

# 检查安全组规则
aws ec2 describe-security-groups --group-ids sg-your-security-group

# 检查路由表
aws ec2 describe-route-tables
```

### 6. 性能问题

#### 问题：系统响应缓慢或超时

**症状**：
- 上下文提取耗时过长
- Job ID验证超时
- 血缘合并处理缓慢

**诊断步骤**：

```bash
# 1. 性能测试
python -c "
import time
from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor

# 测试上下文提取性能
start_time = time.time()
extractor = ExecutionContextExtractor()
for i in range(10):
    context = extractor.extract_context()
end_time = time.time()

avg_time = (end_time - start_time) / 10
print(f'Average context extraction time: {avg_time:.2f} seconds')

if avg_time > 1.0:
    print('WARNING: Context extraction is slow')
"

# 2. 检查系统资源
top -p $(pgrep -f python)
free -h
df -h

# 3. 检查网络延迟
ping dynamodb.us-east-1.amazonaws.com
ping s3.us-east-1.amazonaws.com
```

**解决方案**：

1. **优化配置**：
```bash
# 减少重试次数
export ERROR_RECOVERY_MAX_RETRIES=2
export ERROR_RECOVERY_RETRY_DELAY_SECONDS=3

# 增加超时时间
export AWS_DEFAULT_TIMEOUT=60
export AWS_MAX_ATTEMPTS=3
```

2. **缓存优化**：
```bash
# 启用本地缓存
export ENABLE_LOCAL_CACHE=true
export CACHE_TTL_SECONDS=300
```

3. **并发优化**：
```bash
# 调整并发设置
export MAX_CONCURRENT_REQUESTS=5
export CONNECTION_POOL_SIZE=10
```

## 日志分析

### 1. 日志位置

```bash
# 应用日志
tail -f /var/log/lineage_agent.log

# Lambda日志
aws logs tail /aws/lambda/enhanced-lineage-agent-context-aware-agent-dev --follow

# 系统日志
tail -f /var/log/syslog | grep lineage
```

### 2. 有用的日志查询

```bash
# 错误日志
grep "ERROR" /var/log/lineage_agent.log | tail -20

# 上下文相关日志
grep -i "context" /var/log/lineage_agent.log | tail -20

# 验证相关日志
grep -i "validation" /var/log/lineage_agent.log | tail -20

# 性能相关日志
grep -E "(duration|time|performance)" /var/log/lineage_agent.log | tail -20

# 特定时间范围的日志
awk '/2024-01-01 10:00:00/,/2024-01-01 11:00:00/' /var/log/lineage_agent.log
```

### 3. 日志级别调整

```bash
# 临时启用调试日志
export LOGGING_LEVEL=DEBUG

# 或修改配置文件
echo "logging:
  level: DEBUG" >> enhanced_lineage_agent/config/config-dev.yaml
```

## 监控和告警

### 1. 检查CloudWatch指标

```bash
# 获取指标摘要
python -c "
from enhanced_lineage_agent.monitoring.simple_monitoring import SimpleMonitoring
monitoring = SimpleMonitoring()
summary = monitoring.get_metrics_summary(24)  # 最近24小时
print('Metrics Summary:')
for metric, data in summary.items():
    print(f'  {metric}: {data}')
"

# 查看特定指标
aws cloudwatch get-metric-statistics \
  --namespace EnhancedLineageAgent \
  --metric-name ContextIdentificationSuccess \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Sum,Average
```

### 2. 检查告警状态

```bash
# 查看告警状态
aws cloudwatch describe-alarms \
  --alarm-names enhanced-lineage-agent-high-error-rate-dev

# 查看告警历史
aws cloudwatch describe-alarm-history \
  --alarm-name enhanced-lineage-agent-high-error-rate-dev \
  --max-records 10
```

## 紧急恢复程序

### 1. 系统完全故障

```bash
# 1. 停止所有相关进程
pkill -f "enhanced_lineage_agent"

# 2. 检查系统资源
free -h
df -h
ps aux | grep python

# 3. 重启服务
systemctl restart your-lineage-service  # 如果使用systemd

# 4. 验证恢复
python -c "
from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor
extractor = ExecutionContextExtractor()
context = extractor.extract_context()
print(f'System recovered: {context.context_id}')
"
```

### 2. 数据损坏恢复

```bash
# 1. 从备份恢复DynamoDB表
aws dynamodb restore-table-from-backup \
  --target-table-name enhanced-lineage-agent-job-mappings-dev-restored \
  --backup-arn arn:aws:dynamodb:us-east-1:123456789012:table/enhanced-lineage-agent-job-mappings-dev/backup/01234567890123-abcdefgh

# 2. 恢复S3数据
aws s3 sync s3://your-backup-bucket/lineage-data/ s3://enhanced-lineage-agent-lineage-data-dev/

# 3. 验证数据完整性
python -c "
import boto3
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('enhanced-lineage-agent-job-mappings-dev')
response = table.scan(Limit=10)
print(f'Table contains {response[\"Count\"]} items (sample)')
"
```

### 3. 配置回滚

```bash
# 1. 恢复配置文件
git checkout HEAD~1 -- enhanced_lineage_agent/config/

# 2. 重新加载配置
python -c "
from enhanced_lineage_agent.deployment.config_manager import get_config_manager
config_manager = get_config_manager('dev')
config = config_manager.load_config()
print('Configuration reloaded successfully')
"

# 3. 重启应用
# 根据部署方式重启相应服务
```

## 联系支持

如果以上解决方案都无法解决问题，请收集以下信息并联系技术支持：

### 收集诊断信息

```bash
# 创建诊断报告
python -c "
import json
import sys
import os
from datetime import datetime
from enhanced_lineage_agent.utils.diagnostics import create_diagnostic_report

report = create_diagnostic_report()
report_file = f'diagnostic_report_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.json'

with open(report_file, 'w') as f:
    json.dump(report, f, indent=2, default=str)

print(f'Diagnostic report created: {report_file}')
"

# 收集日志
tar -czf logs_$(date +%Y%m%d_%H%M%S).tar.gz /var/log/lineage_agent.log*

# 收集配置
tar -czf config_$(date +%Y%m%d_%H%M%S).tar.gz enhanced_lineage_agent/config/
```

### 支持信息模板

```
问题描述：
[详细描述遇到的问题]

环境信息：
- 环境：[dev/test/prod]
- AWS区域：[us-east-1]
- Python版本：[3.9.x]
- 系统版本：[Ubuntu 20.04]

重现步骤：
1. [步骤1]
2. [步骤2]
3. [步骤3]

错误信息：
[粘贴完整的错误信息和堆栈跟踪]

已尝试的解决方案：
[列出已经尝试过的解决方案]

附件：
- 诊断报告：diagnostic_report_xxx.json
- 日志文件：logs_xxx.tar.gz
- 配置文件：config_xxx.tar.gz
```

---

通过遵循本故障排除指南，您应该能够诊断和解决Enhanced Lineage Agent的大部分常见问题。如果问题仍然存在，请不要犹豫联系技术支持团队。