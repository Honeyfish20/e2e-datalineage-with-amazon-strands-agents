# 部署指南

## 概述

本指南详细介绍如何在不同环境中部署Enhanced Lineage Agent，包括基础设施配置、应用部署和监控设置。

## 前提条件

### 系统要求

- Python 3.9+
- AWS CLI 2.0+
- 足够的AWS权限（见权限要求部分）

### AWS服务要求

- AWS Glue
- Amazon DynamoDB
- Amazon S3
- Amazon CloudWatch
- Amazon SNS
- Amazon Bedrock
- AWS Lambda（可选）

### 权限要求

部署用户需要以下AWS权限：

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:*",
                "dynamodb:*",
                "s3:*",
                "lambda:*",
                "iam:*",
                "logs:*",
                "cloudwatch:*",
                "sns:*",
                "bedrock:*",
                "glue:*"
            ],
            "Resource": "*"
        }
    ]
}
```

## 部署步骤

### 1. 环境准备

#### 1.1 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd enhanced-lineage-agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 1.2 配置AWS凭证

```bash
# 配置AWS CLI
aws configure

# 或设置环境变量
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

#### 1.3 验证AWS访问

```bash
# 验证AWS凭证
aws sts get-caller-identity

# 检查必要的服务可用性
aws glue list-jobs --max-results 1
aws dynamodb list-tables --max-items 1
aws s3 ls
```

### 2. 配置管理

#### 2.1 创建配置文件

```bash
# 创建配置目录
mkdir -p enhanced_lineage_agent/config

# 创建基础配置文件
cat > enhanced_lineage_agent/config/config.yaml << EOF
aws:
  region: us-east-1
  profile: default

dynamodb:
  region: us-east-1
  job_mapping_table: enhanced-lineage-agent-job-mappings-{environment}
  context_table: enhanced-lineage-agent-execution-contexts-{environment}

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

error_recovery:
  max_retries: 3
  retry_delay_seconds: 5
  enable_fallback: true

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

s3:
  lineage_bucket: enhanced-lineage-agent-lineage-data-{environment}
  region: us-east-1
  prefix: lineage
EOF
```

#### 2.2 创建环境特定配置

```bash
# 开发环境配置
cat > enhanced_lineage_agent/config/config-dev.yaml << EOF
validation:
  min_confidence_score: 0.5  # 开发环境使用较低阈值

logging:
  level: DEBUG

monitoring:
  alert_topic_arn: arn:aws:sns:us-east-1:123456789012:enhanced-lineage-agent-alerts-dev
EOF

# 生产环境配置
cat > enhanced_lineage_agent/config/config-prod.yaml << EOF
validation:
  min_confidence_score: 0.8  # 生产环境使用较高阈值

logging:
  level: WARNING

monitoring:
  alert_topic_arn: arn:aws:sns:us-east-1:123456789012:enhanced-lineage-agent-alerts-prod
EOF
```

#### 2.3 验证配置

```bash
# 验证开发环境配置
python enhanced_lineage_agent/deployment/config_manager.py \
  --environment dev --action validate

# 验证生产环境配置
python enhanced_lineage_agent/deployment/config_manager.py \
  --environment prod --action validate
```

### 3. 基础设施部署

#### 3.1 部署开发环境

```bash
python enhanced_lineage_agent/deployment/deploy.py \
  --environment dev \
  --region us-east-1 \
  --alert-email dev-alerts@yourcompany.com \
  --action deploy
```

#### 3.2 部署测试环境

```bash
python enhanced_lineage_agent/deployment/deploy.py \
  --environment test \
  --region us-east-1 \
  --alert-email test-alerts@yourcompany.com \
  --action deploy
```

#### 3.3 部署生产环境

```bash
python enhanced_lineage_agent/deployment/deploy.py \
  --environment prod \
  --region us-east-1 \
  --alert-email prod-alerts@yourcompany.com \
  --action deploy
```

#### 3.4 验证部署

```bash
# 验证基础设施部署
python enhanced_lineage_agent/deployment/deploy.py \
  --environment dev \
  --region us-east-1 \
  --action validate

# 检查CloudFormation堆栈状态
aws cloudformation describe-stacks \
  --stack-name enhanced-lineage-agent-dev \
  --query 'Stacks[0].StackStatus'

# 检查DynamoDB表
aws dynamodb describe-table \
  --table-name enhanced-lineage-agent-job-mappings-dev

# 检查S3存储桶
aws s3 ls enhanced-lineage-agent-lineage-data-dev-$(aws sts get-caller-identity --query Account --output text)
```

### 4. 应用部署

#### 4.1 创建部署包

```bash
# 创建Lambda部署包
python enhanced_lineage_agent/deployment/deploy.py \
  --environment dev \
  --region us-east-1 \
  --action create-package
```

#### 4.2 部署Lambda函数

```bash
# 部署Lambda代码
python enhanced_lineage_agent/deployment/deploy.py \
  --environment dev \
  --region us-east-1 \
  --action deploy-lambda
```

#### 4.3 测试Lambda函数

