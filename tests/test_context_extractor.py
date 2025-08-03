"""
执行上下文提取器测试
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor
from enhanced_lineage_agent.models.execution_context import EnvironmentType


class TestExecutionContextExtractor(unittest.TestCase):
    """执行上下文提取器测试类"""
    
    def setUp(self):
        """测试设置"""
        self.extractor = ExecutionContextExtractor()
    
    @patch('enhanced_lineage_agent.tools.context_extractor.psutil.Process')
    @patch('enhanced_lineage_agent.tools.context_extractor.os.getcwd')
    @patch('enhanced_lineage_agent.tools.context_extractor.sys.argv')
    def test_extract_context_basic(self, mock_argv, mock_getcwd, mock_process):
        """测试基本上下文提取"""
        # 设置模拟
        mock_argv.__getitem__ = lambda self, key: ['test_script.py', '--arg1', 'value1'][key]
        mock_argv.__len__ = lambda self: 3
        mock_getcwd.return_value = '/test/directory'
        
        mock_process_instance = MagicMock()
        mock_process_instance.parent.return_value = None
        mock_process.return_value = mock_process_instance
        
        # 执行测试
        context = self.extractor.extract_context()
        
        # 验证结果
        self.assertIsNotNone(context)
        self.assertIsNotNone(context.context_id)
        self.assertIsInstance(context.timestamp, datetime)
        self.assertEqual(context.working_directory, '/test/directory')
        self.assertIn('test_script.py', context.command_line)
    
    @patch.dict(os.environ, {
        'SM_CURRENT_INSTANCE_TYPE': 'ml.t3.medium',
        'SAGEMAKER_NOTEBOOK_INSTANCE_NAME': 'test-notebook'
    })
    def test_identify_sagemaker_environment(self):
        """测试SageMaker环境识别"""
        env_type = self.extractor._identify_environment_type()
        self.assertEqual(env_type, EnvironmentType.SAGEMAKER_NOTEBOOK)
    
    @patch.dict(os.environ, {
        'AIRFLOW_CTX_DAG_ID': 'test_dag',
        'AIRFLOW_CTX_TASK_ID': 'test_task'
    })
    def test_identify_airflow_environment(self):
        """测试Airflow环境识别"""
        env_type = self.extractor._identify_environment_type()
        self.assertEqual(env_type, EnvironmentType.AIRFLOW_TASK)
    
    @patch.dict(os.environ, {'JPY_PARENT_PID': '12345'})
    def test_identify_jupyter_environment(self):
        """测试Jupyter环境识别"""
        env_type = self.extractor._identify_environment_type()
        self.assertEqual(env_type, EnvironmentType.JUPYTER_NOTEBOOK)
    
    @patch('enhanced_lineage_agent.tools.context_extractor.sys.argv', ['extract-lineage-to-s3.py'])
    def test_identify_standalone_script(self):
        """测试独立脚本识别"""
        env_type = self.extractor._identify_environment_type()
        self.assertEqual(env_type, EnvironmentType.STANDALONE_SCRIPT)
    
    def test_generate_context_id_uniqueness(self):
        """测试上下文ID唯一性"""
        context_ids = set()
        
        for _ in range(10):
            context_id = self.extractor._generate_context_id(
                EnvironmentType.STANDALONE_SCRIPT,
                12345,
                datetime.now()
            )
            context_ids.add(context_id)
        
        # 所有ID应该是唯一的
        self.assertEqual(len(context_ids), 10)
    
    @patch('enhanced_lineage_agent.tools.context_extractor.ExecutionContextExtractor.extract_context')
    def test_extract_execution_context_tool(self, mock_extract):
        """测试Strands工具函数"""
        from enhanced_lineage_agent.tools.context_extractor import extract_execution_context
        
        # 设置模拟返回值
        mock_context = MagicMock()
        mock_context.to_dict.return_value = {'context_id': 'test_id'}
        mock_extract.return_value = mock_context
        
        # 执行测试
        result = extract_execution_context()
        
        # 验证结果
        self.assertEqual(result, {'context_id': 'test_id'})
        mock_extract.assert_called_once()
    
    def test_fallback_context_creation(self):
        """测试后备上下文创建"""
        fallback_context = self.extractor._create_fallback_context()
        
        self.assertIsNotNone(fallback_context)
        self.assertEqual(fallback_context.environment_type, EnvironmentType.UNKNOWN)
        self.assertTrue(fallback_context.metadata.get('fallback', False))
        self.assertIn('fallback', fallback_context.context_id)


class TestContextExtractionIntegration(unittest.TestCase):
    """上下文提取集成测试"""
    
    def setUp(self):
        """测试设置"""
        self.extractor = ExecutionContextExtractor()
    
    def test_end_to_end_context_extraction(self):
        """端到端上下文提取测试"""
        # 这个测试在真实环境中运行
        context = self.extractor.extract_context()
        
        # 验证基本属性
        self.assertIsNotNone(context.context_id)
        self.assertIsInstance(context.timestamp, datetime)
        self.assertIsNotNone(context.process_id)
        self.assertIsNotNone(context.working_directory)
        self.assertIsInstance(context.environment_type, EnvironmentType)
    
    def test_context_serialization(self):
        """测试上下文序列化"""
        context = self.extractor.extract_context()
        
        # 转换为字典
        context_dict = context.to_dict()
        self.assertIsInstance(context_dict, dict)
        self.assertIn('context_id', context_dict)
        self.assertIn('environment_type', context_dict)
        
        # 从字典重建
        from enhanced_lineage_agent.models.execution_context import ExecutionContext
        rebuilt_context = ExecutionContext.from_dict(context_dict)
        
        self.assertEqual(context.context_id, rebuilt_context.context_id)
        self.assertEqual(context.environment_type, rebuilt_context.environment_type)


if __name__ == '__main__':
    unittest.main()