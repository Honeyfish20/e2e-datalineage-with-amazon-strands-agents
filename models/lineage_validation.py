"""
血缘验证结果数据模型

定义血缘数据验证的结果结构。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from datetime import datetime
from enum import Enum


class ValidationResultType(Enum):
    """验证结果类型枚举"""
    SINGLE_SOURCE = "single_source"
    CROSS_SERVICE = "cross_service"
    END_TO_END = "end_to_end"
    CONTEXT_MATCH = "context_match"


class RecommendationType(Enum):
    """建议类型枚举"""
    PROCEED = "proceed"
    BLOCK = "block"
    WARN = "warn"
    MANUAL_REVIEW = "manual_review"
    RETRY = "retry"


@dataclass
class LineageValidationResult:
    """血缘验证结果模型"""
    context_id: str
    validation_timestamp: datetime
    is_valid: bool
    confidence_score: float
    validation_type: ValidationResultType
    
    # 多源血缘验证详情
    glue_lineage_file: Optional[str] = None
    redshift_lineage_file: Optional[str] = None
    sagemaker_lineage_file: Optional[str] = None
    
    # 验证结果详情
    context_match: bool = False
    data_consistency: bool = False
    temporal_alignment: bool = False
    cross_service_consistency: Optional[float] = None
    
    # 数据源验证状态
    sources_validated: List[str] = field(default_factory=list)
    
    # 建议和警告
    recommendation: RecommendationType = RecommendationType.MANUAL_REVIEW
    warning_messages: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    
    # 验证统计
    total_records_validated: int = 0
    failed_validations: int = 0
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_warning(self, message: str, severity: str = "medium"):
        """添加警告消息"""
        self.warning_messages.append(message)
        
        # 记录警告详情
        if 'warnings' not in self.metadata:
            self.metadata['warnings'] = []
        
        self.metadata['warnings'].append({
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        })
    
    def add_suggested_action(self, action: str, priority: str = "medium"):
        """添加建议操作"""
        self.suggested_actions.append(action)
        
        # 记录建议详情
        if 'suggestions' not in self.metadata:
            self.metadata['suggestions'] = []
        
        self.metadata['suggestions'].append({
            'action': action,
            'priority': priority,
            'timestamp': datetime.now().isoformat()
        })
    
    def update_validation_score(self, new_score: float, reason: str = None):
        """更新验证分数"""
        old_score = self.confidence_score
        self.confidence_score = max(0.0, min(1.0, new_score))
        
        # 根据新分数更新验证状态
        self.is_valid = self.confidence_score >= 0.7
        
        # 更新建议
        if self.confidence_score >= 0.9:
            self.recommendation = RecommendationType.PROCEED
        elif self.confidence_score >= 0.7:
            self.recommendation = RecommendationType.WARN
        elif self.confidence_score >= 0.5:
            self.recommendation = RecommendationType.MANUAL_REVIEW
        else:
            self.recommendation = RecommendationType.BLOCK
        
        # 记录分数变更
        if 'score_history' not in self.metadata:
            self.metadata['score_history'] = []
        
        self.metadata['score_history'].append({
            'timestamp': datetime.now().isoformat(),
            'old_score': old_score,
            'new_score': self.confidence_score,
            'reason': reason
        })
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """获取验证摘要"""
        return {
            'is_valid': self.is_valid,
            'confidence_score': self.confidence_score,
            'validation_type': self.validation_type.value,
            'recommendation': self.recommendation.value,
            'sources_count': len(self.sources_validated),
            'warnings_count': len(self.warning_messages),
            'suggestions_count': len(self.suggested_actions),
            'validation_details': {
                'context_match': self.context_match,
                'data_consistency': self.data_consistency,
                'temporal_alignment': self.temporal_alignment,
                'cross_service_consistency': self.cross_service_consistency
            }
        }
    
    def has_critical_issues(self) -> bool:
        """检查是否有关键问题"""
        return (
            not self.is_valid or
            self.confidence_score < 0.5 or
            self.recommendation in [RecommendationType.BLOCK, RecommendationType.MANUAL_REVIEW] or
            any('critical' in warning.lower() for warning in self.warning_messages)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'context_id': self.context_id,
            'validation_timestamp': self.validation_timestamp.isoformat(),
            'is_valid': self.is_valid,
            'confidence_score': self.confidence_score,
            'validation_type': self.validation_type.value,
            'glue_lineage_file': self.glue_lineage_file,
            'redshift_lineage_file': self.redshift_lineage_file,
            'sagemaker_lineage_file': self.sagemaker_lineage_file,
            'context_match': self.context_match,
            'data_consistency': self.data_consistency,
            'temporal_alignment': self.temporal_alignment,
            'cross_service_consistency': self.cross_service_consistency,
            'sources_validated': self.sources_validated,
            'recommendation': self.recommendation.value,
            'warning_messages': self.warning_messages,
            'suggested_actions': self.suggested_actions,
            'total_records_validated': self.total_records_validated,
            'failed_validations': self.failed_validations,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LineageValidationResult':
        """从字典创建LineageValidationResult实例"""
        return cls(
            context_id=data['context_id'],
            validation_timestamp=datetime.fromisoformat(data['validation_timestamp']),
            is_valid=data['is_valid'],
            confidence_score=data['confidence_score'],
            validation_type=ValidationResultType(data['validation_type']),
            glue_lineage_file=data.get('glue_lineage_file'),
            redshift_lineage_file=data.get('redshift_lineage_file'),
            sagemaker_lineage_file=data.get('sagemaker_lineage_file'),
            context_match=data.get('context_match', False),
            data_consistency=data.get('data_consistency', False),
            temporal_alignment=data.get('temporal_alignment', False),
            cross_service_consistency=data.get('cross_service_consistency'),
            sources_validated=data.get('sources_validated', []),
            recommendation=RecommendationType(data.get('recommendation', 'manual_review')),
            warning_messages=data.get('warning_messages', []),
            suggested_actions=data.get('suggested_actions', []),
            total_records_validated=data.get('total_records_validated', 0),
            failed_validations=data.get('failed_validations', 0),
            metadata=data.get('metadata', {})
        )