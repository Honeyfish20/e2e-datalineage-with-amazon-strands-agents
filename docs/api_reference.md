# API参考文档

## 概述

本文档提供了Enhanced Lineage Agent所有公共API的详细参考，包括核心工具、Strands工具、集成模块和配置接口。

## 核心工具 API

### ExecutionContextExtractor

执行上下文提取器，用于识别和提取当前执行环境的上下文信息。

#### 类定义

```python
class ExecutionContextExtractor(IExecutionContextExtractor):
    """执行上下文提取器实现"""
    
    def __init__(self):
        """初始化提取器"""
        pass
```

#### 方法

##### extract_context()

提取当前执行上下文。

```python
def extract_context(self) -> ExecutionContext:
    """
    提取当前执行上下文
    
    Returns:
        ExecutionContext: 执行上下文信息
        
    Raises:
        Exception: 当上下文提取失败时
    """
```

**返回值**：
- `ExecutionContext`: 包含以下属性的执行上下文对象
  - `context_id`: 唯一上下文标识符
  - `environment_type`: 环境类型（EnvironmentType枚举）
  - `timestamp`: 提取时间戳
  - `process_id`: 进程ID
  - `command_line`: 命令行参数
  - `working_directory`: 工作目录
  - `metadata`: 额外的元数据信息

**示例**：
```python
from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor

extractor = ExecutionContextExtractor()
context = extractor.extract_context()

print(f"Context ID: {context.context_id}")
print(f"Environment: {context.environment_type.value}")
print(f"Process ID: {context.process_id}")
```

##### identify_environment_type()

识别执行环境类型。

```python
def identify_environment_type(self) -> str:
    """
    识别执行环境类型
    
    Returns:
        str: 环境类型字符串
    """
```

**返回值**：
- `str`: 环境类型字符串，可能的值：
  - `"sagemaker_notebook"`: SageMaker Notebook环境
  - `"jupyter_notebook"`: Jupyter Notebook环境
  - `"airflow_task"`: Airflow任务环境
  - `"standalone_script"`: 独立脚本环境
  - `"unknown"`: 未知环境

### JobIDValidator

Job ID验证器，用于验证Job Run ID与执行上下文的匹配性。

#### 类定义

```python
class JobIDValidator(IJobIDValidator):
    """Job ID验证器实现"""
    
    def __init__(self):
        """初始化验证器"""
        pass
```

#### 方法

##### validate_job_run_id()

验证Job Run ID是否属于当前执行上下文。

```python
def validate_job_run_id(
    self, 
    job_name: str, 
    candidate_job_id: str, 
    execution_context: ExecutionContext
) -> Dict[str, Any]:
    """
    验证Job Run ID是否属于当前执行上下文
    
    Args:
        job_name: Glue作业名称
        candidate_job_id: 候选的Job Run ID
        execution_context: 执行上下文
    
    Returns:
        Dict[str, Any]: 验证结果
    """
```

**参数**：
- `job_name` (str): AWS Glue作业名称
- `candidate_job_id` (str): 要验证的Job Run ID
- `execution_context` (ExecutionContext): 执行上下文对象

**返回值**：
- `Dict[str, Any]`: 验证结果字典，包含：
  - `is_valid` (bool): 验证是否通过
  - `confidence_score` (float): 置信度分数 (0.0-1.0)
  - `recommendation` (str): 推荐操作 ("accept", "reject", "manual_review")
  - `job_start_time` (str): 作业开始时间 (ISO格式)
  - `context_time` (str): 上下文时间 (ISO格式)
  - `time_validation` (dict): 时间验证详情
  - `parameter_validation` (dict): 参数验证详情
  - `environment_validation` (dict): 环境验证详情

**示例**：
```python
from enhanced_lineage_agent.tools.job_validator import JobIDValidator
from enhanced_lineage_agent.models.execution_context import ExecutionContext

validator = JobIDValidator()
result = validator.validate_job_run_id(
    job_name="my-glue-job",
    candidate_job_id="jr_abc123",
    execution_context=context
)

if result['is_valid']:
    print(f"Job ID validated with confidence: {result['confidence_score']:.2f}")
else:
    print(f"Job ID validation failed: {result.get('reason', 'Unknown')}")
```

##### create_job_mapping()

创建Job执行映射。

```python
def create_job_mapping(
    self,
    context: ExecutionContext,
    job_name: str,
    job_run_id: str,
    validation_result: Dict[str, Any]
) -> JobExecutionMapping:
    """
    创建Job执行映射
    
    Args:
        context: 执行上下文
        job_name: 作业名称
        job_run_id: 作业运行ID
        validation_result: 验证结果
    
    Returns:
        JobExecutionMapping: Job执行映射
    """
```

