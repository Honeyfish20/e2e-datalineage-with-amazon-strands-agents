"""
血缘合并器集成
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..tools.lineage_validator import LineageValidator
from ..utils.logging_config import get_contextual_logger


class LineageMergerIntegration:
    """血缘合并器集成类"""
    
    def __init__(self):
        self.logger = get_contextual_logger('merger_integration')
        self.validator = LineageValidator()
    
    def validate_before_merge(self, glue_lineage_file: str, redshift_lineage_file: str) -> Dict[str, Any]:
        """
        在合并前验证血缘文件的上下文匹配性
        
        Args:
            glue_lineage_file: Glue血缘文件路径
            redshift_lineage_file: Redshift血缘文件路径
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            self.logger.info("Validating lineage files before merge")
            
            # 从文件中提取上下文信息
            glue_context_id = self._extract_context_from_lineage_file(glue_lineage_file)
            redshift_context_id = self._extract_context_from_lineage_file(redshift_lineage_file)
            
            if not glue_context_id or not redshift_context_id:
                return {
                    'valid': False,
                    'reason': 'Cannot extract context IDs from lineage files',
                    'recommendation': 'manual_review'
                }
            
            # 检查合并兼容性
            compatible = self.validator.check_merge_compatibility(glue_context_id, redshift_context_id)
            
            if not compatible:
                return {
                    'valid': False,
                    'reason': 'Context incompatibility detected',
                    'glue_context': glue_context_id,
                    'redshift_context': redshift_context_id,
                    'recommendation': 'block_merge'
                }
            
            # 执行详细验证
            validation_result = self.validator.validate_lineage_context_match(
                context_id=glue_context_id,  # 使用Glue上下文作为主上下文
                glue_lineage_file=glue_lineage_file,
                redshift_lineage_file=redshift_lineage_file
            )
            
            return {
                'valid': validation_result.is_valid,
                'confidence': validation_result.confidence_score,
                'recommendation': validation_result.recommendation.value,
                'issues': [issue.__dict__ for issue in validation_result.issues],
                'glue_context': glue_context_id,
                'redshift_context': redshift_context_id
            }
            
        except Exception as e:
            self.logger.error(f"Validation before merge failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'recommendation': 'manual_review'
            }
    
    def enhance_file_selection(self, s3_bucket: str, glue_prefix: str, redshift_prefix: str) -> Dict[str, Any]:
        """
        增强文件选择逻辑，不仅仅基于时间戳
        
        Args:
            s3_bucket: S3存储桶
            glue_prefix: Glue血缘文件前缀
            redshift_prefix: Redshift血缘文件前缀
        
        Returns:
            Dict[str, Any]: 选择结果
        """
        try:
            import boto3
            
            s3_client = boto3.client('s3')
            
            # 获取Glue血缘文件列表
            glue_files = self._list_s3_files(s3_client, s3_bucket, glue_prefix)
            redshift_files = self._list_s3_files(s3_client, s3_bucket, redshift_prefix)
            
            if not glue_files or not redshift_files:
                return {
                    'success': False,
                    'reason': 'No lineage files found',
                    'glue_files_count': len(glue_files),
                    'redshift_files_count': len(redshift_files)
                }
            
            # 智能匹配文件对
            best_match = self._find_best_file_match(glue_files, redshift_files)
            
            if not best_match:
                return {
                    'success': False,
                    'reason': 'No compatible file pairs found',
                    'recommendation': 'check_execution_contexts'
                }
            
            return {
                'success': True,
                'glue_file': best_match['glue_file'],
                'redshift_file': best_match['redshift_file'],
                'match_confidence': best_match['confidence'],
                'match_reason': best_match['reason']
            }
            
        except Exception as e:
            self.logger.error(f"Enhanced file selection failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_enhanced_merger_wrapper(self, original_merger_class):
        """
        创建增强的合并器包装类
        
        Args:
            original_merger_class: 原始的合并器类
        
        Returns:
            增强的合并器类
        """
        class EnhancedTableLineageMerger(original_merger_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.integration = LineageMergerIntegration()
            
            def process_lineage(self):
                """重写process_lineage方法，添加验证"""
                try:
                    # 1. 增强文件选择
                    file_selection = self.integration.enhance_file_selection(
                        self.bucket_name, 'lineage-reports/glue-jobs/', 'lineage/redshift/'
                    )
                    
                    if not file_selection.get('success', False):
                        self.logger.warning(f"Enhanced file selection failed: {file_selection.get('reason')}")
                        # 回退到原始逻辑
                        return super().process_lineage()
                    
                    glue_file = file_selection['glue_file']['key']
                    redshift_file = file_selection['redshift_file']['key']
                    
                    # 2. 验证合并兼容性
                    validation_result = self.integration.validate_before_merge(
                        f"s3://{self.bucket_name}/{glue_file}",
                        f"s3://{self.bucket_name}/{redshift_file}"
                    )
                    
                    if not validation_result.get('valid', False):
                        self.logger.error(f"Merge validation failed: {validation_result.get('reason')}")
                        
                        if validation_result.get('recommendation') == 'block_merge':
                            self.logger.error("Merge blocked due to context incompatibility")
                            return None
                    
                    # 3. 执行原始合并逻辑
                    return super().process_lineage()
                    
                except Exception as e:
                    self.logger.error(f"Enhanced merger processing failed: {e}")
                    # 回退到原始逻辑
                    return super().process_lineage()
        
        return EnhancedTableLineageMerger
    
    def _extract_context_from_lineage_file(self, file_path: str) -> Optional[str]:
        """从血缘文件中提取上下文ID"""
        try:
            if file_path.startswith('s3://'):
                # S3文件处理
                import boto3
                s3_client = boto3.client('s3')
                
                bucket, key = self._parse_s3_path(file_path)
                response = s3_client.get_object(Bucket=bucket, Key=key)
                content = response['Body'].read().decode('utf-8')
                
                data = json.loads(content)
            else:
                # 本地文件处理
                with open(file_path, 'r') as f:
                    data = json.load(f)
            
            # 尝试从不同位置提取上下文ID
            # 1. 从metadata中提取
            metadata = data.get('metadata', {})
            if 'context_id' in metadata:
                return metadata['context_id']
            
            # 2. 从events中提取
            events = data.get('events', [])
            for event in events:
                if '_metadata' in event and 'context_id' in event['_metadata']:
                    return event['_metadata']['context_id']
            
            # 3. 从文件名中推断
            if file_path:
                # 尝试从文件名中提取时间戳等信息来构造上下文ID
                import re
                timestamp_match = re.search(r'(\d{8}_\d{6})', file_path)
                if timestamp_match:
                    timestamp = timestamp_match.group(1)
                    # 构造一个可能的上下文ID
                    return f"inferred_{timestamp}"
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to extract context from {file_path}: {e}")
            return None
    
    def _list_s3_files(self, s3_client, bucket: str, prefix: str) -> List[Dict[str, Any]]:
        """列出S3文件"""
        try:
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            
            files = []
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.json'):
                    files.append({
                        'key': obj['Key'],
                        'last_modified': obj['LastModified'],
                        'size': obj['Size']
                    })
            
            # 按修改时间排序
            files.sort(key=lambda x: x['last_modified'], reverse=True)
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to list S3 files: {e}")
            return []
    
    def _find_best_file_match(self, glue_files: List[Dict[str, Any]], 
                            redshift_files: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """找到最佳的文件匹配对"""
        best_match = None
        best_confidence = 0.0
        
        for glue_file in glue_files[:5]:  # 只检查最新的5个文件
            for redshift_file in redshift_files[:5]:
                # 计算时间匹配度
                time_diff = abs((glue_file['last_modified'] - redshift_file['last_modified']).total_seconds())
                
                # 时间差越小，匹配度越高
                if time_diff <= 3600:  # 1小时内
                    confidence = 1.0 - (time_diff / 3600)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = {
                            'glue_file': glue_file,
                            'redshift_file': redshift_file,
                            'confidence': confidence,
                            'reason': f'Time match within {time_diff:.0f} seconds'
                        }
        
        return best_match
    
    def _parse_s3_path(self, s3_path: str) -> tuple:
        """解析S3路径"""
        if not s3_path.startswith('s3://'):
            raise ValueError(f"Invalid S3 path: {s3_path}")
        
        path_parts = s3_path[5:].split('/', 1)
        bucket = path_parts[0]
        key = path_parts[1] if len(path_parts) > 1 else ''
        
        return bucket, key


def patch_existing_merger():
    """
    为现有的table_lineage_merger.py脚本提供补丁
    """
    try:
        integration = LineageMergerIntegration()
        return integration
        
    except Exception as e:
        logger = get_contextual_logger('merger_patch')
        logger.error(f"Failed to patch existing merger: {e}")
        return None