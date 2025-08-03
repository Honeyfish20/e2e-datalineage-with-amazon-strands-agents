# Enhanced Lineage Agent

基于Amazon Strands Agents的智能数据血缘管理系统，提供跨AWS Glue、Amazon Redshift和SageMaker服务的端到端数据血缘收集、验证和智能合并功能。

## 概述

本系统解决了现有血缘提取器中的关键问题，特别是由`lastEventTime`排序导致的Job ID混淆和血缘数据交叉污染问题。它实现了一个上下文感知的智能代理，能够：

- 准确识别和关联执行上下文与正确的Glue Job实例
- 收集Glue Job、Redshift和SageMaker Notebook的完整数据血缘
- 基于真实的上下游关系智能合并多源血缘数据
- 提供统一的血缘查询、追溯和影响分析能力

## 核心特性

### 上下文感知智能
- **多环境检测**：支持独立脚本、SageMaker Notebook、Jupyter、Airflow等执行环境
- **上下文隔离**：确保不同执行上下文的血缘数据不会交叉污染
- **精确关联**：建立执行上下文与血缘数据的精确映射关系

### 智能Job ID验证
- **多维度验证**：使用时间匹配、参数匹配和环境匹配验证Job Run ID
- **置信度评分**：为Job ID选择提供置信度分数
- **冲突解决**：智能处理Job ID冲突和歧义

### 智能日志流选择
- **智能选择**：用多维度评分算法替换`lastEventTime`排序
- **质量评估**：评估日志流内容质量、大小和相关性
- **基于上下文的过滤**：基于执行上下文信息选择日志流

### 端到端血缘整合
- **多源收集**：收集来自Glue、Redshift和SageMaker的血缘
- **智能合并**：基于实际数据流关系合并血缘数据
- **跨服务关联**：自动建立不同AWS服务之间的连接

### 高级验证和质量保证
- **血缘验证**：全面验证血缘数据的一致性和完整性
- **跨服务一致性**：确保不同数据源之间的一致性
- **冲突检测**：识别和解决血缘数据冲突

## 架构

系统采用分层的智能代理架构：

```
┌─────────────────────────────────────────────────────────────┐
│                    执行上下文层                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐ │
│  │   独立脚本   │ │  SageMaker  │ │   Airflow   │ │  其他  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                上下文感知代理                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐ │
│  │   上下文    │ │   Job ID    │ │   日志流    │ │ 血缘   │ │
│  │   提取器    │ │   验证器    │ │   选择器    │ │ 合并器 │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 血缘收集层                                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │    Glue     │ │  Redshift   │ │  SageMaker  │           │
│  │   提取器    │ │   提取器    │ │   提取器    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    存储层                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  DynamoDB   │ │     S3      │ │ OpenSearch  │           │
│  │  (上下文)   │ │   (血缘)    │ │   (索引)    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## 安装

### 前置条件

- Python 3.8+
- 已配置适当权限的AWS CLI
- 访问Amazon Bedrock (Claude 3.5 Sonnet)
- AWS Glue、Redshift和/或SageMaker服务

### 设置

1. **克隆仓库**：
   ```bash
   git clone https://github.com/Honeyfish20/e2e-datalineage-with-amazon-strands-agents.git
   cd e2e-datalineage-with-amazon-strands-agents
   ```

2. **运行设置脚本**：
   ```bash
   python scripts/setup_project.py
   ```

3. **配置环境**：
   ```bash
   cp .env.sample .env
   # 编辑.env文件，填入你的AWS配置
   ```

4. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

5. **配置AWS凭证**：
   ```bash
   aws configure
   ```

## 快速开始

### 基础使用

```python
from agents.context_aware_agent import ContextAwareAgent
from utils.config_manager import ConfigManager

# 初始化代理
config = ConfigManager()
agent = ContextAwareAgent(config.get_all_config())

# 识别执行上下文
context = agent.identify_execution_context()
print(f"Context ID: {context.context_id}")
print(f"Environment: {context.environment_type.value}")

# 收集和合并血缘数据
lineage_sources = {
    'glue': glue_lineage_data,
    'redshift': redshift_lineage_data,
    'sagemaker': sagemaker_lineage_data
}

result = agent.merge_lineage_data(lineage_sources, context)
if result['success']:
    print("血缘合并成功！")
    print(f"事件数量: {len(result['merged_lineage']['lineage_events'])}")
    print(f"数据实体: {len(result['merged_lineage']['data_entities'])}")
```

### SageMaker Notebook集成

```python
# 在SageMaker Notebook中
from agents.context_aware_agent import ContextAwareAgent

