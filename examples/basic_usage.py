#!/usr/bin/env python3
"""
基础使用示例

演示如何使用Enhanced Lineage Agent进行血缘管理。
"""

import sys
import os
import logging
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.context_aware_agent import ContextAwareAgent
from utils.config_manager import ConfigManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """主函数"""
    logger = logging.getLogger(__name__)
    logger.info("Starting Enhanced Lineage Agent basic usage example")
    
    try:
        # 1. 初始化配置管理器
        config = ConfigManager()
        logger.info("Configuration manager initialized")
        
        # 2. 创建Context-Aware Agent
        agent = ContextAwareAgent(config.get_all_config())
        logger.info("Context-Aware Agent created")
        
        # 3. 识别执行上下文
        logger.info("Identifying execution context...")
        context = agent.identify_execution_context()
        
        print(f"\n=== Execution Context ===")
        print(f"Context ID: {context.context_id}")
        print(f"Environment Type: {context.environment_type.value}")
        print(f"Process ID: {context.process_id}")
        print(f"User ID: {context.user_id}")
        print(f"Working Directory: {context.working_directory}")
        print(f"Command Line: {context.command_line}")
        
        if context.is_sagemaker_environment():
            print(f"Notebook Instance: {context.notebook_instance}")
            print(f"SageMaker Role: {context.sagemaker_role}")
        
        # 4. 模拟Job ID验证
        logger.info("Simulating Job ID validation...")
        job_name = "example-etl-job"
        job_run_id = "jr_example123456789"
        
        # 注意：这里会失败，因为我们使用的是模拟的Job ID
        try:
            mapping = agent.validate_job_id_selection(job_name, job_run_id, context)
            
            print(f"\n=== Job ID Validation ===")
            print(f"Job Name: {job_name}")
            print(f"Job Run ID: {job_run_id}")
            print(f"Validation Status: {mapping.validation_status.value}")
            print(f"Confidence Score: {mapping.confidence_score:.3f}")
            print(f"Time Difference: {mapping.time_diff_seconds} seconds")
            
        except Exception as e:
            logger.warning(f"Job ID validation failed (expected for demo): {e}")
            print(f"\n=== Job ID Validation ===")
            print(f"Job Name: {job_name}")
            print(f"Job Run ID: {job_run_id}")
            print(f"Status: Failed (demo with non-existent job)")
        
        # 5. 演示血缘数据收集（模拟）
        logger.info("Demonstrating lineage data collection...")
        
        # 模拟多源血缘数据
        mock_lineage_sources = {
            'glue': {
                'context_id': context.context_id,
                'extraction_timestamp': datetime.now().isoformat(),
                'events': [
                    {
                        'inputs': [{'name': 's3://example-bucket/input/data.csv'}],
                        'outputs': [{'name': 's3://example-bucket/output/processed_data.parquet'}],
                        'job': {'name': 'example-etl-job'}
                    }
                ],
                'metadata': {
                    'execution_context': {
                        'context_id': context.context_id
                    }
                }
            },
            'redshift': {
                'context_id': context.context_id,
                'extraction_timestamp': datetime.now().isoformat(),
                'queries': [
                    {
                        'input_tables': ['staging.raw_data'],
                        'output_tables': ['analytics.processed_data'],
                        'sql': 'INSERT INTO analytics.processed_data SELECT * FROM staging.raw_data WHERE status = "active"'
                    }
                ]
            }
        }
        
        # 6. 血缘数据合并
        logger.info("Merging lineage data...")
        merge_result = agent.merge_lineage_data(mock_lineage_sources, context)
        
        print(f"\n=== Lineage Merge Result ===")
        print(f"Success: {merge_result['success']}")
        print(f"Sources Processed: {merge_result.get('sources_processed', [])}")
        print(f"Correlation Status: {merge_result.get('correlation_status', 'unknown')}")
        
        if merge_result['success']:
            merged_lineage = merge_result['merged_lineage']
            print(f"Events Count: {len(merged_lineage.get('lineage_events', []))}")
            print(f"Data Entities: {len(merged_lineage.get('data_entities', []))}")
            
            # 显示血缘图统计
            lineage_graph = merged_lineage.get('lineage_graph', {})
            print(f"Graph Nodes: {lineage_graph.get('node_count', 0)}")
            print(f"Graph Edges: {lineage_graph.get('edge_count', 0)}")
        else:
            print(f"Error: {merge_result.get('error', 'Unknown error')}")
        
        # 7. 显示验证结果
        validation_result = merge_result.get('validation_result', {})
        if validation_result:
            print(f"\n=== Validation Details ===")
            print(f"Validation Valid: {validation_result.get('is_valid', False)}")
            print(f"Confidence Score: {validation_result.get('confidence_score', 0.0):.3f}")
            print(f"Sources Validated: {validation_result.get('sources_validated', [])}")
            
            warnings = validation_result.get('warnings', [])
            if warnings:
                print(f"Warnings: {len(warnings)}")
                for warning in warnings[:3]:  # 显示前3个警告
                    print(f"  - {warning.get('message', 'Unknown warning')}")
        
        logger.info("Basic usage example completed successfully")
        
    except Exception as e:
        logger.error(f"Example execution failed: {e}")
        print(f"\nError: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)