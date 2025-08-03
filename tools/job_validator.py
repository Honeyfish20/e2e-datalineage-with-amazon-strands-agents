"""
Job ID验证工具

多维度验证Job Run ID与执行上下文的匹配性。
"""

import boto3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import logging
from botocore.exceptions import ClientError

from ..models.execution_context import ExecutionContext, EnvironmentType
from ..models.job_mapping import JobExecutionMapping, ValidationStatus, ValidationMethod


class JobIDValidator:
    """Job ID验证器"""
    
    def __init__(self):
        self.glue_client = boto3.client('glue')
        self.logger = logging.getLogger(__name__)
        
        # 验证配置
        self.time_tolerance_seconds = 300  # 5分钟时间容差
        self.confidence_thresholds = {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
    
    def validate_job_run_id(self, job_name: str, candidate_job_id: str, 
                           execution_context: ExecutionContext) -> JobExecutionMapping:
        """
        验证候选Job Run ID是否属于当前执行上下文
        
        Args:
            job_name: Glue作业名称
            candidate_job_id: 候选的Job Run ID
            execution_context: 执行上下文信息
        
        Returns:
            JobExecutionMapping: 验证结果和映射信息
        """
        try:
            # 获取Job Run详细信息
            job_run_info = self._get_job_run_info(job_name, candidate_job_id)
            if not job_run_info:
                return self._create_failed_mapping(
                    execution_context.context_id, job_name, candidate_job_id,
                    "Job run not found"
                )
            
            # 多维度验证
            validation_results = self._perform_multi_dimensional_validation(
                job_run_info, execution_context
            )
            
            # 计算综合置信度分数
            confidence_score = self._calculate_confidence_score(validation_results)
            
            # 确定验证状态
            validation_status = self._determine_validation_status(confidence_score)
            
            # 创建Job执行映射
            mapping = JobExecutionMapping(
                context_id=execution_context.context_id,
                job_name=job_name,
                job_run_id=candidate_job_id,
                mapping_timestamp=datetime.now(),
                confidence_score=confidence_score,
                validation_status=validation_status,
                time_diff_seconds=validation_results.get('time_diff_seconds'),
                parameter_match=validation_results.get('parameter_match'),
                environment_match=validation_results.get('environment_match'),
                validation_method=ValidationMethod.MULTI_DIMENSIONAL,
                job_start_time=job_run_info.get('StartedOn'),
                job_end_time=job_run_info.get('CompletedOn'),
                job_status=job_run_info.get('JobRunState'),
                job_arguments=job_run_info.get('Arguments', {})
            )
            
            # 添加验证详情到元数据
            mapping.metadata.update({
                'validation_details': validation_results,
                'job_run_info': {
                    'job_name': job_run_info.get('JobName'),
                    'glue_version': job_run_info.get('GlueVersion'),
                    'max_capacity': job_run_info.get('MaxCapacity'),
                    'worker_type': job_run_info.get('WorkerType'),
                    'number_of_workers': job_run_info.get('NumberOfWorkers')
                }
            })
            
            self.logger.info(
                f"Job ID validation completed: {candidate_job_id} -> "
                f"confidence: {confidence_score:.3f}, status: {validation_status.value}"
            )
            
            return mapping
            
        except Exception as e:
            self.logger.error(f"Job ID validation failed: {e}")
            return self._create_failed_mapping(
                execution_context.context_id, job_name, candidate_job_id,
                f"Validation error: {str(e)}"
            )
    
    def _get_job_run_info(self, job_name: str, job_run_id: str) -> Optional[Dict[str, Any]]:
        """获取Job Run详细信息"""
        try:
            response = self.glue_client.get_job_run(
                JobName=job_name,
                RunId=job_run_id
            )
            return response.get('JobRun')
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                self.logger.warning(f"Job run not found: {job_name}/{job_run_id}")
                return None
            else:
                raise e
    
    def _perform_multi_dimensional_validation(self, job_run_info: Dict[str, Any], 
                                            execution_context: ExecutionContext) -> Dict[str, Any]:
        """执行多维度验证"""
        results = {}
        
        # 1. 时间匹配验证
        results.update(self._validate_time_match(job_run_info, execution_context))
        
        # 2. 参数匹配验证
        results.update(self._validate_parameter_match(job_run_info, execution_context))
        
        # 3. 环境匹配验证
        results.update(self._validate_environment_match(job_run_info, execution_context))
        
        # 4. 上下文特定验证
        results.update(self._validate_context_specific(job_run_info, execution_context))
        
        return results
    
    def _validate_time_match(self, job_run_info: Dict[str, Any], 
                           execution_context: ExecutionContext) -> Dict[str, Any]:
        """验证时间匹配性"""
        job_start_time = job_run_info.get('StartedOn')
        if not job_start_time:
            return {
                'time_match': False,
                'time_diff_seconds': None,
                'time_match_score': 0.0,
                'time_match_reason': 'Job start time not available'
            }
        
        # 计算时间差
        context_time = execution_context.timestamp
        if context_time.tzinfo is None:
            context_time = context_time.replace(tzinfo=timezone.utc)
        if job_start_time.tzinfo is None:
            job_start_time = job_start_time.replace(tzinfo=timezone.utc)
        
        time_diff = abs((job_start_time - context_time).total_seconds())
        
        # 评估时间匹配
        time_match = time_diff <= self.time_tolerance_seconds
        
        # 计算时间匹配分数（距离越近分数越高）
        if time_diff <= 60:  # 1分钟内
            time_match_score = 1.0
        elif time_diff <= 300:  # 5分钟内
            time_match_score = 0.8
        elif time_diff <= 900:  # 15分钟内
            time_match_score = 0.6
        elif time_diff <= 1800:  # 30分钟内
            time_match_score = 0.4
        else:
            time_match_score = 0.2
        
        return {
            'time_match': time_match,
            'time_diff_seconds': time_diff,
            'time_match_score': time_match_score,
            'time_match_reason': f'Time difference: {time_diff:.1f} seconds'
        }
    
    def _validate_parameter_match(self, job_run_info: Dict[str, Any], 
                                execution_context: ExecutionContext) -> Dict[str, Any]:
        """验证参数匹配性"""
        job_arguments = job_run_info.get('Arguments', {})
        
        # 基础参数匹配检查
        parameter_matches = []
        
        # 检查用户相关参数
        if execution_context.user_id:
            user_indicators = ['user', 'owner', 'creator', 'initiated_by']
            for key, value in job_arguments.items():
                if any(indicator in key.lower() for indicator in user_indicators):
                    if execution_context.user_id.lower() in value.lower():
                        parameter_matches.append(f'User match in {key}')
        
        # 检查环境特定参数
        env_specific_matches = self._check_environment_specific_parameters(
            job_arguments, execution_context
        )
        parameter_matches.extend(env_specific_matches)
        
        # 检查路径相关参数
        if execution_context.working_directory:
            path_indicators = ['path', 'dir', 'location', 'source', 'target']
            for key, value in job_arguments.items():
                if any(indicator in key.lower() for indicator in path_indicators):
                    if execution_context.working_directory in value:
                        parameter_matches.append(f'Path match in {key}')
        
        parameter_match = len(parameter_matches) > 0
        parameter_match_score = min(1.0, len(parameter_matches) * 0.3)
        
        return {
            'parameter_match': parameter_match,
            'parameter_match_score': parameter_match_score,
            'parameter_matches': parameter_matches,
            'parameter_match_reason': f'Found {len(parameter_matches)} parameter matches'
        }
    
    def _validate_environment_match(self, job_run_info: Dict[str, Any], 
                                  execution_context: ExecutionContext) -> Dict[str, Any]:
        """验证执行环境匹配性"""
        environment_matches = []
        
        # 检查SageMaker环境匹配
        if execution_context.environment_type == EnvironmentType.SAGEMAKER_NOTEBOOK:
            sagemaker_indicators = self._check_sagemaker_indicators(
                job_run_info, execution_context
            )
            environment_matches.extend(sagemaker_indicators)
        
        # 检查Airflow环境匹配
        elif execution_context.environment_type == EnvironmentType.AIRFLOW_TASK:
            airflow_indicators = self._check_airflow_indicators(
                job_run_info, execution_context
            )
            environment_matches.extend(airflow_indicators)
        
        environment_match = len(environment_matches) > 0
        environment_match_score = min(1.0, len(environment_matches) * 0.4)
        
        return {
            'environment_match': environment_match,
            'environment_match_score': environment_match_score,
            'environment_matches': environment_matches,
            'environment_match_reason': f'Found {len(environment_matches)} environment matches'
        }
    
    def _validate_context_specific(self, job_run_info: Dict[str, Any], 
                                 execution_context: ExecutionContext) -> Dict[str, Any]:
        """执行上下文特定验证"""
        context_matches = []
        
        # 检查进程ID相关信息（如果在参数中）
        job_arguments = job_run_info.get('Arguments', {})
        for key, value in job_arguments.items():
            if 'process' in key.lower() or 'pid' in key.lower():
                if str(execution_context.process_id) in str(value):
                    context_matches.append(f'Process ID match in {key}')
        
        # 检查会话ID匹配
        if execution_context.session_id:
            for key, value in job_arguments.items():
                if 'session' in key.lower():
                    if execution_context.session_id in str(value):
                        context_matches.append(f'Session ID match in {key}')
        
        context_match_score = min(1.0, len(context_matches) * 0.5)
        
        return {
            'context_specific_score': context_match_score,
            'context_matches': context_matches
        }
    
    def _check_environment_specific_parameters(self, job_arguments: Dict[str, Any], 
                                             execution_context: ExecutionContext) -> List[str]:
        """检查环境特定参数"""
        matches = []
        
        if execution_context.environment_type == EnvironmentType.SAGEMAKER_NOTEBOOK:
            sagemaker_indicators = ['sagemaker', 'notebook', 'ml.', 'sm-']
            for key, value in job_arguments.items():
                if any(indicator in str(value).lower() for indicator in sagemaker_indicators):
                    matches.append(f'SageMaker indicator in {key}')
        
        elif execution_context.environment_type == EnvironmentType.AIRFLOW_TASK:
            if execution_context.airflow_dag_id:
                for key, value in job_arguments.items():
                    if execution_context.airflow_dag_id in str(value):
                        matches.append(f'Airflow DAG ID match in {key}')
        
        return matches
    
    def _check_sagemaker_indicators(self, job_run_info: Dict[str, Any], 
                                  execution_context: ExecutionContext) -> List[str]:
        """检查SageMaker环境指标"""
        indicators = []
        job_arguments = job_run_info.get('Arguments', {})
        
        # 检查notebook实例类型
        if execution_context.notebook_instance:
            for key, value in job_arguments.items():
                if execution_context.notebook_instance in str(value):
                    indicators.append(f'Notebook instance match in {key}')
        
        # 检查SageMaker角色
        if execution_context.sagemaker_role:
            for key, value in job_arguments.items():
                if execution_context.sagemaker_role in str(value):
                    indicators.append(f'SageMaker role match in {key}')
        
        return indicators
    
    def _check_airflow_indicators(self, job_run_info: Dict[str, Any], 
                                execution_context: ExecutionContext) -> List[str]:
        """检查Airflow环境指标"""
        indicators = []
        job_arguments = job_run_info.get('Arguments', {})
        
        # 检查DAG ID
        if execution_context.airflow_dag_id:
            for key, value in job_arguments.items():
                if execution_context.airflow_dag_id in str(value):
                    indicators.append(f'Airflow DAG ID match in {key}')
        
        # 检查Task ID
        if execution_context.airflow_task_id:
            for key, value in job_arguments.items():
                if execution_context.airflow_task_id in str(value):
                    indicators.append(f'Airflow Task ID match in {key}')
        
        return indicators
    
    def _calculate_confidence_score(self, validation_results: Dict[str, Any]) -> float:
        """计算综合置信度分数"""
        # 权重配置
        weights = {
            'time_match_score': 0.4,
            'parameter_match_score': 0.3,
            'environment_match_score': 0.2,
            'context_specific_score': 0.1
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for score_key, weight in weights.items():
            if score_key in validation_results:
                total_score += validation_results[score_key] * weight
                total_weight += weight
        
        # 归一化分数
        if total_weight > 0:
            confidence_score = total_score / total_weight
        else:
            confidence_score = 0.0
        
        return min(1.0, max(0.0, confidence_score))
    
    def _determine_validation_status(self, confidence_score: float) -> ValidationStatus:
        """根据置信度分数确定验证状态"""
        if confidence_score >= self.confidence_thresholds['high']:
            return ValidationStatus.VALIDATED
        elif confidence_score >= self.confidence_thresholds['medium']:
            return ValidationStatus.PENDING
        else:
            return ValidationStatus.REJECTED
    
    def _create_failed_mapping(self, context_id: str, job_name: str, 
                             job_run_id: str, reason: str) -> JobExecutionMapping:
        """创建失败的映射记录"""
        mapping = JobExecutionMapping(
            context_id=context_id,
            job_name=job_name,
            job_run_id=job_run_id,
            mapping_timestamp=datetime.now(),
            confidence_score=0.0,
            validation_status=ValidationStatus.REJECTED,
            validation_method=ValidationMethod.MULTI_DIMENSIONAL
        )
        
        mapping.metadata['failure_reason'] = reason
        return mapping
    
    def get_job_run_candidates(self, job_name: str, 
                             time_window_hours: int = 2) -> List[Dict[str, Any]]:
        """获取指定时间窗口内的Job Run候选列表"""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=time_window_hours)
            
            response = self.glue_client.get_job_runs(
                JobName=job_name,
                MaxResults=50  # 限制结果数量
            )
            
            candidates = []
            for job_run in response.get('JobRuns', []):
                job_start_time = job_run.get('StartedOn')
                if job_start_time and start_time <= job_start_time <= end_time:
                    candidates.append(job_run)
            
            # 按开始时间排序
            candidates.sort(key=lambda x: x.get('StartedOn', datetime.min), reverse=True)
            
            return candidates
            
        except Exception as e:
            self.logger.error(f"Failed to get job run candidates: {e}")
            return []