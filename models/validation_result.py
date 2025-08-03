"""
血缘验证结果数据模型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class RecommendationType(Enum):
    """推荐操作类型"""
    PROCEED = "proceed"
    BLOCK = "block"
    WARN = "warn"
    MANUAL_REVIEW = "manual_review"


class ValidationIssueType(Enum):
    """验证问题类型"""
    CONTEXT_MISMATCH = "context_mismatch"
    TIME_INCONSISTENCY = "time_inconsistency"
    PARAMETER_CONFLICT = "parameter_conflict"
    MISSING_CONTEXT = "missing_context"
    DUPLICATE_MAPPING = "duplicate_mapping"


@dataclass
class ValidationIssue:
    """验证问题详情"""
    issue_type: ValidationIssueType
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    affected_components: List[str] = field(default_factory=list)
    suggested_fix: Optional[str] = None


@dataclass
class LineageValidationResult:
    """血缘验证结果模型"""
    
    # 基本信息
    context_id: str
    validation_timestamp: datetime
    is_valid: bool
    confidence_score: float
    
    # 验证对象
    glue_lineage_file: Optional[str] = None
    redshift_lineage_file: Optional[str] = None
    job_run_ids: List[str] = field(default_factory=list)
    
    # 验证结果
    context_match: bool = False
    time_consistency: bool = False
    parameter_consistency: bool = False
    
    # 推荐和问题
    recommendation: RecommendationType = RecommendationType.MANUAL_REVIEW
    warning_message: Optional[str] = None
    issues: List[ValidationIssue] = field(default_factory=list)
    
    # 详细信息
    validation_details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'context_id': self.context_id,
            'validation_timestamp': self.validation_timestamp.isoformat(),
            'is_valid': self.is_valid,
            'confidence_score': self.confidence_score,
            'glue_lineage_file': self.glue_lineage_file,
            'redshift_lineage_file': self.redshift_lineage_file,
            'job_run_ids': self.job_run_ids,
            'context_match': self.context_match,
            'time_consistency': self.time_consistency,
            'parameter_consistency': self.parameter_consistency,
            'recommendation': self.recommendation.value,
            'warning_message': self.warning_message,
            'issues': [
                {
                    'issue_type': issue.issue_type.value,
                    'severity': issue.severity,
                    'description': issue.description,
                    'affected_components': issue.affected_components,
                    'suggested_fix': issue.suggested_fix
                }
                for issue in self.issues
            ],
            'validation_details': self.validation_details,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LineageValidationResult':
        """从字典创建LineageValidationResult实例"""
        issues = []
        for issue_data in data.get('issues', []):
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType(issue_data['issue_type']),
                severity=issue_data['severity'],
                description=issue_data['description'],
                affected_components=issue_data.get('affected_components', []),
                suggested_fix=issue_data.get('suggested_fix')
            ))
        
        return cls(
            context_id=data['context_id'],
            validation_timestamp=datetime.fromisoformat(data['validation_timestamp']),
            is_valid=data['is_valid'],
            confidence_score=data['confidence_score'],
            glue_lineage_file=data.get('glue_lineage_file'),
            redshift_lineage_file=data.get('redshift_lineage_file'),
            job_run_ids=data.get('job_run_ids', []),
            context_match=data.get('context_match', False),
            time_consistency=data.get('time_consistency', False),
            parameter_consistency=data.get('parameter_consistency', False),
            recommendation=RecommendationType(data.get('recommendation', 'manual_review')),
            warning_message=data.get('warning_message'),
            issues=issues,
            validation_details=data.get('validation_details', {}),
            metadata=data.get('metadata', {})
        )
    
    def add_issue(self, issue_type: ValidationIssueType, severity: str, 
                  description: str, affected_components: List[str] = None,
                  suggested_fix: str = None):
        """添加验证问题"""
        issue = ValidationIssue(
            issue_type=issue_type,
            severity=severity,
            description=description,
            affected_components=affected_components or [],
            suggested_fix=suggested_fix
        )
        self.issues.append(issue)
    
    def has_critical_issues(self) -> bool:
        """检查是否有严重问题"""
        return any(issue.severity == 'critical' for issue in self.issues)
    
    def get_issue_summary(self) -> Dict[str, int]:
        """获取问题摘要统计"""
        summary = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        for issue in self.issues:
            summary[issue.severity] += 1
        return summary