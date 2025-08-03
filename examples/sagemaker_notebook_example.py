#!/usr/bin/env python3
"""
SageMaker Notebook血缘管理示例

演示在SageMaker Notebook环境中如何使用Enhanced Lineage Agent。
"""

import sys
import os
import logging
from datetime import datetime
import json

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.context_aware_agent import ContextAwareAgent
from utils.config_manager import ConfigManager
from models.execution_context import EnvironmentType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def simulate_sagemaker_environment():
    """模拟SageMaker环境变量"""
    os.environ['SM_CURRENT_INSTANCE_TYPE'] = 'ml.t3.medium'
    os.environ['SM_CURRENT_INSTANCE_GROUP'] = 'sagemaker-notebook-instance'
    os.environ['USER'] = 'sagemaker-user'

def main():
    """主函数"""
    logger = logging.getLogger(__name__)
    logger.info("Starting SageMaker Notebook lineage example")
    
    try:
        # 模拟SageMaker环境
        simulate_sagemaker_environment()
        
        # 1. 初始化系统
        config = ConfigManager()
        agent = ContextAwareAgent(config.get_all_config())
        
        # 2. 识别SageMaker执行上下文
        logger.info("Identifying SageMaker execution context...")
        context = agent.identify_execution_context()
        
        print(f"\n=== SageMaker Execution Context ===")
        print(f"Context ID: {context.context_id}")
        print(f"Environment Type: {context.environment_type.value}")
        print(f"Is SageMaker Environment: {context.is_sagemaker_environment()}")
        print(f"Notebook Instance: {context.notebook_instance}")
        print(f"SageMaker Role: {context.sagemaker_role}")
        print(f"Working Directory: {context.working_directory}")
        
        # 3. 模拟数据科学工作流的血缘数据
        logger.info("Simulating data science workflow lineage...")
        
        # 模拟SageMaker Notebook的数据操作
        sagemaker_lineage = {
            'context_id': context.context_id,
            'extraction_timestamp': datetime.now().isoformat(),
            'notebook_instance': context.notebook_instance,
            'sagemaker_role': context.sagemaker_role,
            'operations': [
                {
                    'operation_type': 'data_read',
                    'inputs': ['s3://ml-data-bucket/raw/customer_data.csv'],
                    'outputs': [],
                    'cell_id': 'cell_001',
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'operation_type': 'feature_engineering',
                    'inputs': ['customer_data.csv'],
                    'outputs': ['s3://ml-data-bucket/features/customer_features.parquet'],
                    'cell_id': 'cell_002',
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'operation_type': 'model_training',
                    'inputs': ['s3://ml-data-bucket/features/customer_features.parquet'],
                    'outputs': ['s3://ml-models-bucket/customer_churn_model/'],
                    'cell_id': 'cell_003',
                    'timestamp': datetime.now().isoformat()
                }
            ],
            'metadata': {
                'execution_context': {
                    'context_id': context.context_id
                }
            }
        }\n        \n        # 模拟触发的Glue ETL作业血缘\n        glue_lineage = {\n            'context_id': context.context_id,\n            'extraction_timestamp': datetime.now().isoformat(),\n            'events': [\n                {\n                    'inputs': [{\n                        'name': 's3://ml-models-bucket/customer_churn_model/',\n                        'namespace': 's3'\n                    }],\n                    'outputs': [{\n                        'name': 'analytics.customer_predictions',\n                        'namespace': 'redshift'\n                    }],\n                    'job': {'name': 'model-deployment-job'}\n                }\n            ],\n            'metadata': {\n                'execution_context': {\n                    'context_id': context.context_id\n                },\n                'triggered_by': 'sagemaker_notebook'\n            }\n        }\n        \n        # 模拟Redshift数据处理血缘\n        redshift_lineage = {\n            'context_id': context.context_id,\n            'extraction_timestamp': datetime.now().isoformat(),\n            'queries': [\n                {\n                    'input_tables': ['analytics.customer_predictions'],\n                    'output_tables': ['reports.customer_churn_report'],\n                    'sql': '''INSERT INTO reports.customer_churn_report \n                             SELECT customer_id, prediction_score, risk_level \n                             FROM analytics.customer_predictions \n                             WHERE prediction_score > 0.7'''\n                }\n            ]\n        }\n        \n        # 4. 合并多源血缘数据\n        logger.info(\"Merging multi-source lineage data...\")\n        \n        lineage_sources = {\n            'sagemaker': sagemaker_lineage,\n            'glue': glue_lineage,\n            'redshift': redshift_lineage\n        }\n        \n        merge_result = agent.merge_lineage_data(lineage_sources, context)\n        \n        print(f\"\\n=== Multi-Source Lineage Merge Result ===\")\n        print(f\"Success: {merge_result['success']}\")\n        print(f\"Sources Processed: {merge_result.get('sources_processed', [])}\")\n        print(f\"Correlation Status: {merge_result.get('correlation_status', 'unknown')}\")\n        \n        if merge_result['success']:\n            merged_lineage = merge_result['merged_lineage']\n            print(f\"\\n=== End-to-End Lineage Summary ===\")\n            print(f\"Total Events: {len(merged_lineage.get('lineage_events', []))}\")\n            print(f\"Data Entities: {len(merged_lineage.get('data_entities', []))}\")\n            \n            # 显示数据流路径\n            lineage_graph = merged_lineage.get('lineage_graph', {})\n            print(f\"Graph Nodes: {lineage_graph.get('node_count', 0)}\")\n            print(f\"Graph Edges: {lineage_graph.get('edge_count', 0)}\")\n            \n            # 显示数据实体\n            print(f\"\\n=== Data Entities ===\")\n            for entity in merged_lineage.get('data_entities', [])[:5]:  # 显示前5个\n                print(f\"  - {entity}\")\n            \n            # 显示血缘事件\n            print(f\"\\n=== Lineage Events ===\")\n            for i, event in enumerate(merged_lineage.get('lineage_events', [])[:3]):  # 显示前3个\n                print(f\"  Event {i+1}:\")\n                print(f\"    Source: {event.get('source', 'unknown')}\")\n                print(f\"    Type: {event.get('event_type', 'unknown')}\")\n                print(f\"    Inputs: {event.get('inputs', [])}\")\n                print(f\"    Outputs: {event.get('outputs', [])}\")\n        else:\n            print(f\"Error: {merge_result.get('error', 'Unknown error')}\")\n        \n        # 5. 演示血缘查询功能\n        logger.info(\"Demonstrating lineage query capabilities...\")\n        \n        if merge_result['success']:\n            # 模拟血缘查询\n            print(f\"\\n=== Lineage Query Example ===\")\n            \n            # 查询特定数据源的下游影响\n            data_source = \"s3://ml-data-bucket/raw/customer_data.csv\"\n            print(f\"Querying downstream impact of: {data_source}\")\n            \n            # 这里可以实现实际的查询逻辑\n            downstream_entities = []\n            for event in merged_lineage.get('lineage_events', []):\n                if data_source in event.get('inputs', []):\n                    downstream_entities.extend(event.get('outputs', []))\n            \n            print(f\"Downstream entities: {list(set(downstream_entities))}\")\n            \n            # 查询特定输出的上游依赖\n            data_target = \"reports.customer_churn_report\"\n            print(f\"\\nQuerying upstream dependencies of: {data_target}\")\n            \n            upstream_entities = []\n            for event in merged_lineage.get('lineage_events', []):\n                if data_target in event.get('outputs', []):\n                    upstream_entities.extend(event.get('inputs', []))\n            \n            print(f\"Upstream entities: {list(set(upstream_entities))}\")\n        \n        # 6. 显示验证详情\n        validation_result = merge_result.get('validation_result', {})\n        if validation_result:\n            print(f\"\\n=== Validation Details ===\")\n            print(f\"Overall Valid: {validation_result.get('is_valid', False)}\")\n            print(f\"Confidence Score: {validation_result.get('confidence_score', 0.0):.3f}\")\n            print(f\"Context Match: {validation_result.get('context_match', False)}\")\n            print(f\"Data Consistency: {validation_result.get('data_consistency', False)}\")\n            print(f\"Temporal Alignment: {validation_result.get('temporal_alignment', False)}\")\n            \n            # 显示建议\n            suggested_actions = validation_result.get('suggested_actions', [])\n            if suggested_actions:\n                print(f\"\\nSuggested Actions:\")\n                for action in suggested_actions[:3]:\n                    print(f\"  - {action.get('action', 'Unknown action')} (Priority: {action.get('priority', 'unknown')})\")\n        \n        logger.info(\"SageMaker Notebook lineage example completed successfully\")\n        \n    except Exception as e:\n        logger.error(f\"SageMaker example execution failed: {e}\")\n        print(f\"\\nError: {e}\")\n        return 1\n    \n    return 0\n\n\nif __name__ == \"__main__\":\n    exit_code = main()\n    sys.exit(exit_code)