"""
智能日志流选择工具

基于执行上下文智能选择正确的日志流，替换简单的lastEventTime排序。
"""

import boto3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import logging
from botocore.exceptions import ClientError

from ..models.execution_context import ExecutionContext, EnvironmentType


class IntelligentLogStreamSelector:
    """智能日志流选择器"""
    
    def __init__(self):
        self.logs_client = boto3.client('logs')
        self.logger = logging.getLogger(__name__)
        
        # 评分权重配置
        self.scoring_weights = {
            'time_match': 0.4,
            'environment_match': 0.25,
            'content_quality': 0.2,
            'size_relevance': 0.15
        }
        
        # 时间容差配置（秒）
        self.time_tolerances = {
            'excellent': 60,    # 1分钟内
            'good': 300,        # 5分钟内
            'acceptable': 900,  # 15分钟内
            'poor': 1800        # 30分钟内
        }
    
    def intelligent_log_stream_selection(self, job_name: str, execution_context: ExecutionContext,
                                       available_streams: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        基于执行上下文智能选择正确的日志流
        
        Args:
            job_name: Glue作业名称
            execution_context: 执行上下文
            available_streams: 可用的日志流列表
        
        Returns:
            Dict: 包含选择结果和详细信息的字典
        """
        if not available_streams:
            return {
                'selected_stream': None,
                'selection_reason': 'No streams available',
                'confidence_score': 0.0,
                'all_scores': []
            }
        
        try:
            # 为每个日志流计算综合匹配分数
            scored_streams = []
            
            for stream in available_streams:
                score_details = self._calculate_stream_score(stream, execution_context)
                
                scored_streams.append({
                    'stream': stream,
                    'total_score': score_details['total_score'],
                    'score_breakdown': score_details['breakdown'],
                    'selection_reasons': score_details['reasons']
                })
            
            # 按分数排序
            scored_streams.sort(key=lambda x: x['total_score'], reverse=True)
            
            # 选择得分最高的日志流
            best_stream_info = scored_streams[0]
            best_stream = best_stream_info['stream']
            
            # 检查是否存在冲突（多个高分流）
            conflict_info = self._detect_selection_conflicts(scored_streams)
            
            # 构建选择结果
            result = {
                'selected_stream': best_stream,
                'confidence_score': best_stream_info['total_score'],
                'selection_reasons': best_stream_info['selection_reasons'],
                'score_breakdown': best_stream_info['score_breakdown'],
                'all_scores': scored_streams,
                'conflict_detected': conflict_info['has_conflict'],
                'conflict_details': conflict_info['details'] if conflict_info['has_conflict'] else None
            }
            
            # 记录选择历史
            self._record_selection_history(job_name, execution_context, result)
            
            self.logger.info(
                f"Selected log stream for job {job_name}: "
                f"{best_stream.get('logStreamName', 'unknown')} "
                f"(score: {best_stream_info['total_score']:.3f})"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Log stream selection failed: {e}")
            return self._create_fallback_selection(available_streams, str(e))
    
    def _calculate_stream_score(self, stream: Dict[str, Any], 
                              execution_context: ExecutionContext) -> Dict[str, Any]:
        """计算单个日志流的综合匹配分数"""
        breakdown = {}
        reasons = []
        
        # 1. 时间匹配评分
        time_score, time_reasons = self._score_time_match(stream, execution_context)
        breakdown['time_match'] = time_score
        reasons.extend(time_reasons)
        
        # 2. 环境匹配评分
        env_score, env_reasons = self._score_environment_match(stream, execution_context)
        breakdown['environment_match'] = env_score
        reasons.extend(env_reasons)
        
        # 3. 内容质量评分
        quality_score, quality_reasons = self._score_content_quality(stream)
        breakdown['content_quality'] = quality_score
        reasons.extend(quality_reasons)
        
        # 4. 大小相关性评分
        size_score, size_reasons = self._score_size_relevance(stream)
        breakdown['size_relevance'] = size_score
        reasons.extend(size_reasons)
        
        # 计算加权总分
        total_score = sum(
            breakdown[key] * self.scoring_weights[key]
            for key in self.scoring_weights.keys()
        )
        
        return {
            'total_score': total_score,
            'breakdown': breakdown,
            'reasons': reasons
        }
    
    def _score_time_match(self, stream: Dict[str, Any], 
                         execution_context: ExecutionContext) -> Tuple[float, List[str]]:
        """评估时间匹配度"""
        last_event_time = stream.get('lastEventTime', 0)
        if last_event_time == 0:
            return 0.0, ['No last event time available']
        
        # 转换时间戳
        stream_time = datetime.fromtimestamp(last_event_time / 1000, tz=timezone.utc)
        context_time = execution_context.timestamp
        if context_time.tzinfo is None:
            context_time = context_time.replace(tzinfo=timezone.utc)
        
        # 计算时间差
        time_diff = abs((stream_time - context_time).total_seconds())
        
        # 评分
        if time_diff <= self.time_tolerances['excellent']:
            score = 1.0
            reason = f"Excellent time match (within {time_diff:.0f}s)"
        elif time_diff <= self.time_tolerances['good']:
            score = 0.8
            reason = f"Good time match (within {time_diff:.0f}s)"
        elif time_diff <= self.time_tolerances['acceptable']:
            score = 0.6
            reason = f"Acceptable time match (within {time_diff:.0f}s)"
        elif time_diff <= self.time_tolerances['poor']:
            score = 0.3
            reason = f"Poor time match ({time_diff:.0f}s difference)"
        else:
            score = 0.1
            reason = f"Very poor time match ({time_diff:.0f}s difference)"
        
        return score, [reason]
    
    def _score_environment_match(self, stream: Dict[str, Any], 
                                execution_context: ExecutionContext) -> Tuple[float, List[str]]:
        """评估环境匹配度"""
        stream_name = stream.get('logStreamName', '').lower()
        reasons = []
        score = 0.0
        
        # SageMaker环境匹配
        if execution_context.environment_type == EnvironmentType.SAGEMAKER_NOTEBOOK:
            sagemaker_indicators = ['sagemaker', 'notebook', 'ml-', 'sm-']
            matches = [indicator for indicator in sagemaker_indicators if indicator in stream_name]
            
            if matches:
                score = 0.9
                reasons.append(f"SageMaker environment match: {', '.join(matches)}")
            else:
                score = 0.2
                reasons.append("No SageMaker indicators in stream name")
        
        # Airflow环境匹配
        elif execution_context.environment_type == EnvironmentType.AIRFLOW_TASK:
            airflow_indicators = ['airflow', 'dag', 'task']
            matches = [indicator for indicator in airflow_indicators if indicator in stream_name]
            
            if matches:
                score = 0.9
                reasons.append(f"Airflow environment match: {', '.join(matches)}")
            
            # 检查DAG ID匹配
            if execution_context.airflow_dag_id and execution_context.airflow_dag_id.lower() in stream_name:
                score = max(score, 0.95)
                reasons.append(f"DAG ID match: {execution_context.airflow_dag_id}")
            
            if not matches and not (execution_context.airflow_dag_id and execution_context.airflow_dag_id.lower() in stream_name):
                score = 0.2
                reasons.append("No Airflow indicators in stream name")
        
        # 独立脚本环境
        elif execution_context.environment_type == EnvironmentType.STANDALONE_SCRIPT:
            script_indicators = ['script', 'standalone', 'manual']
            matches = [indicator for indicator in script_indicators if indicator in stream_name]
            
            if matches:
                score = 0.7
                reasons.append(f"Script environment match: {', '.join(matches)}")
            else:
                # 对于独立脚本，没有特定指标也是正常的
                score = 0.5
                reasons.append("Neutral match for standalone script")
        
        # 未知环境
        else:
            score = 0.5
            reasons.append("Unknown environment type")
        
        return score, reasons
    
    def _score_content_quality(self, stream: Dict[str, Any]) -> Tuple[float, List[str]]:
        """评估内容质量"""
        reasons = []
        
        # 检查是否有存储的字节数
        stored_bytes = stream.get('storedBytes', 0)
        
        if stored_bytes == 0:
            return 0.1, ['No stored content']
        
        # 基于内容大小评分
        if stored_bytes > 10000:  # 10KB以上
            score = 1.0
            reasons.append(f"Substantial content ({stored_bytes:,} bytes)")
        elif stored_bytes > 1000:  # 1KB以上
            score = 0.8
            reasons.append(f"Good content size ({stored_bytes:,} bytes)")
        elif stored_bytes > 100:  # 100B以上
            score = 0.6
            reasons.append(f"Moderate content ({stored_bytes:,} bytes)")
        else:
            score = 0.3
            reasons.append(f"Limited content ({stored_bytes:,} bytes)")
        
        return score, reasons
    
    def _score_size_relevance(self, stream: Dict[str, Any]) -> Tuple[float, List[str]]:
        """评估大小相关性"""
        stored_bytes = stream.get('storedBytes', 0)
        
        # 避免过大或过小的日志流
        if stored_bytes == 0:
            return 0.0, ['Empty log stream']
        elif stored_bytes < 50:  # 太小可能是错误日志
            return 0.2, ['Very small log stream, possibly incomplete']
        elif stored_bytes > 100000000:  # 100MB以上可能有问题
            return 0.3, ['Very large log stream, possibly contains errors']
        else:
            # 理想大小范围
            if 1000 <= stored_bytes <= 10000000:  # 1KB到10MB
                return 1.0, ['Optimal log stream size']
            else:
                return 0.7, ['Acceptable log stream size']
    
    def _detect_selection_conflicts(self, scored_streams: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检测选择冲突"""
        if len(scored_streams) < 2:
            return {'has_conflict': False, 'details': None}
        
        best_score = scored_streams[0]['total_score']
        second_best_score = scored_streams[1]['total_score']
        
        # 如果前两名分数非常接近，认为存在冲突
        score_diff = best_score - second_best_score
        
        if score_diff < 0.1:  # 分数差异小于0.1
            conflict_streams = [
                {
                    'stream_name': stream['stream'].get('logStreamName', 'unknown'),
                    'score': stream['total_score'],
                    'reasons': stream['selection_reasons'][:3]  # 只显示前3个原因
                }
                for stream in scored_streams[:3]  # 显示前3个候选
                if stream['total_score'] >= second_best_score
            ]
            
            return {
                'has_conflict': True,
                'details': {
                    'score_difference': score_diff,
                    'conflicting_streams': conflict_streams,
                    'recommendation': 'Manual review recommended due to close scores'
                }
            }
        
        return {'has_conflict': False, 'details': None}
    
    def _record_selection_history(self, job_name: str, execution_context: ExecutionContext,
                                 selection_result: Dict[str, Any]):
        """记录选择历史（用于审计和优化）"""
        history_record = {
            'timestamp': datetime.now().isoformat(),
            'job_name': job_name,
            'context_id': execution_context.context_id,
            'environment_type': execution_context.environment_type.value,
            'selected_stream': selection_result['selected_stream'].get('logStreamName') if selection_result['selected_stream'] else None,
            'confidence_score': selection_result['confidence_score'],
            'conflict_detected': selection_result['conflict_detected'],
            'total_candidates': len(selection_result['all_scores'])
        }
        
        # 这里可以将历史记录存储到DynamoDB或其他持久化存储
        self.logger.debug(f"Selection history recorded: {history_record}")
    
    def _create_fallback_selection(self, available_streams: List[Dict[str, Any]], 
                                 error_reason: str) -> Dict[str, Any]:
        """创建降级选择结果"""
        if not available_streams:
            return {
                'selected_stream': None,
                'confidence_score': 0.0,
                'selection_reasons': ['No streams available'],
                'fallback_reason': error_reason
            }
        
        # 降级到最简单的lastEventTime选择
        fallback_stream = max(
            available_streams,
            key=lambda x: x.get('lastEventTime', 0)
        )
        
        return {
            'selected_stream': fallback_stream,
            'confidence_score': 0.3,  # 低置信度
            'selection_reasons': [
                'Fallback to lastEventTime selection',
                f'Error in intelligent selection: {error_reason}'
            ],
            'fallback_reason': error_reason,
            'is_fallback': True
        }
    
    def get_log_streams_for_job(self, log_group_name: str, 
                               time_window_hours: int = 2) -> List[Dict[str, Any]]:
        """获取指定时间窗口内的日志流"""
        try:
            # 计算时间窗口
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now().timestamp() - time_window_hours * 3600) * 1000)
            
            response = self.logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=50  # 限制结果数量
            )
            
            # 过滤时间窗口内的日志流
            filtered_streams = []
            for stream in response.get('logStreams', []):
                last_event_time = stream.get('lastEventTime', 0)
                if start_time <= last_event_time <= end_time:
                    filtered_streams.append(stream)
            
            return filtered_streams
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self.logger.warning(f"Log group not found: {log_group_name}")
                return []
            else:
                raise e
        except Exception as e:
            self.logger.error(f"Failed to get log streams: {e}")
            return []