### IntelligentLogStreamSelector

智能日志流选择器，用于基于执行上下文智能选择正确的日志流。

#### 类定义

```python
class IntelligentLogStreamSelector(ILogStreamSelector):
    """智能日志流选择器实现"""
    
    def __init__(self):
        """初始化选择器"""
        pass
```

#### 方法

##### select_log_stream()

基于执行上下文智能选择日志流。

```python
def select_log_stream(
    self,
    job_name: str,
    execution_context: ExecutionContext,
    available_streams: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    基于执行上下文智能选择日志流
    
    Args:
        job_name: 作业名称
        execution_context: 执行上下文
        available_streams: 可用的日志流列表
    
    Returns:
        Dict[str, Any]: 选择结果
    """
```

**参数**：
- `job_name` (str): 作业名称
- `execution_context` (ExecutionContext): 执行上下文
- `available_streams` (List[Dict[str, Any]]): 可用日志流列表，每个元素包含：
  - `logGroup` (str): 日志组名称
  - `logStreamName` (str): 日志流名称
  - `lastEventTime` (int): 最后事件时间戳
  - `storedBytes` (int): 存储字节数

**返回值**：
- `Dict[str, Any]`: 选择结果，包含：
  - `selected_stream` (dict): 选中的日志流
  - `score` (float): 相关性分数
  - `confidence` (float): 选择置信度
  - `reasons` (List[str]): 选择原因列表
  - `selection_method` (str): 选择方法

##### score_stream_relevance()

为日志流计算相关性分数。

```python
def score_stream_relevance(
    self,
    stream: Dict[str, Any],
    execution_context: ExecutionContext
) -> float:
    """
    为日志流计算相关性分数
    
    Args:
        stream: 日志流信息
        execution_context: 执行上下文
    
    Returns:
        float: 相关性分数 (0.0 - 1.0)
    """
```

## Strands工具 API

### extract_execution_context

Strands工具：提取当前执行上下文信息。

```python
@tool
def extract_execution_context() -> Dict[str, Any]:
    """
    Strands工具：提取当前执行上下文信息
    
    Returns:
        包含执行上下文信息的字典
    """
```

**返回值**：
- `Dict[str, Any]`: 执行上下文字典，包含所有ExecutionContext属性

**示例**：
```python
from enhanced_lineage_agent.tools.context_extractor import extract_execution_context

context_dict = extract_execution_context()
print(f"Context ID: {context_dict['context_id']}")
print(f"Environment: {context_dict['environment_type']}")
```

### validate_job_run_id

Strands工具：验证候选Job Run ID是否属于当前执行上下文。

```python
@tool
def validate_job_run_id(
    job_name: str, 
    candidate_job_id: str, 
    execution_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Strands工具：验证候选Job Run ID是否属于当前执行上下文
    
    Args:
        job_name: Glue作业名称
        candidate_job_id: 候选的Job Run ID
        execution_context: 执行上下文字典
    
    Returns:
        验证结果字典
    """
```

### intelligent_log_stream_selection

Strands工具：基于执行上下文智能选择正确的日志流。

```python
@tool
def intelligent_log_stream_selection(
    job_name: str, 
    execution_context: Dict[str, Any],
    available_streams: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Strands工具：基于执行上下文智能选择正确的日志流
    
    Args:
        job_name: Glue作业名称
        execution_context: 执行上下文字典
        available_streams: 可用的日志流列表
    
    Returns:
        推荐的日志流和选择理由
    """
```

## 数据模型 API

### ExecutionContext

执行上下文数据模型。

```python
@dataclass
class ExecutionContext:
    """执行上下文数据模型"""
    
    context_id: str
    environment_type: EnvironmentType
    timestamp: datetime
    process_id: int
    command_line: str = ""
    working_directory: str = ""
    parent_process: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    sagemaker_instance_type: Optional[str] = None
    notebook_instance: Optional[str] = None
    jupyter_kernel_id: Optional[str] = None
    airflow_dag_id: Optional[str] = None
    airflow_task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

#### 方法

##### to_dict()

将执行上下文转换为字典。

```python
def to_dict(self) -> Dict[str, Any]:
    """
    将执行上下文转换为字典
    
    Returns:
        Dict[str, Any]: 上下文字典
    """
```

##### from_dict()

从字典创建执行上下文。

```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionContext':
    """
    从字典创建执行上下文
    
    Args:
        data: 上下文数据字典
    
    Returns:
        ExecutionContext: 执行上下文对象
    """
```

##### get_unique_identifier()

获取唯一标识符。

```python
def get_unique_identifier(self) -> str:
    """
    获取唯一标识符
    
    Returns:
        str: 基于多个属性的唯一标识符
    """
