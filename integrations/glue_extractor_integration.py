"""
Glue血缘提取器集成
"""

import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..agents.context_aware_agent import ContextAwareAgent
from ..tools.log_stream_selector import IntelligentLogStreamSelector
from ..utils.logging_config import get_contextual_logger


class GlueExtractorIntegration:
    """Glue血缘提取器集成类"""
    
    def __init__(self):
        self.logger = get_contextual_logger('glue_integration')
        self.context_agent = ContextAwareAgent()
        self.log_selector = IntelligentLogStreamSelector()
    
    def enhance_find_log_streams(self, original_find_log_streams_func, 
                                job_name: str = None, job_run_id: str = None, 
                                start_time: datetime = None) -> List[Dict[str, Any]]:
        """
        增强原有的find_log_streams方法
        
        Args:
            original_find_log_streams_func: 原始的find_log_streams函数
            job_name: Glue作业名称
            job_run_id: 作业运行ID
            start_time: 开始时间
        
        Returns:
            List[Dict[str, Any]]: 增强后的日志流列表
        """
        try:
            self.logger.info(f"Enhancing log stream selection for job {job_name}")
            
            # 1. 识别执行上下文
            context = self.context_agent.identify_execution_context({
                'job_name': job_name,
                'job_run_id': job_run_id,
                'start_time': start_time.isoformat() if start_time else None
            })
            
            # 2. 调用原始方法获取候选日志流
            original_streams = original_find_log_streams_func(job_name, job_run_id, start_time)
            
            if not original_streams:
                self.logger.warning("No log streams found by original method")
                return original_streams
            
            # 3. 使用智能选择器重新排序
            if len(original_streams) > 1:
                selection_result = self.log_selector.select_log_stream(
                    job_name, context, original_streams
                )
                
                selected_stream = selection_result.get('selected_stream')
                if selected_stream:
                    # 将选中的流放在第一位
                    reordered_streams = [selected_stream]
                    reordered_streams.extend([
                        stream for stream in original_streams 
                        if stream != selected_stream
                    ])
                    
                    self.logger.info(f"Reordered streams based on context, confidence: {selection_result.get('confidence', 0.0):.2f}")
                    return reordered_streams
            
            return original_streams
            
        except Exception as e:
            self.logger.error(f"Failed to enhance log stream selection: {e}")
            # 出错时返回原始结果
            return original_find_log_streams_func(job_name, job_run_id, start_time)
    
    def validate_job_run_selection(self, job_name: str, selected_job_run_id: str) -> Dict[str, Any]:
        """
        验证选择的Job Run ID是否正确
        
        Args:
            job_name: 作业名称
            selected_job_run_id: 选择的Job Run ID
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            # 识别执行上下文
            context = self.context_agent.identify_execution_context({
                'job_name': job_name,
                'selected_job_run_id': selected_job_run_id
            })
            
            # 验证Job ID选择
            validation_result = self.context_agent.validate_job_id_selection(
                job_name, selected_job_run_id, context
            )
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Job run validation failed: {e}")
            return {
                'is_valid': False,
                'error': str(e),
                'recommendation': 'proceed_with_caution'
            }
    
    def create_enhanced_extractor_wrapper(self, original_extractor_class):
        """
        创建增强的提取器包装类
        
        Args:
            original_extractor_class: 原始的提取器类
        
        Returns:
            增强的提取器类
        """
        class EnhancedGlueLineageExtractor(original_extractor_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.integration = GlueExtractorIntegration()
            
            def find_log_streams(self, job_name=None, job_run_id=None, start_time=None):
                """重写find_log_streams方法"""
                return self.integration.enhance_find_log_streams(
                    super().find_log_streams, job_name, job_run_id, start_time
                )
            
            def extract_and_save_lineage(self, job_name, job_run_id=None, start_time=None, continuous=False):
                """重写extract_and_save_lineage方法，添加验证"""
                # 如果有job_run_id，先验证
                if job_run_id:
                    validation_result = self.integration.validate_job_run_selection(job_name, job_run_id)
                    
                    if not validation_result.get('is_valid', False):
                        confidence = validation_result.get('confidence_score', 0.0)
                        if confidence < 0.5:
                            self.logger.warning(f"Low confidence Job ID validation: {confidence:.2f}")
                            # 可以选择继续或停止
                
                # 调用原始方法
                return super().extract_and_save_lineage(job_name, job_run_id, start_time, continuous)
        
        return EnhancedGlueLineageExtractor


def patch_existing_extractor():
    """
    为现有的extract-lineage-to-s3.py脚本提供补丁
    """
    try:
        # 动态导入现有的提取器模块
        sys.path.append(os.path.join(os.getcwd(), 'script', 'glue'))
        
        # 这里可以添加对现有脚本的补丁逻辑
        # 例如monkey patching关键方法
        
        integration = GlueExtractorIntegration()
        
        # 返回集成实例供外部使用
        return integration
        
    except Exception as e:
        logger = get_contextual_logger('glue_patch')
        logger.error(f"Failed to patch existing extractor: {e}")
        return None


# 提供给现有脚本使用的便捷函数
def get_enhanced_log_streams(job_name: str, job_run_id: str = None, 
                           start_time: datetime = None) -> List[Dict[str, Any]]:
    """
    为现有脚本提供增强的日志流选择功能
    
    Args:
        job_name: 作业名称
        job_run_id: 作业运行ID
        start_time: 开始时间
    
    Returns:
        List[Dict[str, Any]]: 增强后的日志流列表
    """
    integration = GlueExtractorIntegration()
    
    # 模拟原始的find_log_streams行为
    def mock_original_find_streams(job_name, job_run_id, start_time):
        # 这里应该调用原始的逻辑，现在返回空列表作为示例
        return []
    
    return integration.enhance_find_log_streams(
        mock_original_find_streams, job_name, job_run_id, start_time
    )