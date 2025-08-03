"""
Job ID验证器测试
"""

import unittest
import boto3
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from moto import mock_glue, mock_dynamodb

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tools.job_validator import JobIDValidator
from models.execution_context import ExecutionContext, EnvironmentType
from models.job_mapping import ValidationStatus


class TestJobIDValidator(unittest.TestCase):
    """Job ID验证器测试类"""
    
    def setUp(self):
        """测试设置"""
        # 创建测试用的执行上下文
        self.test_context = ExecutionContext(
            context_id="test_context_123",
            environment_type=EnvironmentType.STANDALONE_SCRIPT,
            timestamp=datetime.now(timezone.utc),
            process_id=12345,
            command_line="python test_script.py",
            working_directory="/test/dir"
        )
        
        # 模拟配置
        self.mock_config = MagicMock()
        self.mock_config.aws_region = 'us-east-1'
        self.mock_config.dynamodb.region = 'us-east-1'
        self.mock_config.dynamodb.job_mapping_table = 'test-job-mappings'
        self.mock_config.validation.min_confidence_score = 0.7
        self.mock_config.validation.time_tolerance_seconds = 300
        self.mock_config.validation.enable_parameter_validation = True
        self.mock_config.validation.enable_environment_validation = True
    
    @mock_glue
    @mock_dynamodb
    @patch('enhanced_lineage_agent.tools.job_validator.get_config')
    def test_validate_job_run_id_success(self, mock_get_config):
        """测试Job Run ID验证成功"""
        mock_get_config.return_value = self.mock_config
        
        # 创建模拟的Glue作业运行
        glue_client = boto3.client('glue', region_name='us-east-1')
        
        # 创建作业
        glue_client.create_job(
            Name='test-job',
            Role='arn:aws:iam::123456789012:role/test-role',
            Command={'Name': 'glueetl', 'ScriptLocation': 's3://test/script.py'}
        )
        
        # 创建DynamoDB表
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-job-mappings',
            KeySchema=[{'AttributeName': 'context_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'context_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # 创建验证器
        validator = JobIDValidator()
        
        # 模拟作业运行信息
        job_run_info = {
            'StartedOn': self.test_context.timestamp,
            'Arguments': {'--job-language': 'python'}
        }
        
        with patch.object(validator, '_get_job_run_info', return_value=job_run_info):
            result = validator.validate_job_run_id(
                'test-job', 
                'jr_test123', 
                self.test_context
            )
        
        # 验证结果
        self.assertTrue(result['is_valid'])
        self.assertGreater(result['confidence_score'], 0.5)
        self.assertEqual(result['recommendation'], 'accept')
    
    @mock_glue
    @patch('enhanced_lineage_agent.tools.job_validator.get_config')
    def test_validate_job_run_id_not_found(self, mock_get_config):
        """测试Job Run ID不存在"""
        mock_get_config.return_value = self.mock_config
        
        validator = JobIDValidator()
        
        with patch.object(validator, '_get_job_run_info', return_value=None):
            result = validator.validate_job_run_id(
                'test-job', 
                'jr_nonexistent', 
                self.test_context
            )
        
        # 验证结果
        self.assertFalse(result['is_valid'])
        self.assertEqual(result['confidence_score'], 0.0)
        self.assertEqual(result['recommendation'], 'reject')
        self.assertEqual(result['reason'], 'Job run not found')
    
    @patch('enhanced_lineage_agent.tools.job_validator.get_config')
    def test_time_validation_within_tolerance(self, mock_get_config):
        """测试时间验证在容忍范围内"""
        mock_get_config.return_value = self.mock_config
        
        validator = JobIDValidator()
        
        # 创建时间差在容忍范围内的作业运行信息
        job_start_time = self.test_context.timestamp + timedelta(seconds=100)  # 100秒差异
        job_run_info = {
            'StartedOn': job_start_time,
            'Arguments': {}
        }
        
        time_validation = validator._validate_time_match(job_run_info, self.test_context)
        
        self.assertTrue(time_validation['match'])
        self.assertGreater(time_validation['score'], 0.5)
        self.assertEqual(time_validation['time_diff_seconds'], 100)
    
    @patch('enhanced_lineage_agent.tools.job_validator.get_config')
    def test_time_validation_outside_tolerance(self, mock_get_config):
        """测试时间验证超出容忍范围"""
        mock_get_config.return_value = self.mock_config
        
        validator = JobIDValidator()
        
        # 创建时间差超出容忍范围的作业运行信息
        job_start_time = self.test_context.timestamp + timedelta(seconds=600)  # 600秒差异
        job_run_info = {
            'StartedOn': job_start_time,
            'Arguments': {}
        }
        
        time_validation = validator._validate_time_match(job_run_info, self.test_context)
        
        self.assertFalse(time_validation['match'])
        self.assertLess(time_validation['score'], 0.5)
        self.assertEqual(time_validation['time_diff_seconds'], 600)
    
    @patch('enhanced_lineage_agent.tools.job_validator.get_config')
    def test_sagemaker_parameter_validation(self, mock_get_config):
        """测试SageMaker参数验证"""
        mock_get_config.return_value = self.mock_config
        
        validator = JobIDValidator()
        
        # 创建SageMaker上下文
        sagemaker_context = ExecutionContext(
            context_id="sagemaker_context_123",
            environment_type=EnvironmentType.SAGEMAKER_NOTEBOOK,
            timestamp=datetime.now(timezone.utc),
            process_id=12345,
            command_line="python test_script.py",
            working_directory="/opt/ml/code",
            sagemaker_instance_type="ml.t3.medium"
        )
        
        # 包含SageMaker相关参数的作业参数
        job_arguments = {
            '--sagemaker-instance-type': 'ml.t3.medium',
            '--notebook-name': 'test-notebook'
        }
        
        param_validation = validator._validate_sagemaker_parameters(job_arguments, sagemaker_context)
        
        self.assertTrue(param_validation['match'])
        self.assertGreater(param_validation['score'], 0.5)
        self.assertIn('Instance type match', str(param_validation['matches']))
    
    @mock_dynamodb
    @patch('enhanced_lineage_agent.tools.job_validator.get_config')
    def test_create_job_mapping(self, mock_get_config):
        """测试创建Job执行映射"""
        mock_get_config.return_value = self.mock_config
        
        # 创建DynamoDB表
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-job-mappings',
            KeySchema=[{'AttributeName': 'context_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'context_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        validator = JobIDValidator()
        
        # 创建验证结果
        validation_result = {
            'is_valid': True,
            'confidence_score': 0.85,
            'job_start_time': datetime.now(timezone.utc).isoformat(),
            'validation_method': 'multi_dimensional',
            'time_validation': {'match': True, 'time_diff_seconds': 50},
            'parameter_validation': {'match': True},
            'environment_validation': {'match': True}
        }
        
        # 创建映射
        mapping = validator.create_job_mapping(
            self.test_context,
            'test-job',
            'jr_test123',
            validation_result
        )
        
        # 验证映射
        self.assertEqual(mapping.context_id, self.test_context.context_id)
        self.assertEqual(mapping.job_name, 'test-job')
        self.assertEqual(mapping.job_run_id, 'jr_test123')
        self.assertEqual(mapping.validation_status, ValidationStatus.VALIDATED)
        self.assertEqual(mapping.confidence_score, 0.85)
    
    @patch('enhanced_lineage_agent.tools.job_validator.get_config')
    def test_confidence_score_calculation(self, mock_get_config):
        """测试置信度分数计算"""
        mock_get_config.return_value = self.mock_config
        
        validator = JobIDValidator()
        
        # 创建验证结果
        time_validation = {'score': 0.9}
        param_validation = {'score': 0.7}
        env_validation = {'score': 0.8}
        
        confidence_score = validator._calculate_confidence_score(
            time_validation, param_validation, env_validation
        )
        
        # 验证加权平均计算
        expected_score = 0.9 * 0.6 + 0.7 * 0.3 + 0.8 * 0.1  # 0.54 + 0.21 + 0.08 = 0.83
        self.assertAlmostEqual(confidence_score, expected_score, places=2)


class TestJobValidatorIntegration(unittest.TestCase):
    """Job验证器集成测试"""
    
    @patch('enhanced_lineage_agent.tools.job_validator.get_config')
    def test_strands_tool_integration(self, mock_get_config):
        """测试Strands工具集成"""
        from tools.job_validator import validate_job_run_id
        
        # 模拟配置
        mock_config = MagicMock()
        mock_config.aws_region = 'us-east-1'
        mock_config.dynamodb.region = 'us-east-1'
        mock_config.dynamodb.job_mapping_table = 'test-job-mappings'
        mock_config.validation.min_confidence_score = 0.7
        mock_config.validation.time_tolerance_seconds = 300
        mock_get_config.return_value = mock_config
        
        # 创建测试上下文
        context_dict = {
            'context_id': 'test_context',
            'environment_type': 'standalone_script',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'process_id': 12345,
            'command_line': 'python test.py',
            'working_directory': '/test'
        }
        
        # 模拟验证器
        with patch('enhanced_lineage_agent.tools.job_validator.JobIDValidator') as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate_job_run_id.return_value = {
                'is_valid': True,
                'confidence_score': 0.85,
                'recommendation': 'accept'
            }
            mock_validator_class.return_value = mock_validator
            
            # 执行工具
            result = validate_job_run_id('test-job', 'jr_test123', context_dict)
            
            # 验证结果
            self.assertTrue(result['is_valid'])
            self.assertEqual(result['confidence_score'], 0.85)
            mock_validator.validate_job_run_id.assert_called_once()


if __name__ == '__main__':
    unittest.main()