```

### EnvironmentType

环境类型枚举。

```python
class EnvironmentType(Enum):
    """环境类型枚举"""
    
    SAGEMAKER_NOTEBOOK = "sagemaker_notebook"
    JUPYTER_NOTEBOOK = "jupyter_notebook"
    AIRFLOW_TASK = "airflow_task"
    STANDALONE_SCRIPT = "standalone_script"
    UNKNOWN = "unknown"
```

### JobExecutionMapping

Job执行映射数据模型。

```python
@dataclass
class JobExecutionMapping:
    """Job执行映射数据模型"""
    
    context_id: str
    job_name: str
    job_run_id: str
    mapping_timestamp: datetime
    job_start_time: Optional[datetime] = None
    confidence_score: float = 0.0
    validation_status: ValidationStatus = ValidationStatus.PENDING
    time_diff_seconds: Optional[float] = None
    parameter_match: Optional[bool] = None
    environment_match: Optional[bool] = None
    validation_method: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## 集成模块 API

### EnhancedGlueLineageExtractor

增强的Glue血缘提取器。

```python
class EnhancedGlueLineageExtractor:
    """增强的Glue血缘提取器，集成上下文感知功能"""
    
    def __init__(self, session, lineage_output_path, enable_context_awareness=True):
        """
        初始化增强提取器
        
        Args:
            session: boto3会话
            lineage_output_path: 血缘输出路径
            enable_context_awareness: 是否启用上下文感知
        """
```

#### 方法

##### extract_and_save_lineage()

提取并保存血缘信息。

```python
def extract_and_save_lineage(
    self, 
    job_name, 
    job_run_id=None, 
    start_time=None, 
    continuous=False
):
    """
    提取并保存血缘信息（增强版本）
    
    Args:
        job_name: 作业名称
        job_run_id: 作业运行ID（可选）
        start_time: 开始时间（可选）
        continuous: 是否持续监控
    """
```

### EnhancedTableLineageMerger

增强的表血缘合并器。

```python
class EnhancedTableLineageMerger:
    """增强的表血缘合并器，集成血缘验证功能"""
    
    def __init__(self, output_dir=None, enable_validation=True):
        """
        初始化增强合并器
        
        Args:
            output_dir: 输出目录
            enable_validation: 是否启用验证
        """
```

#### 方法

##### process_lineage()

处理血缘合并。

```python
def process_lineage(self):
    """
    主处理函数 - 保持向后兼容性
    
    Returns:
        str: 输出文件路径
    """
```

##### validate_lineage_compatibility()

验证Glue和Redshift血缘数据的兼容性。

```python
def validate_lineage_compatibility(
    self, 
    glue_data: Dict[str, Any], 
    redshift_data: Dict[str, Any]
) -> LineageValidationResult:
    """
    验证Glue和Redshift血缘数据的兼容性
    
    Args:
        glue_data: Glue血缘数据
        redshift_data: Redshift血缘数据
    
    Returns:
        LineageValidationResult: 验证结果
    """
```

## 监控 API

### SimpleMonitoring

简单监控类。

```python
class SimpleMonitoring:
    """简单监控类"""
    
    def __init__(self):
        """初始化监控"""
        pass
```

#### 方法

##### record_metric()

记录指标。

```python
def record_metric(
    self,
    metric_name: str,
    value: float,
    metric_type: MetricType = MetricType.GAUGE,
    dimensions: Optional[Dict[str, str]] = None,
    timestamp: Optional[datetime] = None
):
    """
    记录指标
    
    Args:
        metric_name: 指标名称
        value: 指标值
        metric_type: 指标类型
        dimensions: 维度信息
        timestamp: 时间戳
    """
```

##### send_alert()

发送告警。

```python
def send_alert(
    self,
    message: str,
    level: AlertLevel = AlertLevel.WARNING,
    details: Optional[Dict[str, Any]] = None
):
    """
    发送告警
    
    Args:
        message: 告警消息
        level: 告警级别
        details: 详细信息
    """
```

##### create_dashboard()

创建CloudWatch仪表板。

```python
def create_dashboard(self) -> str:
    """
    创建CloudWatch仪表板
    
    Returns:
        str: 仪表板URL
    """
```

## 错误处理 API

### ErrorRecoveryManager

错误恢复管理器。

```python
class ErrorRecoveryManager:
    """错误恢复管理器"""
    
    def __init__(self):
        """初始化错误恢复管理器"""
        pass
```

#### 方法

##### handle_error()

处理错误并执行恢复策略。