```bash
# 测试Lambda函数
aws lambda invoke \
  --function-name enhanced-lineage-agent-context-aware-agent-dev \
  --payload '{"action": "health_check"}' \
  response.json

# 查看响应
cat response.json
```

### 5. 集成现有脚本

#### 5.1 备份现有脚本

```bash
# 备份现有血缘提取脚本
cp script/glue/extract-lineage-to-s3.py script/glue/extract-lineage-to-s3.py.backup
cp script/table_lineage_merger.py script/table_lineage_merger.py.backup
```

#### 5.2 应用增强功能

```bash
# 创建迁移脚本
python -m enhanced_lineage_agent.integrations.compatibility_wrapper --create-migration

# 运行迁移
python migrate_lineage_scripts.py \
  --script-dir script \
  --no-backup  # 因为我们已经手动备份了
```

#### 5.3 验证集成

```bash
# 验证增强功能集成
python -m enhanced_lineage_agent.integrations.compatibility_wrapper --verify

# 测试增强的Glue提取器
python script/glue/extract-lineage-to-s3.py \
  --region us-east-1 \
  --job-name test-job \
  --output-path s3://your-bucket/test-lineage/ \
  --dry-run
```

## 环境特定配置

### 开发环境

```yaml
# config-dev.yaml
validation:
  min_confidence_score: 0.5
  time_tolerance_seconds: 600

logging:
  level: DEBUG
  file_path: /tmp/lineage_agent_dev.log

monitoring:
  batch_size: 10
  alert_topic_arn: arn:aws:sns:us-east-1:123456789012:dev-alerts

error_recovery:
  max_retries: 5
  enable_fallback: true
```

### 测试环境

```yaml
# config-test.yaml
validation:
  min_confidence_score: 0.7
  time_tolerance_seconds: 300

logging:
  level: INFO

monitoring:
  batch_size: 20
  alert_topic_arn: arn:aws:sns:us-east-1:123456789012:test-alerts

error_recovery:
  max_retries: 3
  enable_fallback: true
```

### 生产环境

```yaml
# config-prod.yaml
validation:
  min_confidence_score: 0.8
  time_tolerance_seconds: 180

logging:
  level: WARNING
  file_path: /var/log/lineage_agent.log

monitoring:
  batch_size: 50
  alert_topic_arn: arn:aws:sns:us-east-1:123456789012:prod-alerts

error_recovery:
  max_retries: 2
  enable_fallback: false  # 生产环境更严格
```

## 监控设置

### 1. CloudWatch仪表板

```bash
# 创建仪表板
python -c "
from enhanced_lineage_agent.monitoring.simple_monitoring import SimpleMonitoring
monitoring = SimpleMonitoring()
dashboard_url = monitoring.create_dashboard()
print(f'Dashboard URL: {dashboard_url}')
"
```

### 2. 告警配置

```bash
# 设置告警
python -c "
from enhanced_lineage_agent.monitoring.simple_monitoring import SimpleMonitoring
monitoring = SimpleMonitoring()
monitoring.setup_alarms()
print('Alarms configured successfully')
"
```

### 3. 日志配置

```bash
# 配置日志轮转
sudo tee /etc/logrotate.d/lineage-agent << EOF
/var/log/lineage_agent.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
EOF
```

## 安全配置

### 1. IAM角色和策略

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/enhanced-lineage-agent-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": [
                "arn:aws:s3:::enhanced-lineage-agent-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:FilterLogEvents"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
        }
    ]
}
```

### 2. 网络安全

```bash
# 配置VPC端点（如果在VPC中部署）
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.us-east-1.dynamodb \
  --route-table-ids rtb-12345678

aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-12345678
```

### 3. 加密配置

```bash
# 启用DynamoDB加密
aws dynamodb put-table \
  --table-name enhanced-lineage-agent-job-mappings-prod \
  --sse-specification Enabled=true,SSEType=KMS

# 启用S3存储桶加密
aws s3api put-bucket-encryption \
  --bucket enhanced-lineage-agent-lineage-data-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

## 性能优化

### 1. DynamoDB优化

```bash
# 配置DynamoDB自动扩展
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/enhanced-lineage-agent-job-mappings-prod \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 \
  --max-capacity 100

aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/enhanced-lineage-agent-job-mappings-prod \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-name enhanced-lineage-agent-read-scaling-policy \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "ScaleInCooldown": 60,
    "ScaleOutCooldown": 60,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "DynamoDBReadCapacityUtilization"
    }
  }'
```

### 2. Lambda优化

```bash
# 配置Lambda预留并发
aws lambda put-provisioned-concurrency-config \
  --function-name enhanced-lineage-agent-context-aware-agent-prod \
  --qualifier '$LATEST' \
  --provisioned-concurrency-units 10
```

### 3. 缓存配置

```bash
# 配置ElastiCache（可选）
aws elasticache create-cache-cluster \
  --cache-cluster-id enhanced-lineage-agent-cache \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1
```

## 备份和恢复

### 1. DynamoDB备份