# 代理自动检测SageMaker环境
agent = ContextAwareAgent()
context = agent.identify_execution_context()

# 上下文将包含SageMaker特定信息
print(f"Notebook实例: {context.notebook_instance}")
print(f"SageMaker角色: {context.sagemaker_role}")

# 为你的数据科学工作流收集血缘
# ... 你的数据处理代码 ...

# 代理将关联你的notebook操作与下游Glue作业
```

## 示例

`examples/`目录包含全面的使用示例：

- `basic_usage.py`：基础血缘收集和合并
- `sagemaker_notebook_example.py`：SageMaker特定工作流

运行示例：
```bash
python examples/basic_usage.py
python examples/sagemaker_notebook_example.py
```

## 配置

系统使用`config/`目录中的YAML配置文件：

```yaml
# config/config.yaml
agent:
  model:
    model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
    max_tokens: 4000
    temperature: 0.1
  
  context:
    timeout_seconds: 30
    cache_ttl_minutes: 60
  
  job_validation:
    time_tolerance_seconds: 300
    min_confidence_threshold: 0.7

aws:
  region: us-east-1
  glue:
    max_concurrent_jobs: 10
  redshift:
    cluster_identifier: data-warehouse-cluster
  sagemaker:
    default_instance_type: ml.t3.medium
```

## 测试

运行测试套件：
```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试类别
python -m pytest tests/test_context_aware_agent.py -v

# 运行覆盖率测试
python -m pytest tests/ --cov=. --cov-report=html
```

## 开发

### 项目结构

```
e2e-datalineage-with-amazon-strands-agents/
├── agents/                 # 代理实现
│   └── context_aware_agent.py
├── models/                 # 数据模型
│   ├── execution_context.py
│   ├── job_mapping.py
│   ├── lineage_data.py
│   └── lineage_validation.py
├── tools/                  # 工具和实用程序
│   ├── lineage_validator.py
│   ├── lineage_merger.py
│   └── context_extractor.py
├── utils/                  # 实用函数
│   ├── config_manager.py
│   └── monitoring.py
├── config/                 # 配置文件
│   └── config.yaml
├── examples/               # 使用示例
│   ├── basic_usage.py
│   └── sagemaker_notebook_example.py
└── tests/                  # 测试文件
    └── test_context_aware_agent.py
```

### 开发脚本

```bash
# 设置开发环境
python scripts/setup_project.py

# 运行测试
python -m pytest tests/ -v
```

## API参考

### Context-Aware Agent

协调所有血缘操作的主要代理类：

```python
class ContextAwareAgent:
    def identify_execution_context(self) -> ExecutionContext
    def validate_job_id_selection(self, job_name: str, job_run_id: str, context: ExecutionContext) -> JobExecutionMapping
    def merge_lineage_data(self, lineage_sources: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]
    def query_lineage_by_context(self, context_id: str, query_type: str) -> Dict[str, Any]
```

### 数据模型

系统中使用的关键数据模型：

- `ExecutionContext`：表示执行环境和上下文
- `JobExecutionMapping`：将Job Run ID映射到执行上下文
- `LineageValidationResult`：包含血缘验证结果
- `MultiSourceLineageData`：保存多源血缘信息

## 监控和可观测性

系统包含全面的监控：

- **指标**：上下文识别成功率、Job ID验证置信度、血缘合并成功率
- **日志**：可配置级别的结构化日志
- **告警**：关键故障的CloudWatch告警
- **追踪**：AWS X-Ray集成的分布式追踪

## 安全

- **加密**：静态和传输中的数据加密
- **访问控制**：基于IAM的细粒度权限
- **审计日志**：所有操作的完整审计跟踪
- **合规性**：支持GDPR、HIPAA、SOX合规

## 许可证

本项目采用MIT许可证 - 详见LICENSE文件。

## 支持

如有问题、问题或贡献：

- 在GitHub仓库中创建issue
- 查看`docs/`目录中的文档
- 查看`examples/`目录中的示例

## 路线图

### 阶段一（当前）：MVP核心功能
- ✅ 上下文感知执行识别
- ✅ 智能Job ID验证
- ✅ 智能日志流选择
- ✅ 基础多源血缘合并

### 阶段二：多代理架构
- 🔄 专业化代理实现
- 🔄 RESTful API平台
- 🔄 高级查询和可视化

### 阶段三：企业级功能
- ⏳ 安全和合规框架
- ⏳ 高级分析和ML预测
- ⏳ 高可用性和灾难恢复