"""
上下文感知代理

基于Claude 3.5 Sonnet的智能代理，协调整个血缘管理流程。
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from strands import Agent
from strands.tools.aws import BedrockModel

from ..models.execution_context import ExecutionContext, EnvironmentType
from ..models.job_mapping import JobExecutionMapping, ValidationStatus
from ..models.lineage_validation import LineageValidationResult, RecommendationType
from ..tools.context_extractor import ExecutionContextExtractor
from ..tools.job_validator import JobIDValidator
from ..tools.log_stream_selector import IntelligentLogStreamSelector
from ..utils.config_manager import ConfigManager
from ..utils.monitoring import SimpleMonitoring


class ContextAwareAgent:
    """上下文感知代理 - MVP版本的单一代理实现"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(__name__)
        self.config_manager = ConfigManager(config)
        self.monitoring = SimpleMonitoring()
        
        # 初始化Bedrock模型
        self.model = BedrockModel("anthropic.claude-3-5-sonnet-20241022-v2:0")
        
        # 初始化工具
        self.context_extractor = ExecutionContextExtractor()
        self.job_validator = JobIDValidator()
        self.log_stream_selector = IntelligentLogStreamSelector()
        
        # 系统提示
        self.system_prompt = """
        你是一个端到端数据血缘管理的智能代理。你的核心职责是：
        
        1. **执行上下文管理**：
           - 识别和追踪多种执行上下文（独立脚本、SageMaker Notebook、Airflow等）
           - 确保每个执行上下文都能获取到属于自己的正确数据血缘
           - 防止不同执行上下文的血缘数据交叉污染
        
        2. **智能Job ID验证**：
           - 使用多维度验证替代简单的lastEventTime排序
           - 基于时间匹配、参数匹配、环境匹配等因素进行综合判断
           - 提供置信度评分和验证建议
        
        3. **血缘数据协调**：
           - 收集Glue Job、Redshift和SageMaker Notebook的完整数据血缘
           - 按照真实的上下游关系智能合并多源血缘数据
           - 确保血缘数据的一致性和完整性
        
        4. **冲突检测和解决**：
           - 检测Job ID冲突和上下文混淆
           - 提供智能的冲突解决策略
           - 在必要时建议人工干预
        
        5. **决策制定**：
           - 基于多维度信息做出智能决策
           - 提供清晰的决策理由和建议
           - 确保决策的可解释性和可审计性
        
        **工作原则**：
        - 准确性优先：宁可保守也不要产生错误的血缘关联
        - 上下文隔离：严格确保不同执行上下文的数据不会混淆
        - 智能决策：综合多个维度的信息进行决策
        - 可解释性：提供清晰的决策理由和建议
        - 错误恢复：在出现问题时提供恢复建议
        """
        
        self.logger.info("Context-Aware Agent initialized successfully")
    
    def identify_execution_context(self, trigger_info: Optional[Dict[str, Any]] = None) -> ExecutionContext:
        """
        识别当前执行上下文
        
        Args:
            trigger_info: 可选的触发信息
        
        Returns:
            ExecutionContext: 识别的执行上下文
        """
        try:
            self.logger.info("Starting execution context identification")
            
            # 提取执行上下文
            context = self.context_extractor.extract_execution_context()
            
            # 验证上下文
            is_valid = self.context_extractor.validate_context(context)
            
            # 记录监控指标
            self.monitoring.emit_context_identification_metric(
                success=is_valid,
                environment_type=context.environment_type.value,
                processing_time_ms=0  # 这里可以添加实际的处理时间
            )
            
            if not is_valid:
                self.logger.warning(f"Context validation failed for {context.context_id}")
                context.metadata['validation_warning'] = 'Context validation failed'
            
            self.logger.info(f"Execution context identified: {context.context_id} ({context.environment_type.value})")
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to identify execution context: {e}")
            self.monitoring.emit_context_identification_metric(
                success=False,
                environment_type="unknown",
                processing_time_ms=0
            )
            raise
    
    def validate_job_id_selection(self, job_name: str, selected_job_id: str, 
                                 context: ExecutionContext) -> JobExecutionMapping:
        """
        验证Job ID选择的正确性
        
        Args:
            job_name: Glue作业名称
            selected_job_id: 选择的Job Run ID
            context: 执行上下文
        
        Returns:
            JobExecutionMapping: 验证结果和映射信息
        """
        try:
            self.logger.info(f"Validating Job ID selection: {job_name}/{selected_job_id}")
            
            # 执行多维度验证
            mapping = self.job_validator.validate_job_run_id(job_name, selected_job_id, context)
            
            # 记录监控指标
            self.monitoring.emit_job_id_validation_metric(
                confidence_score=mapping.confidence_score,
                validation_result=mapping.validation_status.value,
                job_name=job_name
            )
            
            # 根据验证结果提供建议
            if mapping.validation_status == ValidationStatus.VALIDATED:
                self.logger.info(f"Job ID validation successful: {selected_job_id} (confidence: {mapping.confidence_score:.3f})")
            elif mapping.validation_status == ValidationStatus.PENDING:
                self.logger.warning(f"Job ID validation pending: {selected_job_id} (confidence: {mapping.confidence_score:.3f})")
            else:
                self.logger.error(f"Job ID validation failed: {selected_job_id} (confidence: {mapping.confidence_score:.3f})")
            
            return mapping
            
        except Exception as e:
            self.logger.error(f"Job ID validation failed: {e}")
            raise
    
    def resolve_job_id_conflict(self, job_name: str, conflicting_jobs: List[str], 
                               context: ExecutionContext) -> Dict[str, Any]:
        """
        解决Job ID冲突
        
        Args:
            job_name: Glue作业名称
            conflicting_jobs: 冲突的Job Run ID列表
            context: 执行上下文
        
        Returns:
            Dict: 冲突解决结果
        """
        try:
            self.logger.info(f"Resolving Job ID conflict for {job_name}: {len(conflicting_jobs)} candidates")
            
            # 为每个候选Job ID进行验证
            validation_results = []
            for job_id in conflicting_jobs:
                mapping = self.validate_job_id_selection(job_name, job_id, context)
                validation_results.append({
                    'job_id': job_id,
                    'mapping': mapping,
                    'confidence': mapping.confidence_score
                })
            
            # 按置信度排序
            validation_results.sort(key=lambda x: x['confidence'], reverse=True)
            
            # 选择最佳候选
            best_candidate = validation_results[0]
            
            # 检查是否有明确的最佳选择
            if len(validation_results) > 1:
                confidence_gap = best_candidate['confidence'] - validation_results[1]['confidence']
                if confidence_gap < 0.2:  # 置信度差距小于0.2
                    # 需要人工干预
                    return {
                        'resolution_status': 'manual_intervention_required',
                        'recommended_job_id': best_candidate['job_id'],
                        'confidence_score': best_candidate['confidence'],
                        'conflict_details': {
                            'candidates': validation_results,
                            'confidence_gap': confidence_gap,
                            'reason': 'Multiple candidates with similar confidence scores'
                        },
                        'suggested_actions': [
                            'Review job execution logs manually',
                            'Check job parameters and timing',
                            'Verify execution environment context'
                        ]
                    }
            
            # 有明确的最佳选择
            return {
                'resolution_status': 'resolved',
                'selected_job_id': best_candidate['job_id'],
                'confidence_score': best_candidate['confidence'],
                'mapping': best_candidate['mapping'],
                'resolution_reason': f'Clear best candidate with confidence {best_candidate["confidence"]:.3f}'
            }
            
        except Exception as e:
            self.logger.error(f"Job ID conflict resolution failed: {e}")
            return {
                'resolution_status': 'error',
                'error_message': str(e),
                'suggested_actions': ['Manual review required', 'Check system logs for details']
            }
    
    def intelligent_log_stream_selection(self, job_name: str, context: ExecutionContext,
                                       log_group_name: str) -> Dict[str, Any]:
        """
        智能选择日志流
        
        Args:
            job_name: Glue作业名称
            context: 执行上下文
            log_group_name: 日志组名称
        
        Returns:
            Dict: 日志流选择结果
        """
        try:
            self.logger.info(f"Performing intelligent log stream selection for {job_name}")
            
            # 获取可用的日志流
            available_streams = self.log_stream_selector.get_log_streams_for_job(log_group_name)
            
            if not available_streams:
                return {
                    'selected_stream': None,
                    'selection_reason': 'No log streams found',
                    'confidence_score': 0.0
                }
            
            # 执行智能选择
            selection_result = self.log_stream_selector.intelligent_log_stream_selection(
                job_name, context, available_streams
            )
            
            # 记录选择结果
            self.logger.info(
                f"Log stream selected: {selection_result.get('selected_stream', {}).get('logStreamName', 'None')} "
                f"(confidence: {selection_result.get('confidence_score', 0):.3f})"
            )
            
            return selection_result
            
        except Exception as e:
            self.logger.error(f"Intelligent log stream selection failed: {e}")
            return {
                'selected_stream': None,
                'selection_reason': f'Selection failed: {str(e)}',
                'confidence_score': 0.0,
                'error': str(e)
            }
    
    def collect_multi_source_lineage(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        收集多源血缘数据
        
        Args:
            context: 执行上下文
        
        Returns:
            Dict: 多源血缘收集结果
        """
        try:
            self.logger.info(f"Starting multi-source lineage collection for context {context.context_id}")
            
            collection_results = {
                'context_id': context.context_id,
                'collection_timestamp': datetime.now().isoformat(),
                'sources_collected': [],
                'lineage_data': {},
                'collection_status': 'in_progress'
            }
            
            # 收集Glue血缘（基础功能）
            try:
                glue_lineage = self._collect_glue_lineage(context)
                if glue_lineage:
                    collection_results['sources_collected'].append('glue')
                    collection_results['lineage_data']['glue'] = glue_lineage
            except Exception as e:
                self.logger.warning(f"Glue lineage collection failed: {e}")
                collection_results['lineage_data']['glue'] = {'error': str(e)}
            
            # 收集Redshift血缘（如果适用）
            if self._should_collect_redshift_lineage(context):
                try:
                    redshift_lineage = self._collect_redshift_lineage(context)
                    if redshift_lineage:
                        collection_results['sources_collected'].append('redshift')
                        collection_results['lineage_data']['redshift'] = redshift_lineage
                except Exception as e:
                    self.logger.warning(f"Redshift lineage collection failed: {e}")
                    collection_results['lineage_data']['redshift'] = {'error': str(e)}
            
            # 收集SageMaker血缘（如果适用）
            if context.environment_type == EnvironmentType.SAGEMAKER_NOTEBOOK:
                try:
                    sagemaker_lineage = self._collect_sagemaker_lineage(context)
                    if sagemaker_lineage:
                        collection_results['sources_collected'].append('sagemaker')
                        collection_results['lineage_data']['sagemaker'] = sagemaker_lineage
                except Exception as e:
                    self.logger.warning(f"SageMaker lineage collection failed: {e}")
                    collection_results['lineage_data']['sagemaker'] = {'error': str(e)}
            
            # 更新收集状态
            if collection_results['sources_collected']:
                collection_results['collection_status'] = 'completed'
            else:
                collection_results['collection_status'] = 'failed'
                collection_results['error'] = 'No lineage data collected from any source'
            
            self.logger.info(
                f"Multi-source lineage collection completed: "
                f"{len(collection_results['sources_collected'])} sources collected"
            )
            
            return collection_results
            
        except Exception as e:
            self.logger.error(f"Multi-source lineage collection failed: {e}")
            return {
                'context_id': context.context_id,
                'collection_status': 'error',
                'error': str(e),
                'collection_timestamp': datetime.now().isoformat()
            }
    
    def _collect_glue_lineage(self, context: ExecutionContext) -> Optional[Dict[str, Any]]:
        """收集Glue血缘数据（占位符实现）"""
        # 这里是MVP版本的简化实现
        # 在完整实现中，这里会调用增强的Glue血缘提取器
        return {
            'source': 'glue',
            'context_id': context.context_id,
            'extraction_timestamp': datetime.now().isoformat(),
            'events': [],  # 实际的血缘事件会在这里
            'metadata': {
                'extractor_version': '1.0.0',
                'extraction_method': 'context_aware'
            }
        }
    
    def _collect_redshift_lineage(self, context: ExecutionContext) -> Optional[Dict[str, Any]]:
        """收集Redshift血缘数据（占位符实现）"""
        return {
            'source': 'redshift',
            'context_id': context.context_id,
            'extraction_timestamp': datetime.now().isoformat(),
            'queries': [],  # 实际的查询血缘会在这里
            'metadata': {
                'extractor_version': '1.0.0',
                'extraction_method': 'context_aware'
            }
        }
    
    def _collect_sagemaker_lineage(self, context: ExecutionContext) -> Optional[Dict[str, Any]]:
        """收集SageMaker血缘数据（占位符实现）"""
        return {
            'source': 'sagemaker',
            'context_id': context.context_id,
            'extraction_timestamp': datetime.now().isoformat(),
            'notebook_instance': context.notebook_instance,
            'operations': [],  # 实际的notebook操作会在这里
            'metadata': {
                'extractor_version': '1.0.0',
                'extraction_method': 'context_aware'
            }
        }
    
    def _should_collect_redshift_lineage(self, context: ExecutionContext) -> bool:
        """判断是否应该收集Redshift血缘"""
        # 简化的判断逻辑，实际实现会更复杂
        return True  # MVP版本默认尝试收集
    
    def get_agent_status(self) -> Dict[str, Any]:
        """获取代理状态信息"""
        return {
            'agent_type': 'ContextAwareAgent',
            'version': '1.0.0',
            'status': 'active',
            'model': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
            'tools_available': [
                'ExecutionContextExtractor',
                'JobIDValidator',
                'IntelligentLogStreamSelector'
            ],
            'capabilities': [
                'execution_context_identification',
                'job_id_validation',
                'intelligent_log_stream_selection',
                'multi_source_lineage_collection',
                'conflict_resolution'
            ]
        }