```bash
# 启用DynamoDB时间点恢复
aws dynamodb update-continuous-backups \
  --table-name enhanced-lineage-agent-job-mappings-prod \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

# 创建按需备份
aws dynamodb create-backup \
  --table-name enhanced-lineage-agent-job-mappings-prod \
  --backup-name enhanced-lineage-agent-backup-$(date +%Y%m%d)
```

### 2. S3备份

```bash
# 启用S3版本控制
aws s3api put-bucket-versioning \
  --bucket enhanced-lineage-agent-lineage-data-prod \
  --versioning-configuration Status=Enabled

# 配置跨区域复制
aws s3api put-bucket-replication \
  --bucket enhanced-lineage-agent-lineage-data-prod \
  --replication-configuration file://replication-config.json
```

### 3. 配置备份

```bash
# 备份配置文件
tar -czf enhanced-lineage-agent-config-backup-$(date +%Y%m%d).tar.gz \
  enhanced_lineage_agent/config/

# 上传到S3
aws s3 cp enhanced-lineage-agent-config-backup-$(date +%Y%m%d).tar.gz \
  s3://your-backup-bucket/config-backups/
```

## 故障排除

### 常见部署问题

#### 1. CloudFormation部署失败

```bash
# 查看堆栈事件
aws cloudformation describe-stack-events \
  --stack-name enhanced-lineage-agent-dev

# 查看失败原因
aws cloudformation describe-stack-events \
  --stack-name enhanced-lineage-agent-dev \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
```

#### 2. Lambda函数部署失败

```bash
# 查看Lambda函数日志
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/enhanced-lineage-agent

aws logs get-log-events \
  --log-group-name /aws/lambda/enhanced-lineage-agent-context-aware-agent-dev \
  --log-stream-name $(aws logs describe-log-streams \
    --log-group-name /aws/lambda/enhanced-lineage-agent-context-aware-agent-dev \
    --order-by LastEventTime \
    --descending \
    --max-items 1 \
    --query 'logStreams[0].logStreamName' \
    --output text)
```

#### 3. 权限问题

```bash
# 检查IAM角色权限
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:role/enhanced-lineage-agent-execution-role-dev \
  --action-names dynamodb:PutItem s3:GetObject glue:GetJobRun \
  --resource-arns "*"

# 检查信任关系
aws iam get-role \
  --role-name enhanced-lineage-agent-execution-role-dev \
  --query 'Role.AssumeRolePolicyDocument'
```

### 回滚部署

```bash
# 回滚CloudFormation堆栈
python enhanced_lineage_agent/deployment/deploy.py \
  --environment dev \
  --region us-east-1 \
  --action rollback

# 或手动回滚
aws cloudformation cancel-update-stack \
  --stack-name enhanced-lineage-agent-dev
```

### 清理部署

```bash
# 完全清理部署
python enhanced_lineage_agent/deployment/deploy.py \
  --environment dev \
  --region us-east-1 \
  --action cleanup

# 手动清理资源
aws cloudformation delete-stack \
  --stack-name enhanced-lineage-agent-dev
```

## 维护和更新

### 1. 定期维护任务

```bash
# 清理旧的DynamoDB备份
aws dynamodb list-backups \
  --table-name enhanced-lineage-agent-job-mappings-prod \
  --query 'BackupSummaries[?BackupCreationDateTime<`2024-01-01`].BackupArn' \
  --output text | xargs -I {} aws dynamodb delete-backup --backup-arn {}

# 清理旧的S3版本
aws s3api list-object-versions \
  --bucket enhanced-lineage-agent-lineage-data-prod \
  --query 'Versions[?LastModified<`2024-01-01`].[Key,VersionId]' \
  --output text | while read key version; do
    aws s3api delete-object --bucket enhanced-lineage-agent-lineage-data-prod --key "$key" --version-id "$version"
  done
```

### 2. 更新部署

```bash
# 更新应用代码
git pull origin main

# 重新部署
python enhanced_lineage_agent/deployment/deploy.py \
  --environment prod \
  --region us-east-1 \
  --action deploy
```

### 3. 监控和告警维护

```bash
# 更新告警阈值
aws cloudwatch put-metric-alarm \
  --alarm-name enhanced-lineage-agent-high-error-rate-prod \
  --alarm-description "High error rate in production" \
  --metric-name ErrorOccurrence \
  --namespace EnhancedLineageAgent \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

## 最佳实践

### 1. 部署策略

- 使用蓝绿部署减少停机时间
- 在生产环境部署前先在测试环境验证
- 保持配置文件版本控制
- 定期备份关键数据和配置

### 2. 监控策略

- 设置适当的告警阈值
- 定期审查监控指标
- 建立运维响应流程
- 保持日志轮转和清理

### 3. 安全策略

- 使用最小权限原则
- 定期轮换访问密钥
- 启用审计日志
- 定期安全评估

### 4. 性能策略

- 监控资源使用情况
- 根据负载调整容量
- 优化数据库查询
- 使用缓存减少延迟

---

通过遵循本部署指南，您可以成功地在各种环境中部署Enhanced Lineage Agent，并确保系统的稳定性、安全性和性能。