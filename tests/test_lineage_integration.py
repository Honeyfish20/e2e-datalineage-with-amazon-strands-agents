"""
血缘集成测试 - 端到端测试
"""

import unittest
import tempfile
import json
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from enhanced_lineage_agent.integrations.enhanced_glue_extractor import EnhancedGlueLineageExtractor
from enhanced_lineage_agent.integrations.enhanced_table_merger import EnhancedTableLineageMerger
from enhanced_lineage_agent.models.execution_context import ExecutionContext, EnvironmentType


class TestLineageIntegrationEndToEnd(unittest.TestCase):
    """血缘集成端到端测试"""
    
    def setUp(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试用的血缘数据
        self.sample_glue_lineage = {
            "metadata": {
                "job_name": "test-glue-job",
                "job_run_id": "jr_test123",
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_context": {
                    "context_id": "test_context_123",
                    "environment_type": "standalone_script",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            "events": [
                {
                    "eventType": "START",
                    "eventTime": datetime.now(timezone.utc).isoformat(),
                    "inputs": [
                        {
                            "namespace": "s3://test-bucket",
                            "name": "input-data/file1.csv"
                        }
                    ],
                    "outputs": [
                        {
                            "namespace": "s3://test-bucket",
                            "name": "processed-data/output1.parquet"
                        }
                    ],
                    "_metadata": {
                        "execution_context": {
                            "context_id": "test_context_123"
                        }
                    }
                }
            ]
        }
        
        self.sample_redshift_lineage = {
            "metadata": {
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_context": {
                    "context_id": "test_context_123",
                    "environment_type": "standalone_script",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            "events": [
                {
                    "eventType": "COMPLETE",
                    "eventTime": datetime.now(timezone.utc).isoformat(),
                    "inputs": [
                        {
                            "namespace": "s3://test-bucket",
                            "name": "processed-data/output1.parquet"
                        }
                    ],
                    "outputs": [
                        {
                            "namespace": "redshift://test-cluster",
                            "name": "public.final_table"
                        }
                    ],
                    "_metadata": {
                        "execution_context": {
                            "context_id": "test_context_123"
                        }
                    }
                }
            ]
        }
    
    def tearDown(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('enhanced_lineage_agent.integrations.enhanced_glue_extractor.get_config')
    @patch('boto3.Session')
    def test_enhanced_glue_extractor_context_awareness(self, mock_session, mock_get_config):
        """测试增强Glue提取器的上下文感知功能"""
        # 模拟配置
        mock_config = MagicMock()
        mock_config.aws_region = 'us-east-1'
        mock_get_config.return_value = mock_config
        
        # 模拟AWS会话
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        
        # 创建增强提取器
        extractor = EnhancedGlueLineageExtractor(
            session=mock_session_instance,
            lineage_output_path="s3://test-bucket/lineage/",
            enable_context_awareness=True
        )
        
        # 验证上下文感知功能已启用
        self.assertTrue(extractor.enable_context_awareness)
        self.assertIsNotNone(extractor.execution_context)
        self.assertIsNotNone(extractor.context_extractor)
        self.assertIsNotNone(extractor.job_validator)
        self.assertIsNotNone(extractor.log_stream_selector)
    
    @patch('enhanced_lineage_agent.integrations.enhanced_table_merger.get_config')
    def test_enhanced_table_merger_validation(self, mock_get_config):
        """测试增强表合并器的验证功能"""
        # 模拟配置
        mock_config = MagicMock()
        mock_config.aws_region = 'us-east-1'
        mock_get_config.return_value = mock_config
        
        # 创建增强合并器
        merger = EnhancedTableLineageMerger(
            output_dir=self.temp_dir,
            enable_validation=True
        )
        
        # 验证验证功能已启用
        self.assertTrue(merger.enable_validation)
        self.assertIsNotNone(merger.lineage_validator)
    
    def test_context_consistency_across_components(self):
        """测试组件间上下文一致性"""
        # 创建测试上下文
        test_context = ExecutionContext(
            context_id="consistency_test_123",
            environment_type=EnvironmentType.STANDALONE_SCRIPT,
            timestamp=datetime.now(timezone.utc),
            process_id=12345,
            command_line="python test_script.py",
            working_directory="/test/dir"
        )
        
        # 验证上下文序列化和反序列化
        context_dict = test_context.to_dict()
        rebuilt_context = ExecutionContext.from_dict(context_dict)
        
        self.assertEqual(test_context.context_id, rebuilt_context.context_id)
        self.assertEqual(test_context.environment_type, rebuilt_context.environment_type)
        self.assertEqual(test_context.process_id, rebuilt_context.process_id)
    
    def test_lineage_data_flow_integration(self):
        """测试血缘数据流集成"""
        # 创建临时血缘文件
        glue_file = os.path.join(self.temp_dir, 'glue_lineage.json')
        redshift_file = os.path.join(self.temp_dir, 'redshift_lineage.json')
        
        with open(glue_file, 'w') as f:
            json.dump(self.sample_glue_lineage, f)
        
        with open(redshift_file, 'w') as f:
            json.dump(self.sample_redshift_lineage, f)
        
        # 验证文件创建成功
        self.assertTrue(os.path.exists(glue_file))
        self.assertTrue(os.path.exists(redshift_file))
        
        # 验证数据完整性
        with open(glue_file, 'r') as f:
            loaded_glue = json.load(f)
        
        self.assertEqual(loaded_glue['metadata']['job_name'], 'test-glue-job')
        self.assertEqual(len(loaded_glue['events']), 1)
    
    @patch('enhanced_lineage_agent.integrations.enhanced_table_merger.get_config')
    def test_validation_workflow(self, mock_get_config):
        """测试验证工作流"""
        # 模拟配置
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        
        merger = EnhancedTableLineageMerger(
            output_dir=self.temp_dir,
            enable_validation=True
        )
        
        # 测试上下文提取
        glue_context = merger.extract_execution_context_from_lineage(self.sample_glue_lineage)
        redshift_context = merger.extract_execution_context_from_lineage(self.sample_redshift_lineage)
        
        # 验证上下文提取成功
        self.assertIsNotNone(glue_context)
        self.assertIsNotNone(redshift_context)
        self.assertEqual(glue_context.context_id, "test_context_123")
        self.assertEqual(redshift_context.context_id, "test_context_123")
    
    def test_error_handling_integration(self):
        """测试错误处理集成"""
        from enhanced_lineage_agent.utils.error_recovery import ErrorRecoveryManager, ErrorType
        
        recovery_manager = ErrorRecoveryManager()
        
        # 模拟上下文提取失败
        test_error = Exception("Context extraction failed")
        
        recovery_result = recovery_manager.handle_error(
            test_error,
            ErrorType.CONTEXT_EXTRACTION_FAILED,
            {'test_context': 'test_value'}
        )
        
        # 验证恢复策略
        self.assertIn('strategy', recovery_result)
        self.assertIn('success', recovery_result)
    
    def test_monitoring_integration(self):
        """测试监控集成"""
        from enhanced_lineage_agent.monitoring.simple_monitoring import SimpleMonitoring
        
        monitoring = SimpleMonitoring()
        
        # 记录测试指标
        monitoring.record_context_identification_success('standalone_script', True)
        monitoring.record_job_id_validation_confidence(0.85, 'test-job')
        monitoring.record_lineage_merge_status('success', 10, 5)
        
        # 验证指标缓存
        self.assertGreater(len(monitoring.metrics_cache), 0)
        
        # 验证指标内容
        context_metric = next(
            (m for m in monitoring.metrics_cache if m['MetricName'] == 'ContextIdentificationSuccess'),
            None
        )
        self.assertIsNotNone(context_metric)
        self.assertEqual(context_metric['Value'], 1.0)


class TestConcurrentExecution(unittest.TestCase):
    """并发执行测试"""
    
    def test_concurrent_context_extraction(self):
        """测试并发上下文提取"""
        import threading
        import time
        
        from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor
        
        results = []
        errors = []
        
        def extract_context():
            try:
                extractor = ExecutionContextExtractor()
                context = extractor.extract_context()
                results.append(context.context_id)
            except Exception as e:
                errors.append(str(e))
        
        # 创建多个线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=extract_context)
            threads.append(thread)
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=10)
        
        # 验证结果
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 5)
        
        # 验证所有上下文ID都是唯一的
        self.assertEqual(len(set(results)), 5)
    
    def test_job_id_conflict_handling(self):
        """测试Job ID冲突处理"""
        from enhanced_lineage_agent.tools.job_validator import JobIDValidator
        from enhanced_lineage_agent.models.execution_context import ExecutionContext, EnvironmentType
        
        # 创建两个不同的执行上下文
        context1 = ExecutionContext(
            context_id="context_1",
            environment_type=EnvironmentType.STANDALONE_SCRIPT,
            timestamp=datetime.now(timezone.utc),
            process_id=12345,
            command_line="python script1.py",
            working_directory="/test/dir1"
        )
        
        context2 = ExecutionContext(
            context_id="context_2",
            environment_type=EnvironmentType.SAGEMAKER_NOTEBOOK,
            timestamp=datetime.now(timezone.utc),
            process_id=54321,
            command_line="python script2.py",
            working_directory="/test/dir2"
        )
        
        # 验证上下文确实不同
        self.assertNotEqual(context1.context_id, context2.context_id)
        self.assertNotEqual(context1.environment_type, context2.environment_type)
        self.assertNotEqual(context1.process_id, context2.process_id)


class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    def test_context_extraction_performance(self):
        """测试上下文提取性能"""
        import time
        from enhanced_lineage_agent.tools.context_extractor import ExecutionContextExtractor
        
        extractor = ExecutionContextExtractor()
        
        # 测量多次提取的时间
        start_time = time.time()
        
        for _ in range(10):
            context = extractor.extract_context()
            self.assertIsNotNone(context.context_id)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / 10
        
        # 验证平均提取时间小于1秒
        self.assertLess(avg_time, 1.0, f"Average extraction time too slow: {avg_time:.2f}s")
    
    def test_large_lineage_data_processing(self):
        """测试大型血缘数据处理"""
        # 创建大型血缘数据集
        large_lineage = {
            "metadata": {
                "job_name": "large-test-job",
                "total_events": 1000
            },
            "events": []
        }
        
        # 生成1000个事件
        for i in range(1000):
            event = {
                "eventType": "COMPLETE",
                "eventTime": datetime.now(timezone.utc).isoformat(),
                "inputs": [{"namespace": f"s3://bucket", "name": f"input_{i}.csv"}],
                "outputs": [{"namespace": f"s3://bucket", "name": f"output_{i}.parquet"}]
            }
            large_lineage["events"].append(event)
        
        # 验证数据生成成功
        self.assertEqual(len(large_lineage["events"]), 1000)
        
        # 测量处理时间
        import time
        start_time = time.time()
        
        # 模拟处理过程
        processed_events = 0
        for event in large_lineage["events"]:
            if event["eventType"] == "COMPLETE":
                processed_events += 1
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 验证处理结果和性能
        self.assertEqual(processed_events, 1000)
        self.assertLess(processing_time, 5.0, f"Processing time too slow: {processing_time:.2f}s")


if __name__ == '__main__':
    # 运行所有测试
    unittest.main(verbosity=2)