"""
执行上下文数据模型

定义执行上下文的数据结构，支持多种执行环境的识别和管理。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum
import hashlib
import json


class EnvironmentType(Enum):
    """执行环境类型枚举"""
    STANDALONE_SCRIPT = "standalone_script"
    SAGEMAKER_NOTEBOOK = "sagemaker_notebook"
    JUPYTER_NOTEBOOK = "jupyter_notebook"
    AIRFLOW_TASK = "airflow_task"
    UNKNOWN = "unknown"


@dataclass
class ExecutionContext:
    """执行上下文模型"""
    context_id: str
    environment_type: EnvironmentType
    timestamp: datetime
    process_id: int
    command_line: str
    working_directory: str
    
    # 通用可选字段
    parent_process: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # SageMaker特定字段
    notebook_instance: Optional[str] = None
    sagemaker_role: Optional[str] = None
    kernel_id: Optional[str] = None
    
    # Jupyter特定字段
    jupyter_kernel_id: Optional[str] = None
    
    # Airflow特定字段
    airflow_dag_id: Optional[str] = None
    airflow_task_id: Optional[str] = None
    airflow_run_id: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_unique_identifier(self) -> str:
        """获取唯一标识符"""
        return f"{self.environment_type.value}_{self.process_id}_{self.timestamp.isoformat()}"
    
    def generate_context_hash(self) -> str:
        """生成上下文哈希值，用于快速比较和索引"""
        context_data = {
            'environment_type': self.environment_type.value,
            'process_id': self.process_id,
            'command_line': self.command_line,
            'working_directory': self.working_directory,
            'user_id': self.user_id,
            'parent_process': self.parent_process
        }
        
        # 添加环境特定字段
        if self.environment_type == EnvironmentType.SAGEMAKER_NOTEBOOK:
            context_data.update({
                'notebook_instance': self.notebook_instance,
                'sagemaker_role': self.sagemaker_role,
                'kernel_id': self.kernel_id
            })
        elif self.environment_type == EnvironmentType.AIRFLOW_TASK:
            context_data.update({
                'airflow_dag_id': self.airflow_dag_id,
                'airflow_task_id': self.airflow_task_id,
                'airflow_run_id': self.airflow_run_id
            })
        
        context_json = json.dumps(context_data, sort_keys=True)
        return hashlib.sha256(context_json.encode()).hexdigest()[:16]
    
    def is_sagemaker_environment(self) -> bool:
        """判断是否为SageMaker环境"""
        return self.environment_type == EnvironmentType.SAGEMAKER_NOTEBOOK
    
    def is_airflow_environment(self) -> bool:
        """判断是否为Airflow环境"""
        return self.environment_type == EnvironmentType.AIRFLOW_TASK
    
    def get_environment_specific_info(self) -> Dict[str, Any]:
        """获取环境特定信息"""
        if self.environment_type == EnvironmentType.SAGEMAKER_NOTEBOOK:
            return {
                'notebook_instance': self.notebook_instance,
                'sagemaker_role': self.sagemaker_role,
                'kernel_id': self.kernel_id
            }
        elif self.environment_type == EnvironmentType.AIRFLOW_TASK:
            return {
                'dag_id': self.airflow_dag_id,
                'task_id': self.airflow_task_id,
                'run_id': self.airflow_run_id
            }
        elif self.environment_type == EnvironmentType.JUPYTER_NOTEBOOK:
            return {
                'jupyter_kernel_id': self.jupyter_kernel_id
            }
        else:
            return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于存储和传输"""
        return {
            'context_id': self.context_id,
            'environment_type': self.environment_type.value,
            'timestamp': self.timestamp.isoformat(),
            'process_id': self.process_id,
            'command_line': self.command_line,
            'working_directory': self.working_directory,
            'parent_process': self.parent_process,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'notebook_instance': self.notebook_instance,
            'sagemaker_role': self.sagemaker_role,
            'kernel_id': self.kernel_id,
            'jupyter_kernel_id': self.jupyter_kernel_id,
            'airflow_dag_id': self.airflow_dag_id,
            'airflow_task_id': self.airflow_task_id,
            'airflow_run_id': self.airflow_run_id,
            'metadata': self.metadata,
            'context_hash': self.generate_context_hash()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionContext':
        """从字典创建ExecutionContext实例"""
        return cls(
            context_id=data['context_id'],
            environment_type=EnvironmentType(data['environment_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            process_id=data['process_id'],
            command_line=data['command_line'],
            working_directory=data['working_directory'],
            parent_process=data.get('parent_process'),
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            notebook_instance=data.get('notebook_instance'),
            sagemaker_role=data.get('sagemaker_role'),
            kernel_id=data.get('kernel_id'),
            jupyter_kernel_id=data.get('jupyter_kernel_id'),
            airflow_dag_id=data.get('airflow_dag_id'),
            airflow_task_id=data.get('airflow_task_id'),
            airflow_run_id=data.get('airflow_run_id'),
            metadata=data.get('metadata', {})
        )
    
    def validate(self) -> bool:
        """验证上下文数据的完整性"""
        # 基本字段验证
        if not all([self.context_id, self.environment_type, self.timestamp, 
                   self.process_id, self.command_line, self.working_directory]):
            return False
        
        # 环境特定验证
        if self.environment_type == EnvironmentType.SAGEMAKER_NOTEBOOK:
            if not self.notebook_instance:
                return False
        elif self.environment_type == EnvironmentType.AIRFLOW_TASK:
            if not all([self.airflow_dag_id, self.airflow_task_id]):
                return False
        
        return True