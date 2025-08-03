"""
Enhanced Lineage Agent - 端到端数据血缘管理系统

基于Amazon Strands Agents的智能血缘管理系统，解决Job ID混淆和交叉污染问题，
实现跨服务的端到端血缘收集、验证和智能合并。
"""

__version__ = "1.0.0"
__author__ = "Enhanced Lineage Team"

from .agents.context_aware_agent import ContextAwareAgent
from .models.execution_context import ExecutionContext, EnvironmentType
from .models.job_mapping import JobExecutionMapping
from .models.lineage_validation import LineageValidationResult
from .tools.context_extractor import ExecutionContextExtractor
from .tools.job_validator import JobIDValidator
from .tools.log_stream_selector import IntelligentLogStreamSelector

__all__ = [
    "ContextAwareAgent",
    "ExecutionContext",
    "EnvironmentType", 
    "JobExecutionMapping",
    "LineageValidationResult",
    "ExecutionContextExtractor",
    "JobIDValidator",
    "IntelligentLogStreamSelector"
]