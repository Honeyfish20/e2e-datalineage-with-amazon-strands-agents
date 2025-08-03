"""
Job执行映射数据模型

定义执行上下文与Job Run ID之间的映射关系。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from datetime import datetime
from enum import Enum


class ValidationStatus(Enum):
    """验证状态枚举"""
    VALIDATED = "validated"
    PENDING = "pending"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ValidationMethod(Enum):
    """验证方法枚举"""
    TIME_MATCH = "time_match"
    PARAMETER_MATCH = "parameter_match"
    ENVIRONMENT_MATCH = "environment_match"
    MULTI_DIMENSIONAL = "multi_dimensional"
    MANUAL_OVERRIDE = "manual_override"


@dataclass
class JobExecutionMapping:
    """Job执行映射模型"""
    context_id: str
    job_name: str
    job_run_id: str
    mapping_timestamp: datetime
    confidence_score: float
    validation_status: ValidationStatus
    
    # 验证信息
    time_diff_seconds: Optional[float] = None
    parameter_match: Optional[bool] = None
    environment_match: Optional[bool] = None
    validation_method: ValidationMethod = ValidationMethod.MULTI_DIMENSIONAL
    
    # Job详细信息
    job_start_time: Optional[datetime] = None
    job_end_time: Optional[datetime] = None
    job_status: Optional[str] = None
    job_arguments: Dict[str, Any] = field(default_factory=dict)
    
    # 关联信息
    related_jobs: List[str] = field(default_factory=list)
    upstream_contexts: List[str] = field(default_factory=list)
    downstream_contexts: List[str] = field(default_factory=list)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """检查映射是否有效"""
        return (
            self.validation_status == ValidationStatus.VALIDATED and
            self.confidence_score >= 0.7 and
            self._is_not_expired()
        )
    
    def _is_not_expired(self) -> bool:
        """检查映射是否过期（24小时）"""
        if self.validation_status == ValidationStatus.EXPIRED:
            return False
        
        time_diff = datetime.now() - self.mapping_timestamp
        return time_diff.total_seconds() < 86400  # 24小时
    
    def get_validation_details(self) -> Dict[str, Any]:
        """获取验证详情"""
        return {
            'confidence_score': self.confidence_score,
            'validation_status': self.validation_status.value,
            'validation_method': self.validation_method.value,
            'time_diff_seconds': self.time_diff_seconds,
            'parameter_match': self.parameter_match,
            'environment_match': self.environment_match,
            'is_valid': self.is_valid(),
            'is_expired': not self._is_not_expired()
        }
    
    def update_confidence_score(self, new_score: float, reason: str = None):
        """更新置信度分数"""
        old_score = self.confidence_score
        self.confidence_score = max(0.0, min(1.0, new_score))  # 确保在0-1范围内
        
        # 记录变更
        if 'score_history' not in self.metadata:
            self.metadata['score_history'] = []
        
        self.metadata['score_history'].append({
            'timestamp': datetime.now().isoformat(),
            'old_score': old_score,
            'new_score': self.confidence_score,
            'reason': reason
        })
        
        # 根据新分数更新验证状态
        if self.confidence_score >= 0.8:
            self.validation_status = ValidationStatus.VALIDATED
        elif self.confidence_score >= 0.5:
            self.validation_status = ValidationStatus.PENDING
        else:
            self.validation_status = ValidationStatus.REJECTED
    
    def add_related_job(self, job_run_id: str, relationship_type: str = "related"):
        """添加关联Job"""
        if job_run_id not in self.related_jobs:
            self.related_jobs.append(job_run_id)
            
            # 记录关联关系
            if 'relationships' not in self.metadata:
                self.metadata['relationships'] = []
            
            self.metadata['relationships'].append({
                'job_run_id': job_run_id,
                'relationship_type': relationship_type,
                'added_timestamp': datetime.now().isoformat()
            })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'context_id': self.context_id,
            'job_name': self.job_name,
            'job_run_id': self.job_run_id,
            'mapping_timestamp': self.mapping_timestamp.isoformat(),
            'confidence_score': self.confidence_score,
            'validation_status': self.validation_status.value,
            'time_diff_seconds': self.time_diff_seconds,
            'parameter_match': self.parameter_match,
            'environment_match': self.environment_match,
            'validation_method': self.validation_method.value,
            'job_start_time': self.job_start_time.isoformat() if self.job_start_time else None,
            'job_end_time': self.job_end_time.isoformat() if self.job_end_time else None,
            'job_status': self.job_status,
            'job_arguments': self.job_arguments,
            'related_jobs': self.related_jobs,
            'upstream_contexts': self.upstream_contexts,
            'downstream_contexts': self.downstream_contexts,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobExecutionMapping':
        """从字典创建JobExecutionMapping实例"""
        return cls(
            context_id=data['context_id'],
            job_name=data['job_name'],
            job_run_id=data['job_run_id'],
            mapping_timestamp=datetime.fromisoformat(data['mapping_timestamp']),
            confidence_score=data['confidence_score'],
            validation_status=ValidationStatus(data['validation_status']),
            time_diff_seconds=data.get('time_diff_seconds'),
            parameter_match=data.get('parameter_match'),
            environment_match=data.get('environment_match'),
            validation_method=ValidationMethod(data.get('validation_method', 'multi_dimensional')),
            job_start_time=datetime.fromisoformat(data['job_start_time']) if data.get('job_start_time') else None,
            job_end_time=datetime.fromisoformat(data['job_end_time']) if data.get('job_end_time') else None,
            job_status=data.get('job_status'),
            job_arguments=data.get('job_arguments', {}),
            related_jobs=data.get('related_jobs', []),
            upstream_contexts=data.get('upstream_contexts', []),
            downstream_contexts=data.get('downstream_contexts', []),
            metadata=data.get('metadata', {})
        )