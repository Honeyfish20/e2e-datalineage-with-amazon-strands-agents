"""
错误处理和恢复机制
"""

import traceback
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from datetime import datetime
import time

from ..models.execution_context import ExecutionContext, EnvironmentType
from ..config import get_config
from ..utils.logging_config import get_contextual_logger


class ErrorType(Enum):
    """错误类型枚举"""
    CONTEXT_EXTRACTION_FAILED = "context_extraction_failed"
    JOB_ID_VALIDATION_FAILED = "job_id_validation_failed"
    LOG_STREAM_SELECTION_FAILED = "log_stream_selection_failed"
    LINEAGE_MERGE_CONFLICT = "lineage_merge_conflict"
    AWS_SERVICE_ERROR = "aws_service_error"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(Enum):
    """恢复策略枚举"""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    MANUAL_INTERVENTION = "manual_intervention"


class ErrorRecoveryManager:
    """错误恢复管理器"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_contextual_logger('error_recovery')
        self.error_history: List[Dict[str, Any]] = []
        self.recovery_strategies = self._initialize_recovery_strategies()
    
    def _initialize_recovery_strategies(self) -> Dict[ErrorType, RecoveryStrategy]:
        """初始化错误恢复策略映射"""
        return {
            ErrorType.CONTEXT_EXTRACTION_FAILED: RecoveryStrategy.FALLBACK,
            ErrorType.JOB_ID_VALIDATION_FAILED: RecoveryStrategy.RETRY,
            ErrorType.LOG_STREAM_SELECTION_FAILED: RecoveryStrategy.FALLBACK,
            ErrorType.LINEAGE_MERGE_CONFLICT: RecoveryStrategy.MANUAL_INTERVENTION,
            ErrorType.AWS_SERVICE_ERROR: RecoveryStrategy.RETRY,
            ErrorType.CONFIGURATION_ERROR: RecoveryStrategy.ABORT,
            ErrorType.NETWORK_ERROR: RecoveryStrategy.RETRY,
            ErrorType.UNKNOWN_ERROR: RecoveryStrategy.FALLBACK
        }
    
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
        try:
            self.logger.error(f"Handling error: {error_type.value} - {str(error)}")
            
            # 记录错误
            error_record = self._create_error_record(error, error_type, context, retry_count)
            self.error_history.append(error_record)
            
            # 获取恢复策略
            strategy = self.recovery_strategies.get(error_type, RecoveryStrategy.FALLBACK)
            
            # 执行恢复策略
            recovery_result = self._execute_recovery_strategy(
                strategy, error, error_type, context, retry_count
            )
            
            # 记录恢复结果
            self.logger.info(f"Recovery strategy {strategy.value} executed: {recovery_result['success']}")
            
            return recovery_result
            
        except Exception as recovery_error:
            self.logger.error(f"Error recovery failed: {str(recovery_error)}")
            return {
                'success': False,
                'strategy': 'abort',
                'error': str(recovery_error),
                'recommendation': 'Manual intervention required'
            }
    
    def _create_error_record(
        self,
        error: Exception,
        error_type: ErrorType,
        context: Optional[Dict[str, Any]],
        retry_count: int
    ) -> Dict[str, Any]:
        """创建错误记录"""
        return {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type.value,
            'error_message': str(error),
            'error_traceback': traceback.format_exc(),
            'context': context or {},
            'retry_count': retry_count
        }
    
    def _execute_recovery_strategy(
        self,
        strategy: RecoveryStrategy,
        error: Exception,
        error_type: ErrorType,
        context: Optional[Dict[str, Any]],
        retry_count: int
    ) -> Dict[str, Any]:
        """执行恢复策略"""
        if strategy == RecoveryStrategy.RETRY:
            return self._handle_retry_strategy(error, error_type, context, retry_count)
        elif strategy == RecoveryStrategy.FALLBACK:
            return self._handle_fallback_strategy(error, error_type, context)
        elif strategy == RecoveryStrategy.SKIP:
            return self._handle_skip_strategy(error, error_type, context)
        elif strategy == RecoveryStrategy.ABORT:
            return self._handle_abort_strategy(error, error_type, context)
        elif strategy == RecoveryStrategy.MANUAL_INTERVENTION:
            return self._handle_manual_intervention_strategy(error, error_type, context)
        else:
            return self._handle_fallback_strategy(error, error_type, context)
    
    def _handle_retry_strategy(
        self,
        error: Exception,
        error_type: ErrorType,
        context: Optional[Dict[str, Any]],
        retry_count: int
    ) -> Dict[str, Any]:
        """处理重试策略"""
        max_retries = self.config.error_recovery.get('max_retries', 3)
        retry_delay = self.config.error_recovery.get('retry_delay_seconds', 5)
        
        if retry_count >= max_retries:
            self.logger.warning(f"Max retries ({max_retries}) exceeded for {error_type.value}")
            return {
                'success': False,
                'strategy': 'retry_exhausted',
                'retry_count': retry_count,
                'recommendation': 'Consider fallback strategy or manual intervention'
            }
        
        # 计算退避延迟
        delay = retry_delay * (2 ** retry_count)  # 指数退避
        self.logger.info(f"Retrying in {delay} seconds (attempt {retry_count + 1}/{max_retries})")
        
        time.sleep(delay)
        
        return {
            'success': True,
            'strategy': 'retry',
            'retry_count': retry_count + 1,
            'delay': delay,
            'recommendation': 'Retry the operation'
        }
    
    def _handle_fallback_strategy(
        self,
        error: Exception,
        error_type: ErrorType,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """处理降级策略"""
        fallback_actions = {
            ErrorType.CONTEXT_EXTRACTION_FAILED: self._fallback_context_extraction,
            ErrorType.LOG_STREAM_SELECTION_FAILED: self._fallback_log_stream_selection,
            ErrorType.JOB_ID_VALIDATION_FAILED: self._fallback_job_id_validation
        }
        
        fallback_action = fallback_actions.get(error_type)
        if fallback_action:
            try:
                fallback_result = fallback_action(context)
                return {
                    'success': True,
                    'strategy': 'fallback',
                    'fallback_result': fallback_result,
                    'recommendation': 'Using fallback mechanism'
                }
            except Exception as fallback_error:
                self.logger.error(f"Fallback strategy failed: {str(fallback_error)}")
                return {
                    'success': False,
                    'strategy': 'fallback_failed',
                    'error': str(fallback_error),
                    'recommendation': 'Manual intervention required'
                }
        else:
            return {
                'success': False,
                'strategy': 'no_fallback',
                'recommendation': 'No fallback available for this error type'
            }
    
    def _handle_skip_strategy(
        self,
        error: Exception,
        error_type: ErrorType,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """处理跳过策略"""
        self.logger.warning(f"Skipping operation due to {error_type.value}")
        return {
            'success': True,
            'strategy': 'skip',
            'recommendation': 'Operation skipped, continue with next step'
        }
    
    def _handle_abort_strategy(
        self,
        error: Exception,
        error_type: ErrorType,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """处理中止策略"""
        self.logger.error(f"Aborting operation due to {error_type.value}")
        return {
            'success': False,
            'strategy': 'abort',
            'recommendation': 'Operation aborted, fix the issue before retrying'
        }
    
    def _handle_manual_intervention_strategy(
        self,
        error: Exception,
        error_type: ErrorType,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """处理手动干预策略"""
        self.logger.warning(f"Manual intervention required for {error_type.value}")
        
        # 生成详细的干预指南
        intervention_guide = self._generate_intervention_guide(error_type, error, context)
        
        return {
            'success': False,
            'strategy': 'manual_intervention',
            'intervention_guide': intervention_guide,
            'recommendation': 'Manual intervention required, see intervention guide'
        }
    
    def _fallback_context_extraction(self, context: Optional[Dict[str, Any]]) -> ExecutionContext:
        """上下文提取失败的降级处理"""
        self.logger.info("Using fallback context extraction")
        
        # 创建最小化的执行上下文
        fallback_context = ExecutionContext(
            context_id=f"fallback_{int(time.time())}",
            environment_type=EnvironmentType.UNKNOWN,
            timestamp=datetime.now(),
            process_id=0,
            command_line="unknown",
            working_directory="/unknown",
            metadata={'fallback': True, 'reason': 'Context extraction failed'}
        )
        
        return fallback_context
    
    def _fallback_log_stream_selection(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """日志流选择失败的降级处理"""
        self.logger.info("Using fallback log stream selection (time-based)")
        
        return {
            'selection_method': 'time_based_fallback',
            'strategy': 'Use most recent log stream based on lastEventTime',
            'confidence': 0.3
        }
    
    def _fallback_job_id_validation(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Job ID验证失败的降级处理"""
        self.logger.info("Using fallback job ID validation")
        
        return {
            'validation_method': 'basic_fallback',
            'is_valid': True,  # 在降级模式下假设有效
            'confidence_score': 0.5,
            'recommendation': 'proceed_with_caution',
            'fallback_reason': 'Advanced validation failed, using basic validation'
        }
    
    def _generate_intervention_guide(
        self,
        error_type: ErrorType,
        error: Exception,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成手动干预指南"""
        guides = {
            ErrorType.LINEAGE_MERGE_CONFLICT: {
                'title': '血缘合并冲突处理指南',
                'steps': [
                    '1. 检查Glue和Redshift血缘数据的执行上下文',
                    '2. 验证Job Run ID是否正确',
                    '3. 检查时间戳是否在合理范围内',
                    '4. 手动验证数据源的一致性',
                    '5. 如果确认数据正确，可以强制合并'
                ],
                'commands': [
                    'python -m enhanced_lineage_agent.tools.lineage_validator --check-context',
                    'python -m enhanced_lineage_agent.tools.job_validator --validate-job-id'
                ]
            },
            ErrorType.CONFIGURATION_ERROR: {
                'title': '配置错误处理指南',
                'steps': [
                    '1. 检查配置文件是否存在',
                    '2. 验证环境变量设置',
                    '3. 检查AWS凭证配置',
                    '4. 验证DynamoDB表是否存在',
                    '5. 检查IAM权限设置'
                ],
                'commands': [
                    'aws configure list',
                    'aws dynamodb describe-table --table-name job-execution-mappings',
                    'python -m enhanced_lineage_agent.config --validate'
                ]
            }
        }
        
        default_guide = {
            'title': f'{error_type.value}处理指南',
            'steps': [
                '1. 查看详细错误日志',
                '2. 检查系统配置',
                '3. 验证网络连接',
                '4. 联系技术支持'
            ],
            'commands': [
                'tail -f /var/log/lineage_agent.log',
                'python -m enhanced_lineage_agent.utils.diagnostics'
            ]
        }
        
        guide = guides.get(error_type, default_guide)
        guide['error_details'] = {
            'error_message': str(error),
            'error_type': error_type.value,
            'context': context
        }
        
        return guide
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        if not self.error_history:
            return {'total_errors': 0}
        
        error_counts = {}
        recovery_counts = {}
        
        for error_record in self.error_history:
            error_type = error_record['error_type']
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            'total_errors': len(self.error_history),
            'error_counts': error_counts,
            'most_recent_error': self.error_history[-1] if self.error_history else None,
            'error_rate': len(self.error_history) / max(1, time.time() - self._get_start_time())
        }
    
    def _get_start_time(self) -> float:
        """获取开始时间（用于计算错误率）"""
        if self.error_history:
            first_error_time = datetime.fromisoformat(self.error_history[0]['timestamp'])
            return first_error_time.timestamp()
        return time.time()
    
    def clear_error_history(self):
        """清除错误历史"""
        self.error_history.clear()
        self.logger.info("Error history cleared")


# 装饰器：自动错误处理
def with_error_recovery(error_type: ErrorType, context_extractor: Optional[Callable] = None):
    """
    错误恢复装饰器
    
    Args:
        error_type: 错误类型
        context_extractor: 上下文提取函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            recovery_manager = ErrorRecoveryManager()
            retry_count = 0
            max_retries = 3
            
            while retry_count <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    context = {}
                    if context_extractor:
                        try:
                            context = context_extractor(*args, **kwargs)
                        except:
                            pass
                    
                    recovery_result = recovery_manager.handle_error(
                        e, error_type, context, retry_count
                    )
                    
                    if recovery_result['success'] and recovery_result['strategy'] == 'retry':
                        retry_count = recovery_result['retry_count']
                        continue
                    elif recovery_result['success'] and recovery_result['strategy'] == 'fallback':
                        return recovery_result['fallback_result']
                    else:
                        raise e
            
            raise Exception(f"Max retries exceeded for {error_type.value}")
        
        return wrapper
    return decorator


# 使用示例
if __name__ == "__main__":
    # 测试错误恢复管理器
    recovery_manager = ErrorRecoveryManager()
    
    # 模拟上下文提取失败
    try:
        raise Exception("Context extraction failed")
    except Exception as e:
        result = recovery_manager.handle_error(
            e, 
            ErrorType.CONTEXT_EXTRACTION_FAILED,
            {'job_name': 'test-job'}
        )
        print(f"Recovery result: {result}")
    
    # 获取错误统计
    stats = recovery_manager.get_error_statistics()
    print(f"Error statistics: {stats}")