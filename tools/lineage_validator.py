"""
血缘验证器工具
"""

import boto3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from strands import tool

from ..models.validation_result import (
    LineageValidationResult, ValidationIssue, ValidationIssueType, RecommendationType
)
from ..models.execution_context import ExecutionContext
from ..interfaces import ILineageValidator
from ..config import get_config
from ..utils.logging_config import get_contextual_logger


class LineageValidator(ILineageValidator):
    """血缘验证器实现"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_contextual_logger('lineage_validator')
        
        # AWS客户端
        self.s3_client = boto3.client('s3', region_name=self.config.aws_region)
        self.dynamodb = boto3.resource('dynamodb', region_name=self.config.dynamodb.region)
        
        # DynamoDB表
        self.context_table = self.dynamodb.Table(self.config.dynamodb.execution_context_table)
        self.mapping_table = self.dynamodb.Table(self.config.dynamodb.job_mapping_table)
        self.validation_table = self.dynamodb.Table(self.config.dynamodb.validation_result_table)
    
    def validate_lineage_context_match(
        self,
        context_id: str,
        glue_lineage_file: Optional[str] = None,
        redshift_lineage_file: Optional[str] = None,
        job_run_ids: List[str] = None
    ) -> LineageValidationResult:
        """验证血缘数据的上下文匹配性"""
        try:
            self.logger.info(f"Validating lineage context match for {context_id}")
            
            # 创建验证结果对象
            validation_result = LineageValidationResult(
                context_id=context_id,
                validation_timestamp=datetime.now(),
                is_valid=False,
                confidence_score=0.0,
                glue_lineage_file=glue_lineage_file,
                redshift_lineage_file=redshift_lineage_file,
                job_run_ids=job_run_ids or []
            )
            
            # 获取执行上下文信息
            context_info = self._get_execution_context(context_id)
            if not context_info:
                validation_result.add_issue(
                    ValidationIssueType.MISSING_CONTEXT,
                    'critical',
                    f'Execution context {context_id} not found',
                    ['context_lookup'],
                    'Ensure the context ID is correct and the context was properly stored'
                )
                validation_result.recommendation = RecommendationType.BLOCK
                return validation_result
            
            # 验证Glue血缘文件
            if glue_lineage_file:
                glue_validation = self._validate_glue_lineage_file(glue_lineage_file, context_info)
                validation_result.validation_details['glue_validation'] = glue_validation
                if not glue_validation.get('valid', False):
                    validation_result.add_issue(
                        ValidationIssueType.CONTEXT_MISMATCH,
                        'high',
                        f'Glue lineage file context mismatch: {glue_validation.get("reason", "unknown")}',
                        ['glue_lineage'],
                        'Verify the Glue lineage file belongs to the correct execution context'
                    )
            
            # 验证Redshift血缘文件
            if redshift_lineage_file:
                redshift_validation = self._validate_redshift_lineage_file(redshift_lineage_file, context_info)
                validation_result.validation_details['redshift_validation'] = redshift_validation
                if not redshift_validation.get('valid', False):
                    validation_result.add_issue(
                        ValidationIssueType.CONTEXT_MISMATCH,
                        'high',
                        f'Redshift lineage file context mismatch: {redshift_validation.get("reason", "unknown")}',
                        ['redshift_lineage'],
                        'Verify the Redshift lineage file belongs to the correct execution context'
                    )
            
            # 验证Job Run IDs
            if job_run_ids:
                job_validation = self._validate_job_run_ids(job_run_ids, context_id)
                validation_result.validation_details['job_validation'] = job_validation
                for job_id, job_result in job_validation.items():
                    if not job_result.get('valid', False):
                        validation_result.add_issue(
                            ValidationIssueType.CONTEXT_MISMATCH,
                            'medium',
                            f'Job Run ID {job_id} context mismatch: {job_result.get("reason", "unknown")}',
                            ['job_mapping'],
                            f'Verify Job Run ID {job_id} belongs to the correct execution context'
                        )
            
            # 计算整体验证结果
            validation_result = self._calculate_overall_validation(validation_result)
            
            # 存储验证结果
            self._store_validation_result(validation_result)
            
            self.logger.info(f"Validation completed with confidence {validation_result.confidence_score:.2f}")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Lineage validation failed: {e}")
            # 返回失败的验证结果
            error_result = LineageValidationResult(
                context_id=context_id,
                validation_timestamp=datetime.now(),
                is_valid=False,
                confidence_score=0.0,
                recommendation=RecommendationType.BLOCK,
                warning_message=f"Validation failed: {str(e)}"
            )
            error_result.add_issue(
                ValidationIssueType.MISSING_CONTEXT,
                'critical',
                f'Validation process failed: {str(e)}',
                ['validation_process']
            )
            return error_result
    
    def check_merge_compatibility(
        self,
        glue_context_id: str,
        redshift_context_id: str
    ) -> bool:
        """检查两个上下文的血缘数据是否可以合并"""
        try:
            self.logger.info(f"Checking merge compatibility: {glue_context_id} <-> {redshift_context_id}")
            
            # 获取两个上下文信息
            glue_context = self._get_execution_context(glue_context_id)
            redshift_context = self._get_execution_context(redshift_context_id)
            
            if not glue_context or not redshift_context:
                self.logger.warning("One or both contexts not found")
                return False
            
            # 检查时间兼容性
            time_compatible = self._check_time_compatibility(glue_context, redshift_context)
            
            # 检查环境兼容性
            env_compatible = self._check_environment_compatibility(glue_context, redshift_context)
            
            # 检查用户兼容性
            user_compatible = self._check_user_compatibility(glue_context, redshift_context)
            
            # 综合判断
            compatible = time_compatible and env_compatible and user_compatible
            
            self.logger.info(f"Merge compatibility result: {compatible}")
            return compatible
            
        except Exception as e:
            self.logger.error(f"Merge compatibility check failed: {e}")
            return False
    
    def _get_execution_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """获取执行上下文信息"""
        try:
            response = self.context_table.get_item(Key={'context_id': context_id})
            return response.get('Item')
        except Exception as e:
            self.logger.warning(f"Failed to get execution context {context_id}: {e}")
            return None
    
    def _validate_glue_lineage_file(self, file_path: str, context_info: Dict[str, Any]) -> Dict[str, Any]:
        """验证Glue血缘文件"""
        try:
            # 解析S3路径
            if file_path.startswith('s3://'):
                bucket, key = self._parse_s3_path(file_path)
                
                # 获取文件元数据
                response = self.s3_client.head_object(Bucket=bucket, Key=key)
                file_timestamp = response['LastModified']
                
                # 检查时间匹配
                context_time = datetime.fromisoformat(context_info['timestamp'])
                time_diff = abs((file_timestamp - context_time).total_seconds())
                
                # 如果时间差在合理范围内，认为匹配
                if time_diff <= 3600:  # 1小时内
                    return {'valid': True, 'time_diff': time_diff, 'method': 's3_metadata'}
                else:
                    return {'valid': False, 'reason': f'Time mismatch: {time_diff}s', 'time_diff': time_diff}
            
            # 本地文件路径的处理
            return {'valid': True, 'method': 'local_file', 'reason': 'Local file assumed valid'}
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def _validate_redshift_lineage_file(self, file_path: str, context_info: Dict[str, Any]) -> Dict[str, Any]:
        """验证Redshift血缘文件"""
        # 类似于Glue血缘文件的验证逻辑
        return self._validate_glue_lineage_file(file_path, context_info)
    
    def _validate_job_run_ids(self, job_run_ids: List[str], context_id: str) -> Dict[str, Dict[str, Any]]:
        """验证Job Run IDs"""
        results = {}
        
        for job_id in job_run_ids:
            try:
                # 查询映射表
                response = self.mapping_table.query(
                    IndexName='JobRunIdIndex',  # 假设有这个GSI
                    KeyConditionExpression='job_run_id = :job_id',
                    ExpressionAttributeValues={':job_id': job_id}
                )
                
                items = response.get('Items', [])
                
                # 检查是否有匹配的上下文
                context_match = any(item.get('context_id') == context_id for item in items)
                
                if context_match:
                    results[job_id] = {'valid': True, 'method': 'mapping_table_lookup'}
                else:
                    results[job_id] = {'valid': False, 'reason': 'No matching context in mapping table'}
                    
            except Exception as e:
                results[job_id] = {'valid': False, 'error': str(e)}
        
        return results
    
    def _calculate_overall_validation(self, validation_result: LineageValidationResult) -> LineageValidationResult:
        """计算整体验证结果"""
        # 计算置信度分数
        total_checks = 0
        passed_checks = 0
        
        # Glue验证
        glue_validation = validation_result.validation_details.get('glue_validation', {})
        if glue_validation:
            total_checks += 1
            if glue_validation.get('valid', False):
                passed_checks += 1
                validation_result.context_match = True
        
        # Redshift验证
        redshift_validation = validation_result.validation_details.get('redshift_validation', {})
        if redshift_validation:
            total_checks += 1
            if redshift_validation.get('valid', False):
                passed_checks += 1
        
        # Job验证
        job_validation = validation_result.validation_details.get('job_validation', {})
        if job_validation:
            for job_result in job_validation.values():
                total_checks += 1
                if job_result.get('valid', False):
                    passed_checks += 1
        
        # 计算置信度
        if total_checks > 0:
            validation_result.confidence_score = passed_checks / total_checks
        else:
            validation_result.confidence_score = 0.0
        
        # 确定整体有效性
        validation_result.is_valid = validation_result.confidence_score >= 0.7
        
        # 确定推荐操作
        if validation_result.has_critical_issues():
            validation_result.recommendation = RecommendationType.BLOCK
        elif validation_result.confidence_score >= 0.9:
            validation_result.recommendation = RecommendationType.PROCEED
        elif validation_result.confidence_score >= 0.7:
            validation_result.recommendation = RecommendationType.WARN
        else:
            validation_result.recommendation = RecommendationType.MANUAL_REVIEW
        
        return validation_result
    
    def _check_time_compatibility(self, context1: Dict[str, Any], context2: Dict[str, Any]) -> bool:
        """检查时间兼容性"""
        try:
            time1 = datetime.fromisoformat(context1['timestamp'])
            time2 = datetime.fromisoformat(context2['timestamp'])
            
            # 如果两个上下文的时间差在1小时内，认为兼容
            time_diff = abs((time1 - time2).total_seconds())
            return time_diff <= 3600
            
        except Exception:
            return False
    
    def _check_environment_compatibility(self, context1: Dict[str, Any], context2: Dict[str, Any]) -> bool:
        """检查环境兼容性"""
        try:
            env1 = context1.get('environment_type')
            env2 = context2.get('environment_type')
            
            # 相同环境类型兼容
            if env1 == env2:
                return True
            
            # 某些环境类型组合是兼容的
            compatible_combinations = [
                ('sagemaker_notebook', 'standalone_script'),
                ('jupyter_notebook', 'standalone_script')
            ]
            
            return (env1, env2) in compatible_combinations or (env2, env1) in compatible_combinations
            
        except Exception:
            return False
    
    def _check_user_compatibility(self, context1: Dict[str, Any], context2: Dict[str, Any]) -> bool:
        """检查用户兼容性"""
        try:
            user1 = context1.get('user_id')
            user2 = context2.get('user_id')
            
            # 如果都有用户ID，必须相同
            if user1 and user2:
                return user1 == user2
            
            # 如果有一个没有用户ID，认为兼容
            return True
            
        except Exception:
            return True  # 默认兼容
    
    def _parse_s3_path(self, s3_path: str) -> tuple:
        """解析S3路径"""
        if not s3_path.startswith('s3://'):
            raise ValueError(f"Invalid S3 path: {s3_path}")
        
        path_parts = s3_path[5:].split('/', 1)
        bucket = path_parts[0]
        key = path_parts[1] if len(path_parts) > 1 else ''
        
        return bucket, key
    
    def _store_validation_result(self, validation_result: LineageValidationResult):
        """存储验证结果"""
        try:
            item = validation_result.to_dict()
            # 添加TTL (30天后过期)
            ttl = int((datetime.now() + timedelta(days=30)).timestamp())
            item['ttl'] = ttl
            
            self.validation_table.put_item(Item=item)
            self.logger.debug(f"Stored validation result for {validation_result.context_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to store validation result: {e}")


@tool
def validate_lineage_context_match(
    context_id: str,
    glue_lineage_file: Optional[str] = None,
    redshift_lineage_file: Optional[str] = None,
    job_run_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Strands工具：验证血缘数据的上下文匹配性
    
    Args:
        context_id: 上下文ID
        glue_lineage_file: Glue血缘文件路径
        redshift_lineage_file: Redshift血缘文件路径
        job_run_ids: 相关的Job Run ID列表
    
    Returns:
        Dict[str, Any]: 验证结果
    """
    validator = LineageValidator()
    result = validator.validate_lineage_context_match(
        context_id, glue_lineage_file, redshift_lineage_file, job_run_ids or []
    )
    return result.to_dict()


@tool
def check_lineage_merge_compatibility(glue_context_id: str, redshift_context_id: str) -> bool:
    """
    Strands工具：检查两个上下文的血缘数据是否可以合并
    
    Args:
        glue_context_id: Glue血缘的上下文ID
        redshift_context_id: Redshift血缘的上下文ID
    
    Returns:
        bool: 是否可以合并
    """
    validator = LineageValidator()
    return validator.check_merge_compatibility(glue_context_id, redshift_context_id)