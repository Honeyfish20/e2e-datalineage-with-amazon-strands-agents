#!/usr/bin/env python3
"""
Context-Aware Agent 测试

测试核心代理功能的单元测试。
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.context_aware_agent import ContextAwareAgent
from models.execution_context import ExecutionContext, EnvironmentType
from models.job_mapping import JobExecutionMapping, ValidationStatus
from utils.config_manager import ConfigManager


class TestContextAwareAgent(unittest.TestCase):
    """Context-Aware Agent测试类"""
    
    def setUp(self):
        """测试设置"""
        # 创建模拟配置
        self.mock_config = {
            'agent': {
                'model': {
                    'model_id': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                    'max_tokens': 4000,
                    'temperature': 0.1
                },
                'context': {
                    'timeout_seconds': 30,
                    'cache_ttl_minutes': 60
                },
                'job_validation': {
                    'time_tolerance_seconds': 300,
                    'min_confidence_threshold': 0.7
                }
            },
            'aws': {
                'region': 'us-east-1'
            }
        }
        
        # 创建代理实例
        with patch('enhanced_lineage_agent.utils.config_manager.ConfigManager'):
            self.agent = ContextAwareAgent(self.mock_config)
    
    def test_identify_execution_context_standalone_script(self):
        """测试独立脚本环境的上下文识别"""
        with patch('os.getcwd', return_value='/home/user/scripts'), \
             patch('os.getpid', return_value=12345), \
             patch('sys.argv', ['test_script.py', '--arg1', 'value1']), \
             patch('os.environ.get') as mock_env:
            
            # 模拟环境变量
            mock_env.side_effect = lambda key, default=None: {
                'USER': 'testuser',
                'SM_CURRENT_INSTANCE_TYPE': None,
                'AIRFLOW_CTX_DAG_ID': None,
                'JPY_PARENT_PID': None
            }.get(key, default)
            
            context = self.agent.identify_execution_context()
            
            self.assertIsInstance(context, ExecutionContext)
            self.assertEqual(context.environment_type, EnvironmentType.STANDALONE_SCRIPT)
            self.assertEqual(context.process_id, 12345)
            self.assertEqual(context.user_id, 'testuser')
            self.assertEqual(context.working_directory, '/home/user/scripts')
            self.assertIn('test_script.py', context.command_line)
    
    def test_identify_execution_context_sagemaker(self):
        """测试SageMaker环境的上下文识别"""
        with patch('os.getcwd', return_value='/opt/ml/code'), \
             patch('os.getpid', return_value=23456), \
             patch('sys.argv', ['jupyter-notebook']), \
             patch('os.environ.get') as mock_env:
            
            # 模拟SageMaker环境变量
            mock_env.side_effect = lambda key, default=None: {
                'USER': 'sagemaker-user',
                'SM_CURRENT_INSTANCE_TYPE': 'ml.t3.medium',
                'SM_CURRENT_INSTANCE_GROUP': 'notebook-instance',
                'AIRFLOW_CTX_DAG_ID': None,
                'JPY_PARENT_PID': None
            }.get(key, default)
            
            context = self.agent.identify_execution_context()
            
            self.assertIsInstance(context, ExecutionContext)
            self.assertEqual(context.environment_type, EnvironmentType.SAGEMAKER_NOTEBOOK)
            self.assertEqual(context.notebook_instance, 'ml.t3.medium')
            self.assertEqual(context.sagemaker_role, 'notebook-instance')
            self.assertTrue(context.is_sagemaker_environment())
    
    def test_identify_execution_context_airflow(self):
        """测试Airflow环境的上下文识别"""
        with patch('os.getcwd', return_value='/opt/airflow'), \
             patch('os.getpid', return_value=34567), \
             patch('sys.argv', ['airflow', 'tasks', 'run']), \
             patch('os.environ.get') as mock_env:
            
            # 模拟Airflow环境变量
            mock_env.side_effect = lambda key, default=None: {
                'USER': 'airflow',
                'SM_CURRENT_INSTANCE_TYPE': None,
                'AIRFLOW_CTX_DAG_ID': 'test_dag',
                'AIRFLOW_CTX_TASK_ID': 'test_task',
                'JPY_PARENT_PID': None
            }.get(key, default)
            
            context = self.agent.identify_execution_context()
            
            self.assertIsInstance(context, ExecutionContext)
            self.assertEqual(context.environment_type, EnvironmentType.AIRFLOW_TASK)
            self.assertEqual(context.airflow_dag_id, 'test_dag')
            self.assertEqual(context.airflow_task_id, 'test_task')
    
    @patch('boto3.client')
    def test_validate_job_id_selection_success(self, mock_boto_client):
        """测试Job ID验证成功场景"""
        # 模拟Glue客户端响应
        mock_glue_client = Mock()
        mock_boto_client.return_value = mock_glue_client
        
        # 模拟Job Run信息
        job_start_time = datetime.now()\n        mock_glue_client.get_job_run.return_value = {\n            'JobRun': {\n                'Id': 'jr_test123456789',\n                'JobName': 'test-job',\n                'StartedOn': job_start_time,\n                'Arguments': {\n                    '--environment': 'test',\n                    '--user': 'testuser'\n                },\n                'JobRunState': 'SUCCEEDED'\n            }\n        }\n        \n        # 创建测试上下文\n        context = ExecutionContext(\n            context_id='test_context_123',\n            environment_type=EnvironmentType.STANDALONE_SCRIPT,\n            timestamp=job_start_time,\n            process_id=12345,\n            command_line='test_script.py',\n            working_directory='/test',\n            user_id='testuser'\n        )\n        \n        # 执行验证\n        mapping = self.agent.validate_job_id_selection(\n            'test-job', 'jr_test123456789', context\n        )\n        \n        self.assertIsInstance(mapping, JobExecutionMapping)\n        self.assertEqual(mapping.validation_status, ValidationStatus.VALIDATED)\n        self.assertGreater(mapping.confidence_score, 0.7)\n        self.assertEqual(mapping.job_name, 'test-job')\n        self.assertEqual(mapping.job_run_id, 'jr_test123456789')\n    \n    @patch('boto3.client')\n    def test_validate_job_id_selection_time_mismatch(self, mock_boto_client):\n        \"\"\"测试Job ID验证时间不匹配场景\"\"\"\n        # 模拟Glue客户端响应\n        mock_glue_client = Mock()\n        mock_boto_client.return_value = mock_glue_client\n        \n        # 模拟时间不匹配的Job Run\n        job_start_time = datetime.now()\n        context_time = datetime.fromtimestamp(job_start_time.timestamp() - 3600)  # 1小时前\n        \n        mock_glue_client.get_job_run.return_value = {\n            'JobRun': {\n                'Id': 'jr_test123456789',\n                'JobName': 'test-job',\n                'StartedOn': job_start_time,\n                'Arguments': {},\n                'JobRunState': 'SUCCEEDED'\n            }\n        }\n        \n        # 创建测试上下文\n        context = ExecutionContext(\n            context_id='test_context_123',\n            environment_type=EnvironmentType.STANDALONE_SCRIPT,\n            timestamp=context_time,\n            process_id=12345,\n            command_line='test_script.py',\n            working_directory='/test',\n            user_id='testuser'\n        )\n        \n        # 执行验证\n        mapping = self.agent.validate_job_id_selection(\n            'test-job', 'jr_test123456789', context\n        )\n        \n        self.assertIsInstance(mapping, JobExecutionMapping)\n        self.assertEqual(mapping.validation_status, ValidationStatus.REJECTED)\n        self.assertLess(mapping.confidence_score, 0.7)\n        self.assertGreater(mapping.time_diff_seconds, 300)  # 超过5分钟容差\n    \n    def test_merge_lineage_data_success(self):\n        \"\"\"测试血缘数据合并成功场景\"\"\"\n        # 创建测试上下文\n        context = ExecutionContext(\n            context_id='test_context_123',\n            environment_type=EnvironmentType.STANDALONE_SCRIPT,\n            timestamp=datetime.now(),\n            process_id=12345,\n            command_line='test_script.py',\n            working_directory='/test',\n            user_id='testuser'\n        )\n        \n        # 创建模拟血缘数据\n        lineage_sources = {\n            'glue': {\n                'context_id': context.context_id,\n                'extraction_timestamp': datetime.now().isoformat(),\n                'events': [\n                    {\n                        'inputs': [{'name': 's3://test-bucket/input.csv'}],\n                        'outputs': [{'name': 's3://test-bucket/output.parquet'}],\n                        'job': {'name': 'test-job'}\n                    }\n                ],\n                'metadata': {\n                    'execution_context': {\n                        'context_id': context.context_id\n                    }\n                }\n            },\n            'redshift': {\n                'context_id': context.context_id,\n                'extraction_timestamp': datetime.now().isoformat(),\n                'queries': [\n                    {\n                        'input_tables': ['staging.test_table'],\n                        'output_tables': ['analytics.processed_table'],\n                        'sql': 'INSERT INTO analytics.processed_table SELECT * FROM staging.test_table'\n                    }\n                ]\n            }\n        }\n        \n        # 执行合并\n        result = self.agent.merge_lineage_data(lineage_sources, context)\n        \n        self.assertTrue(result['success'])\n        self.assertEqual(result['context_id'], context.context_id)\n        self.assertIn('sources_processed', result)\n        self.assertIn('merged_lineage', result)\n        \n        merged_lineage = result['merged_lineage']\n        self.assertIn('lineage_events', merged_lineage)\n        self.assertIn('data_entities', merged_lineage)\n        self.assertIn('lineage_graph', merged_lineage)\n    \n    def test_merge_lineage_data_validation_failure(self):\n        \"\"\"测试血缘数据合并验证失败场景\"\"\"\n        # 创建测试上下文\n        context = ExecutionContext(\n            context_id='test_context_123',\n            environment_type=EnvironmentType.STANDALONE_SCRIPT,\n            timestamp=datetime.now(),\n            process_id=12345,\n            command_line='test_script.py',\n            working_directory='/test',\n            user_id='testuser'\n        )\n        \n        # 创建不匹配的血缘数据（不同的context_id）\n        lineage_sources = {\n            'glue': {\n                'context_id': 'different_context_456',  # 不匹配的context_id\n                'extraction_timestamp': datetime.now().isoformat(),\n                'events': [],\n                'metadata': {\n                    'execution_context': {\n                        'context_id': 'different_context_456'\n                    }\n                }\n            }\n        }\n        \n        # 执行合并\n        result = self.agent.merge_lineage_data(lineage_sources, context)\n        \n        self.assertFalse(result['success'])\n        self.assertIn('error', result)\n        self.assertIn('validation_result', result)\n    \n    def test_context_id_generation(self):\n        \"\"\"测试上下文ID生成的唯一性\"\"\"\n        with patch('os.getcwd', return_value='/test'), \\\n             patch('os.getpid', return_value=12345), \\\n             patch('sys.argv', ['test.py']), \\\n             patch('os.environ.get', return_value='testuser'):\n            \n            # 生成多个上下文\n            context1 = self.agent.identify_execution_context()\n            context2 = self.agent.identify_execution_context()\n            \n            # 验证ID不同（因为时间戳不同）\n            self.assertNotEqual(context1.context_id, context2.context_id)\n            \n            # 验证ID格式\n            self.assertTrue(context1.context_id.startswith('standalone_script_'))\n            self.assertTrue(context2.context_id.startswith('standalone_script_'))\n    \n    def test_error_handling(self):\n        \"\"\"测试错误处理机制\"\"\"\n        # 测试无效配置的处理\n        with self.assertRaises(Exception):\n            ContextAwareAgent({})\n        \n        # 测试AWS服务异常的处理\n        with patch('boto3.client') as mock_boto:\n            mock_boto.side_effect = Exception(\"AWS service error\")\n            \n            context = ExecutionContext(\n                context_id='test_context_123',\n                environment_type=EnvironmentType.STANDALONE_SCRIPT,\n                timestamp=datetime.now(),\n                process_id=12345,\n                command_line='test_script.py',\n                working_directory='/test',\n                user_id='testuser'\n            )\n            \n            # 验证错误被正确处理\n            mapping = self.agent.validate_job_id_selection(\n                'test-job', 'jr_test123456789', context\n            )\n            \n            self.assertEqual(mapping.validation_status, ValidationStatus.FAILED)\n            self.assertEqual(mapping.confidence_score, 0.0)\n\n\nclass TestExecutionContextModel(unittest.TestCase):\n    \"\"\"ExecutionContext模型测试类\"\"\"\n    \n    def test_execution_context_creation(self):\n        \"\"\"测试执行上下文创建\"\"\"\n        context = ExecutionContext(\n            context_id='test_123',\n            environment_type=EnvironmentType.SAGEMAKER_NOTEBOOK,\n            timestamp=datetime.now(),\n            process_id=12345,\n            command_line='jupyter-notebook',\n            working_directory='/opt/ml/code',\n            user_id='sagemaker-user',\n            notebook_instance='ml.t3.medium',\n            sagemaker_role='SageMakerRole'\n        )\n        \n        self.assertEqual(context.context_id, 'test_123')\n        self.assertEqual(context.environment_type, EnvironmentType.SAGEMAKER_NOTEBOOK)\n        self.assertTrue(context.is_sagemaker_environment())\n        self.assertEqual(context.notebook_instance, 'ml.t3.medium')\n    \n    def test_unique_identifier_generation(self):\n        \"\"\"测试唯一标识符生成\"\"\"\n        timestamp = datetime.now()\n        context = ExecutionContext(\n            context_id='test_123',\n            environment_type=EnvironmentType.STANDALONE_SCRIPT,\n            timestamp=timestamp,\n            process_id=12345,\n            command_line='test.py',\n            working_directory='/test',\n            user_id='testuser'\n        )\n        \n        unique_id = context.get_unique_identifier()\n        expected_id = f\"standalone_script_12345_{timestamp.isoformat()}\"\n        self.assertEqual(unique_id, expected_id)\n\n\nif __name__ == '__main__':\n    # 运行测试\n    unittest.main(verbosity=2)