"""
核心接口定义
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from .models import ExecutionContext, JobExecutionMapping, LineageValidationResult


class IExecutionContextExtractor(ABC):
    """执行上下文提取器接口"""
    
    @abstractmethod
    def extract_context(self) -> ExecutionContext:
        """
        提取当前执行上下文
        
        Returns:
            ExecutionContext: 执行上下文信息
        """
        pass
    
    @abstractmethod
    def identify_environment_type(self) -> str:
        """
        识别执行环境类型
        
        Returns:
            str: 环境类型
        """
        pass


class IJobIDValidator(ABC):
    """Job ID验证器接口"""
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass


class ILineageValidator(ABC):
    """血缘验证器接口"""
    
    @abstractmethod
    def validate_lineage_context_match(
        self,
        context_id: str,
        glue_lineage_file: Optional[str] = None,
        redshift_lineage_file: Optional[str] = None,
        job_run_ids: List[str] = None
    ) -> LineageValidationResult:
        """
        验证血缘数据的上下文匹配性
        
        Args:
            context_id: 上下文ID
            glue_lineage_file: Glue血缘文件路径
            redshift_lineage_file: Redshift血缘文件路径
            job_run_ids: 相关的Job Run ID列表
        
        Returns:
            LineageValidationResult: 验证结果
        """
        pass
    
    @abstractmethod
    def check_merge_compatibility(
        self,
        glue_context_id: str,
        redshift_context_id: str
    ) -> bool:
        """
        检查两个上下文的血缘数据是否可以合并
        
        Args:
            glue_context_id: Glue血缘的上下文ID
            redshift_context_id: Redshift血缘的上下文ID
        
        Returns:
            bool: 是否可以合并
        """
        pass


class ILogStreamSelector(ABC):
    """日志流选择器接口"""
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
            float: 相关性分数
        """
        pass


class IContextAwareAgent(ABC):
    """上下文感知代理接口"""
    
    @abstractmethod
    def identify_execution_context(self, trigger_info: Dict[str, Any]) -> ExecutionContext:
        """
        识别执行上下文
        
        Args:
            trigger_info: 触发信息
        
        Returns:
            ExecutionContext: 执行上下文
        """
        pass
    
    @abstractmethod
    def validate_job_id_selection(
        self,
        job_name: str,
        selected_job_id: str,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        验证Job ID选择的正确性
        
        Args:
            job_name: 作业名称
            selected_job_id: 选择的Job ID
            context: 执行上下文
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        pass
    
    @abstractmethod
    def resolve_job_id_conflict(
        self,
        conflicting_jobs: List[Dict[str, Any]],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        解决Job ID冲突
        
        Args:
            conflicting_jobs: 冲突的作业列表
            context: 执行上下文
        
        Returns:
            Dict[str, Any]: 解决方案
        """
        pass
    
    @abstractmethod
    def track_execution_mapping(
        self,
        context_id: str,
        job_run_id: str
    ) -> bool:
        """
        追踪执行映射关系
        
        Args:
            context_id: 上下文ID
            job_run_id: Job Run ID
        
        Returns:
            bool: 是否成功
        """
        pass


class IErrorRecoveryManager(ABC):
    """错误恢复管理器接口"""
    
    @abstractmethod
    def handle_context_identification_failure(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理上下文识别失败
        
        Args:
            error_info: 错误信息
        
        Returns:
            Dict[str, Any]: 恢复结果
        """
        pass
    
    @abstractmethod
    def handle_job_id_validation_failure(
        self,
        job_name: str,
        candidate_id: str
    ) -> Dict[str, Any]:
        """
        处理Job ID验证失败
        
        Args:
            job_name: 作业名称
            candidate_id: 候选ID
        
        Returns:
            Dict[str, Any]: 恢复结果
        """
        pass
    
    @abstractmethod
    def handle_lineage_merge_conflict(
        self,
        conflict_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理血缘合并冲突
        
        Args:
            conflict_info: 冲突信息
        
        Returns:
            Dict[str, Any]: 处理结果
        """
        pass


class IMonitoring(ABC):
    """监控接口"""
    
    @abstractmethod
    def emit_context_identification_metric(self, success: bool, environment_type: str):
        """
        发送上下文识别指标
        
        Args:
            success: 是否成功
            environment_type: 环境类型
        """
        pass
    
    @abstractmethod
    def emit_job_id_validation_metric(self, confidence_score: float):
        """
        发送Job ID验证指标
        
        Args:
            confidence_score: 置信度分数
        """
        pass
    
    @abstractmethod
    def emit_lineage_validation_metric(self, validation_result: LineageValidationResult):
        """
        发送血缘验证指标
        
        Args:
            validation_result: 验证结果
        """
        pass