"""
执行上下文提取工具

自动识别和提取当前执行环境的上下文信息。
"""

import os
import sys
import psutil
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
import logging

from ..models.execution_context import ExecutionContext, EnvironmentType


class ExecutionContextExtractor:
    """执行上下文提取器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_execution_context(self) -> ExecutionContext:
        """
        提取当前执行上下文信息，支持多种执行环境
        
        Returns:
            ExecutionContext: 包含执行上下文信息的对象
        """
        try:
            # 基础信息提取
            timestamp = datetime.now()
            process_id = os.getpid()
            command_line = ' '.join(sys.argv)
            working_directory = os.getcwd()
            user_id = os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))
            
            # 父进程信息
            parent_process = None
            try:
                parent = psutil.Process().parent()
                parent_process = parent.name() if parent else None
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            # 会话信息
            session_id = os.environ.get('SESSION_ID')
            
            # 环境类型检测
            environment_type, env_specific_info = self._detect_environment_type(
                command_line, working_directory, parent_process
            )
            
            # 生成唯一上下文标识
            context_id = self._generate_context_id(environment_type, process_id, timestamp)
            
            # 创建执行上下文对象
            context = ExecutionContext(
                context_id=context_id,
                environment_type=environment_type,
                timestamp=timestamp,
                process_id=process_id,
                command_line=command_line,
                working_directory=working_directory,
                parent_process=parent_process,
                user_id=user_id,
                session_id=session_id,
                **env_specific_info
            )
            
            # 添加额外的元数据
            context.metadata.update({
                'python_version': sys.version,
                'platform': sys.platform,
                'extraction_timestamp': timestamp.isoformat(),
                'extractor_version': '1.0.0'
            })
            
            self.logger.info(f"Successfully extracted execution context: {context_id}")
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to extract execution context: {e}")
            # 返回降级的上下文
            return self._create_fallback_context(e)
    
    def _detect_environment_type(self, command_line: str, working_directory: str, 
                                parent_process: Optional[str]) -> tuple[EnvironmentType, Dict[str, Any]]:
        """
        检测执行环境类型
        
        Returns:
            tuple: (环境类型, 环境特定信息)
        """
        env_specific_info = {}
        
        # SageMaker环境检测
        if self._is_sagemaker_environment(working_directory):
            notebook_instance = os.environ.get('SM_CURRENT_INSTANCE_TYPE', 'unknown')
            sagemaker_role = os.environ.get('SM_CURRENT_INSTANCE_GROUP', 'unknown')
            kernel_id = os.environ.get('KERNEL_ID')
            
            env_specific_info.update({
                'notebook_instance': notebook_instance,
                'sagemaker_role': sagemaker_role,
                'kernel_id': kernel_id
            })
            
            return EnvironmentType.SAGEMAKER_NOTEBOOK, env_specific_info
        
        # Airflow环境检测
        if self._is_airflow_environment():
            airflow_dag_id = os.environ.get('AIRFLOW_CTX_DAG_ID')
            airflow_task_id = os.environ.get('AIRFLOW_CTX_TASK_ID')
            airflow_run_id = os.environ.get('AIRFLOW_CTX_DAG_RUN_ID')
            
            env_specific_info.update({
                'airflow_dag_id': airflow_dag_id,
                'airflow_task_id': airflow_task_id,
                'airflow_run_id': airflow_run_id
            })
            
            return EnvironmentType.AIRFLOW_TASK, env_specific_info
        
        # Jupyter环境检测
        if self._is_jupyter_environment(parent_process):
            jupyter_kernel_id = os.environ.get('JPY_PARENT_PID')
            
            env_specific_info.update({
                'jupyter_kernel_id': jupyter_kernel_id
            })
            
            return EnvironmentType.JUPYTER_NOTEBOOK, env_specific_info
        
        # 独立脚本检测
        if self._is_standalone_script(command_line):
            return EnvironmentType.STANDALONE_SCRIPT, env_specific_info
        
        # 默认为未知环境
        return EnvironmentType.UNKNOWN, env_specific_info
    
    def _is_sagemaker_environment(self, working_directory: str) -> bool:
        """检测是否为SageMaker环境"""
        sagemaker_indicators = [
            'sagemaker' in working_directory.lower(),
            os.environ.get('SM_CURRENT_INSTANCE_TYPE') is not None,
            os.environ.get('SM_CURRENT_INSTANCE_GROUP') is not None,
            os.path.exists('/opt/ml'),  # SageMaker特有路径
            os.environ.get('SAGEMAKER_REGION') is not None
        ]
        
        return any(sagemaker_indicators)
    
    def _is_airflow_environment(self) -> bool:
        """检测是否为Airflow环境"""
        airflow_indicators = [
            os.environ.get('AIRFLOW_CTX_DAG_ID') is not None,
            os.environ.get('AIRFLOW_CTX_TASK_ID') is not None,
            os.environ.get('AIRFLOW_HOME') is not None
        ]
        
        return any(airflow_indicators)
    
    def _is_jupyter_environment(self, parent_process: Optional[str]) -> bool:
        """检测是否为Jupyter环境"""
        if not parent_process:
            return False
        
        jupyter_indicators = [
            'jupyter' in parent_process.lower(),
            os.environ.get('JPY_PARENT_PID') is not None,
            os.environ.get('JUPYTER_RUNTIME_DIR') is not None
        ]
        
        return any(jupyter_indicators)
    
    def _is_standalone_script(self, command_line: str) -> bool:
        """检测是否为独立脚本"""
        script_indicators = [
            'extract-lineage-to-s3.py' in command_line,
            'python' in command_line and '.py' in command_line,
            len(sys.argv) > 1 and sys.argv[0].endswith('.py')
        ]
        
        return any(script_indicators)
    
    def _generate_context_id(self, environment_type: EnvironmentType, 
                           process_id: int, timestamp: datetime) -> str:
        """生成唯一的上下文标识"""
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S_%f')[:-3]  # 毫秒精度
        unique_suffix = str(uuid.uuid4())[:8]
        
        return f"{environment_type.value}_{process_id}_{timestamp_str}_{unique_suffix}"
    
    def _create_fallback_context(self, error: Exception) -> ExecutionContext:
        """创建降级的执行上下文"""
        timestamp = datetime.now()
        context_id = f"fallback_{os.getpid()}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        context = ExecutionContext(
            context_id=context_id,
            environment_type=EnvironmentType.UNKNOWN,
            timestamp=timestamp,
            process_id=os.getpid(),
            command_line=' '.join(sys.argv),
            working_directory=os.getcwd(),
            user_id=os.environ.get('USER', 'unknown')
        )
        
        context.metadata['fallback_reason'] = str(error)
        context.metadata['is_fallback'] = True
        
        return context
    
    def validate_context(self, context: ExecutionContext) -> bool:
        """验证上下文的完整性和有效性"""
        try:
            # 基本验证
            if not context.validate():
                return False
            
            # 环境特定验证
            if context.environment_type == EnvironmentType.SAGEMAKER_NOTEBOOK:
                return self._validate_sagemaker_context(context)
            elif context.environment_type == EnvironmentType.AIRFLOW_TASK:
                return self._validate_airflow_context(context)
            elif context.environment_type == EnvironmentType.JUPYTER_NOTEBOOK:
                return self._validate_jupyter_context(context)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Context validation failed: {e}")
            return False
    
    def _validate_sagemaker_context(self, context: ExecutionContext) -> bool:
        """验证SageMaker上下文"""
        return (
            context.notebook_instance is not None and
            context.sagemaker_role is not None
        )
    
    def _validate_airflow_context(self, context: ExecutionContext) -> bool:
        """验证Airflow上下文"""
        return (
            context.airflow_dag_id is not None and
            context.airflow_task_id is not None
        )
    
    def _validate_jupyter_context(self, context: ExecutionContext) -> bool:
        """验证Jupyter上下文"""
        return context.jupyter_kernel_id is not None