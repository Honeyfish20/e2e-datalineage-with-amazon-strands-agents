"""
简单监控实现

为MVP版本提供基础的监控和指标收集功能。
"""

import boto3
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError


class SimpleMonitoring:
    """简化的监控实现"""
    
    def __init__(self, namespace: str = "EnhancedLineage/MVP"):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
        self.logger = logging.getLogger(__name__)
        
        # 指标缓冲区
        self._metric_buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100
    
    def emit_context_identification_metric(self, success: bool, environment_type: str, 
                                         processing_time_ms: float = 0):
        """发送上下文识别指标"""
        metrics = [
            {
                'MetricName': 'ContextIdentificationSuccess',
                'Value': 1 if success else 0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'EnvironmentType', 'Value': environment_type},
                    {'Name': 'Service', 'Value': 'ContextExtractor'}
                ]
            }
        ]
        
        if processing_time_ms > 0:
            metrics.append({
                'MetricName': 'ContextIdentificationLatency',
                'Value': processing_time_ms,
                'Unit': 'Milliseconds',
                'Dimensions': [
                    {'Name': 'EnvironmentType', 'Value': environment_type}
                ]
            })
        
        self._buffer_metrics(metrics)
    
    def emit_job_id_validation_metric(self, confidence_score: float, validation_result: str,
                                    job_name: str):
        """发送Job ID验证指标"""
        metrics = [
            {
                'MetricName': 'JobIDValidationConfidence',
                'Value': confidence_score * 100,  # 转换为百分比
                'Unit': 'Percent',
                'Dimensions': [
                    {'Name': 'ValidationResult', 'Value': validation_result},
                    {'Name': 'JobName', 'Value': job_name}
                ]
            },
            {
                'MetricName': 'JobIDValidationSuccess',
                'Value': 1 if validation_result == 'validated' else 0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'JobName', 'Value': job_name}
                ]
            }
        ]
        
        self._buffer_metrics(metrics)
    
    def emit_log_stream_selection_metric(self, selection_success: bool, confidence_score: float,
                                       conflict_detected: bool, candidates_count: int):
        """发送日志流选择指标"""
        metrics = [
            {
                'MetricName': 'LogStreamSelectionSuccess',
                'Value': 1 if selection_success else 0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'LogStreamSelector'}
                ]
            },
            {
                'MetricName': 'LogStreamSelectionConfidence',
                'Value': confidence_score * 100,
                'Unit': 'Percent',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'LogStreamSelector'}
                ]
            },
            {
                'MetricName': 'LogStreamConflictDetected',
                'Value': 1 if conflict_detected else 0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'LogStreamSelector'}
                ]
            },
            {
                'MetricName': 'LogStreamCandidatesCount',
                'Value': candidates_count,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'LogStreamSelector'}
                ]
            }
        ]
        
        self._buffer_metrics(metrics)
    
    def emit_lineage_collection_metric(self, sources_collected: List[str], 
                                     collection_success: bool, processing_time_ms: float):
        """发送血缘收集指标"""
        metrics = [
            {
                'MetricName': 'LineageCollectionSuccess',
                'Value': 1 if collection_success else 0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'LineageCollector'}
                ]
            },
            {
                'MetricName': 'LineageSourcesCollected',
                'Value': len(sources_collected),
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'LineageCollector'}
                ]
            },
            {
                'MetricName': 'LineageCollectionLatency',
                'Value': processing_time_ms,
                'Unit': 'Milliseconds',
                'Dimensions': [
                    {'Name': 'Service', 'Value': 'LineageCollector'}
                ]
            }
        ]
        
        # 为每个收集的源发送单独的指标
        for source in sources_collected:
            metrics.append({
                'MetricName': 'LineageSourceCollectionSuccess',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'SourceType', 'Value': source}
                ]
            })
        
        self._buffer_metrics(metrics)
    
    def emit_agent_performance_metric(self, operation: str, success: bool, 
                                    duration_ms: float, error_type: Optional[str] = None):
        """发送代理性能指标"""
        metrics = [
            {
                'MetricName': 'AgentOperationSuccess',
                'Value': 1 if success else 0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Operation', 'Value': operation},
                    {'Name': 'Service', 'Value': 'ContextAwareAgent'}
                ]
            },
            {
                'MetricName': 'AgentOperationDuration',
                'Value': duration_ms,
                'Unit': 'Milliseconds',
                'Dimensions': [
                    {'Name': 'Operation', 'Value': operation}
                ]
            }
        ]
        
        if not success and error_type:
            metrics.append({
                'MetricName': 'AgentOperationError',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Operation', 'Value': operation},
                    {'Name': 'ErrorType', 'Value': error_type}
                ]
            })
        
        self._buffer_metrics(metrics)
    
    def emit_system_health_metric(self, component: str, health_status: str, 
                                response_time_ms: float = 0):
        """发送系统健康指标"""
        metrics = [
            {
                'MetricName': 'ComponentHealth',
                'Value': 1 if health_status == 'healthy' else 0,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Component', 'Value': component},
                    {'Name': 'HealthStatus', 'Value': health_status}
                ]
            }
        ]
        
        if response_time_ms > 0:
            metrics.append({
                'MetricName': 'ComponentResponseTime',
                'Value': response_time_ms,
                'Unit': 'Milliseconds',
                'Dimensions': [
                    {'Name': 'Component', 'Value': component}
                ]
            })
        
        self._buffer_metrics(metrics)
    
    def _buffer_metrics(self, metrics: List[Dict[str, Any]]):
        """缓冲指标数据"""
        timestamp = datetime.utcnow()
        
        for metric in metrics:
            metric['Timestamp'] = timestamp
            self._metric_buffer.append(metric)
        
        # 如果缓冲区满了，刷新到CloudWatch
        if len(self._metric_buffer) >= self._buffer_size:
            self.flush_metrics()
    
    def flush_metrics(self):
        """刷新指标到CloudWatch"""
        if not self._metric_buffer:
            return
        
        try:
            # CloudWatch每次最多接受20个指标
            batch_size = 20
            for i in range(0, len(self._metric_buffer), batch_size):
                batch = self._metric_buffer[i:i + batch_size]
                
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            self.logger.debug(f"Flushed {len(self._metric_buffer)} metrics to CloudWatch")
            self._metric_buffer.clear()
            
        except ClientError as e:
            self.logger.error(f"Failed to flush metrics to CloudWatch: {e}")
            # 保留指标数据，下次再试
        except Exception as e:
            self.logger.error(f"Unexpected error flushing metrics: {e}")
            self._metric_buffer.clear()  # 清空缓冲区避免内存泄漏
    
    def create_dashboard(self, dashboard_name: str) -> bool:
        """创建CloudWatch仪表板"""
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "ContextIdentificationSuccess", "Service", "ContextExtractor"],
                            [self.namespace, "JobIDValidationSuccess"],
                            [self.namespace, "LogStreamSelectionSuccess", "Service", "LogStreamSelector"]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": "us-east-1",
                        "title": "Success Metrics"
                    }
                },
                {
                    "type": "metric",
                    "x": 12, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "ContextIdentificationLatency"],
                            [self.namespace, "AgentOperationDuration"],
                            [self.namespace, "LineageCollectionLatency"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-1",
                        "title": "Performance Metrics"
                    }
                },
                {
                    "type": "metric",
                    "x": 0, "y": 6, "width": 24, "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "JobIDValidationConfidence"],
                            [self.namespace, "LogStreamSelectionConfidence"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-1",
                        "title": "Confidence Scores"
                    }
                }
            ]
        }
        
        try:
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            self.logger.info(f"Dashboard created successfully: {dashboard_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create dashboard {dashboard_name}: {e}")
            return False
    
    def create_alarms(self, sns_topic_arn: Optional[str] = None) -> List[str]:
        """创建基础告警"""
        created_alarms = []
        
        alarms_config = [
            {
                'AlarmName': 'EnhancedLineage-HighErrorRate',
                'AlarmDescription': 'High error rate in lineage processing',
                'MetricName': 'ContextIdentificationSuccess',
                'Statistic': 'Average',
                'Period': 300,
                'EvaluationPeriods': 2,
                'Threshold': 0.8,
                'ComparisonOperator': 'LessThanThreshold'
            },
            {
                'AlarmName': 'EnhancedLineage-LowConfidence',
                'AlarmDescription': 'Low confidence in job ID validation',
                'MetricName': 'JobIDValidationConfidence',
                'Statistic': 'Average',
                'Period': 300,
                'EvaluationPeriods': 3,
                'Threshold': 60,  # 60%
                'ComparisonOperator': 'LessThanThreshold'
            },
            {
                'AlarmName': 'EnhancedLineage-HighLatency',
                'AlarmDescription': 'High latency in agent operations',
                'MetricName': 'AgentOperationDuration',
                'Statistic': 'Average',
                'Period': 300,
                'EvaluationPeriods': 2,
                'Threshold': 30000,  # 30秒
                'ComparisonOperator': 'GreaterThanThreshold'
            }
        ]
        
        for alarm_config in alarms_config:
            try:
                alarm_params = {
                    'AlarmName': alarm_config['AlarmName'],
                    'AlarmDescription': alarm_config['AlarmDescription'],
                    'ActionsEnabled': True,
                    'MetricName': alarm_config['MetricName'],
                    'Namespace': self.namespace,
                    'Statistic': alarm_config['Statistic'],
                    'Period': alarm_config['Period'],
                    'EvaluationPeriods': alarm_config['EvaluationPeriods'],
                    'Threshold': alarm_config['Threshold'],
                    'ComparisonOperator': alarm_config['ComparisonOperator']
                }
                
                if sns_topic_arn:
                    alarm_params['AlarmActions'] = [sns_topic_arn]
                    alarm_params['OKActions'] = [sns_topic_arn]
                
                self.cloudwatch.put_metric_alarm(**alarm_params)
                created_alarms.append(alarm_config['AlarmName'])
                
            except Exception as e:
                self.logger.error(f"Failed to create alarm {alarm_config['AlarmName']}: {e}")
        
        self.logger.info(f"Created {len(created_alarms)} alarms")
        return created_alarms
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取指标摘要"""
        try:
            end_time = datetime.utcnow()
            start_time = datetime.utcnow().replace(hour=end_time.hour - hours)
            
            # 获取关键指标
            metrics_to_query = [
                'ContextIdentificationSuccess',
                'JobIDValidationSuccess',
                'LogStreamSelectionSuccess',
                'LineageCollectionSuccess'
            ]
            
            summary = {}
            
            for metric_name in metrics_to_query:
                try:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace=self.namespace,
                        MetricName=metric_name,
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,  # 1小时
                        Statistics=['Sum', 'Average']
                    )
                    
                    datapoints = response.get('Datapoints', [])
                    if datapoints:
                        summary[metric_name] = {
                            'total': sum(dp['Sum'] for dp in datapoints),
                            'average': sum(dp['Average'] for dp in datapoints) / len(datapoints),
                            'datapoints_count': len(datapoints)
                        }
                    else:
                        summary[metric_name] = {'total': 0, 'average': 0, 'datapoints_count': 0}
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get metrics for {metric_name}: {e}")
                    summary[metric_name] = {'error': str(e)}
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics summary: {e}")
            return {'error': str(e)}
    
    def __del__(self):
        """析构函数，确保指标被刷新"""
        try:
            self.flush_metrics()
        except:
            pass  # 忽略析构时的错误