```python
def handle_error(
    self,
    error: Exception,
    error_type: ErrorType,
    context: Optional[Dict[str, Any]] = None,
    retry_count: int = 0
) -> Dict[str, Any]:
    """
    处理错误并执行恢复策略
    
    Args:
        error: 异常对象
        error_type: 错误类型
        context: 错误上下文信息
        retry_count: 重试次数
    
    Returns:
        Dict[str, Any]: 恢复结果
    """
```

### with_error_recovery

错误恢复装饰器。

```python
def with_error_recovery(error_type: ErrorType, context_extractor: Optional[Callable] = None):
    """
    错误恢复装饰器
    
    Args:
        error_type: 错误类型
        context_extractor: 上下文提取函数
    """
```

**示例**：
```python
from enhanced_lineage_agent.utils.error_recovery import with_error_recovery, ErrorType

@with_error_recovery(ErrorType.CONTEXT_EXTRACTION_FAILED)
def my_function():
    # 可能失败的代码
    pass
```

## 配置 API

### get_config()

获取配置对象。

```python
def get_config() -> Config:
    """
    获取配置对象
    
    Returns:
        Config: 配置对象
    """
```

### ConfigManager

配置管理器。

```python
class ConfigManager:
    """配置管理器"""
    
    def __init__(self, environment: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            environment: 环境名称
        """
```

#### 方法

##### load_config()

加载配置。

```python
def load_config(self) -> EnhancedLineageConfig:
    """
    加载配置
    
    Returns:
        EnhancedLineageConfig: 增强血缘配置
    """
```

##### save_config()

保存配置到文件。

```python
def save_config(self, config: EnhancedLineageConfig, file_path: Optional[str] = None):
    """
    保存配置到文件
    
    Args:
        config: 配置对象
        file_path: 文件路径
    """
```

## 异常类型

### 自定义异常

```python
class LineageAgentError(Exception):
    """血缘代理基础异常"""
    pass

class ContextExtractionError(LineageAgentError):
    """上下文提取异常"""
    pass

class JobValidationError(LineageAgentError):
    """Job验证异常"""
    pass

class LineageValidationError(LineageAgentError):
    """血缘验证异常"""
    pass

class ConfigurationError(LineageAgentError):
    """配置异常"""
    pass
```

## 使用示例

### 完整的血缘提取流程

```python
from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor
from enhanced_lineage_agent.tools.job_validator import JobIDValidator
from enhanced_lineage_agent.tools.log_stream_selector import IntelligentLogStreamSelector
from enhanced_lineage_agent.integrations.enhanced_glue_extractor import EnhancedGlueLineageExtractor
import boto3

# 1. 提取执行上下文
extractor = ExecutionContextExtractor()
context = extractor.extract_context()
print(f"Execution context: {context.context_id}")

# 2. 验证Job ID
validator = JobIDValidator()
validation_result = validator.validate_job_run_id(
    job_name="my-glue-job",
    candidate_job_id="jr_abc123",
    execution_context=context
)

if validation_result['is_valid']:
    print(f"Job ID validated with confidence: {validation_result['confidence_score']:.2f}")
    
    # 3. 使用增强的血缘提取器
    session = boto3.Session()
    lineage_extractor = EnhancedGlueLineageExtractor(
        session=session,
        lineage_output_path="s3://my-bucket/lineage/",
        enable_context_awareness=True
    )
    
    # 4. 提取血缘数据
    lineage_extractor.extract_and_save_lineage(
        job_name="my-glue-job",
        job_run_id="jr_abc123"
    )
else:
    print(f"Job ID validation failed: {validation_result.get('reason', 'Unknown')}")
```

### 血缘合并流程

```python
from enhanced_lineage_agent.integrations.enhanced_table_merger import EnhancedTableLineageMerger

# 创建增强的表血缘合并器
merger = EnhancedTableLineageMerger(
    output_dir="/path/to/output",
    enable_validation=True
)

# 处理血缘合并
try:
    result_path = merger.process_lineage()
    print(f"Lineage merged successfully: {result_path}")
except Exception as e:
    print(f"Lineage merge failed: {e}")
```

### 监控和告警

```python
from enhanced_lineage_agent.monitoring.simple_monitoring import SimpleMonitoring, AlertLevel

# 创建监控实例
monitoring = SimpleMonitoring()

# 记录指标
monitoring.record_context_identification_success('sagemaker_notebook', True)
monitoring.record_job_id_validation_confidence(0.85, 'my-job')

# 发送告警
monitoring.send_alert(
    message="High error rate detected",
    level=AlertLevel.WARNING,
    details={'error_count': 10, 'time_window': '5min'}
)

# 创建仪表板
dashboard_url = monitoring.create_dashboard()
print(f"Dashboard created: {dashboard_url}")
```

---

本API参考文档涵盖了Enhanced Lineage Agent的所有主要接口。如需更多详细信息或示例，请参考相应的模块文档或联系开发团队。