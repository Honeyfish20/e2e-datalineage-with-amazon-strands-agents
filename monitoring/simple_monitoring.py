"""
简单监控和可观测性模块
"""

import boto3
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import json

from ..config import get_config
from ..utils.logging_config import get_contextual_logger


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SimpleMonitoring:
    """简单监控类"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_contextual_logger('monitoring')
        
        # 初始化AWS客户端
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.config.aws_region)
        self.sns = boto3.client('sns', region_name=self.config.aws_region)
        
        # 指标缓存
        self.metrics_cache: List[Dict[str, Any]] = []
        self.namespace = self.config.monitoring.get('namespace', 'EnhancedLineageAgent')
        
        # 告警配置
        self.alert_topic_arn = self.config.monitoring.get('alert_topic_arn')
        
    def record_metric(
        self,
        metric_name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        dimensions: Optional[Dict[str, str]] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        记录指标
        
        Args:
            metric_name: 指标名称
            value: 指标值
            metric_type: 指标类型
            dimensions: 维度信息
            timestamp: 时间戳
        """
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Timestamp': timestamp,
                'Dimensions': []
            }
            
            # 添加维度
            if dimensions:
                for key, value_str in dimensions.items():
                    metric_data['Dimensions'].append({
                        'Name': key,
                        'Value': str(value_str)
                    })
            
            # 添加到缓存
            self.metrics_cache.append(metric_data)
            
            # 如果缓存达到阈值，发送到CloudWatch
            if len(self.metrics_cache) >= self.config.monitoring.get('batch_size', 20):
                self.flush_metrics()
                
            self.logger.debug(f"Recorded metric: {metric_name} = {value}")
            
        except Exception as e:
            self.logger.error(f"Failed to record metric {metric_name}: {str(e)}")
    
    def flush_metrics(self):
        """将缓存的指标发送到CloudWatch"""
        if not self.metrics_cache:
            return
        
        try:
            # 分批发送（CloudWatch限制每次最多20个指标）
            batch_size = 20
            for i in range(0, len(self.metrics_cache), batch_size):
                batch = self.metrics_cache[i:i + batch_size]
                
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            self.logger.info(f"Flushed {len(self.metrics_cache)} metrics to CloudWatch")
            self.metrics_cache.clear()
            
        except Exception as e:
            self.logger.error(f"Failed to flush metrics to CloudWatch: {str(e)}")
    
    def record_context_identification_success(self, environment_type: str, success: bool):
        """记录上下文识别成功率"""
        self.record_metric(
            'ContextIdentificationSuccess',
            1.0 if success else 0.0,
            MetricType.GAUGE,
            dimensions={
                'EnvironmentType': environment_type,
                'Status': 'Success' if success else 'Failed'
            }
        )
    
    def record_job_id_validation_confidence(self, confidence_score: float, job_name: str):
        """记录Job ID验证置信度"""
        self.record_metric(
            'JobIdValidationConfidence',
            confidence_score,
            MetricType.GAUGE,
            dimensions={
                'JobName': job_name,
                'ConfidenceLevel': self._get_confidence_level(confidence_score)
            }
        )
    
    def record_lineage_merge_status(self, status: str, glue_events: int, redshift_events: int):
        """记录血缘合并状态"""
        self.record_metric(
            'LineageMergeStatus',
            1.0,
            MetricType.COUNTER,
            dimensions={
                'Status': status,
                'GlueEventsRange': self._get_events_range(glue_events),
                'RedshiftEventsRange': self._get_events_range(redshift_events)
            }
        )
        
        # 记录事件数量
        self.record_metric('GlueEventsCount', float(glue_events), MetricType.GAUGE)
        self.record_metric('RedshiftEventsCount', float(redshift_events), MetricType.GAUGE)
    
    def record_log_stream_selection_performance(
        self,
        selection_time_ms: float,
        streams_evaluated: int,
        selection_method: str
    ):
        """记录日志流选择性能"""
        self.record_metric(
            'LogStreamSelectionTime',
            selection_time_ms,
            MetricType.TIMER,
            dimensions={
                'SelectionMethod': selection_method,
                'StreamsEvaluated': str(streams_evaluated)
            }
        )
    
    def record_error_occurrence(self, error_type: str, component: str):
        """记录错误发生"""
        self.record_metric(
            'ErrorOccurrence',
            1.0,
            MetricType.COUNTER,
            dimensions={
                'ErrorType': error_type,
                'Component': component
            }
        )
    
    def record_processing_duration(self, operation: str, duration_seconds: float):
        """记录处理持续时间"""
        self.record_metric(
            'ProcessingDuration',
            duration_seconds,
            MetricType.TIMER,
            dimensions={
                'Operation': operation,
                'DurationRange': self._get_duration_range(duration_seconds)
            }
        )
    
    def send_alert(
        self,
        message: str,
        level: AlertLevel = AlertLevel.WARNING,
        details: Optional[Dict[str, Any]] = None
    ):
        """发送告警"""
        if not self.alert_topic_arn:
            self.logger.warning("Alert topic ARN not configured, skipping alert")
            return
        
        try:
            alert_payload = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'level': level.value,
                'message': message,
                'source': 'EnhancedLineageAgent',
                'details': details or {}
            }
            
            subject = f"[{level.value.upper()}] Enhanced Lineage Agent Alert"
            
            self.sns.publish(
                TopicArn=self.alert_topic_arn,
                Subject=subject,
                Message=json.dumps(alert_payload, indent=2)
            )
            
            self.logger.info(f"Alert sent: {level.value} - {message}")
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {str(e)}")
    
    def create_dashboard(self) -> str:
        """创建CloudWatch仪表板"""
        try:
            dashboard_body = {
                "widgets": [
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 0,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "ContextIdentificationSuccess", "Status", "Success"],
                                [".", ".", ".", "Failed"]
                            ],
                            "period": 300,
                            "stat": "Sum",
                            "region": self.config.aws_region,
                            "title": "Context Identification Success Rate"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 12,
                        "y": 0,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "JobIdValidationConfidence"]
                            ],
                            "period": 300,
                            "stat": "Average",
                            "region": self.config.aws_region,
                            "title": "Job ID Validation Confidence"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 6,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "LineageMergeStatus", "Status", "success"],
                                [".", ".", ".", "warning"],
                                [".", ".", ".", "blocked"]
                            ],
                            "period": 300,
                            "stat": "Sum",
                            "region": self.config.aws_region,
                            "title": "Lineage Merge Status"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 12,
                        "y": 6,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                [self.namespace, "ErrorOccurrence"]
                            ],
                            "period": 300,
                            "stat": "Sum",
                            "region": self.config.aws_region,
                            "title": "Error Occurrences"
                        }
                    }
                ]
            }
            
            dashboard_name = "EnhancedLineageAgent"
            
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            dashboard_url = f"https://{self.config.aws_region}.console.aws.amazon.com/cloudwatch/home?region={self.config.aws_region}#dashboards:name={dashboard_name}"
            
            self.logger.info(f"Dashboard created: {dashboard_url}")
            return dashboard_url
            
        except Exception as e:
            self.logger.error(f"Failed to create dashboard: {str(e)}")
            return ""
    
    def setup_alarms(self):
        """设置CloudWatch告警"""
        alarms = [
            {
                'AlarmName': 'EnhancedLineageAgent-HighErrorRate',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 2,
                'MetricName': 'ErrorOccurrence',
                'Namespace': self.namespace,
                'Period': 300,
                'Statistic': 'Sum',
                'Threshold': 10.0,
                'ActionsEnabled': True,
                'AlarmActions': [self.alert_topic_arn] if self.alert_topic_arn else [],
                'AlarmDescription': 'High error rate detected in Enhanced Lineage Agent',
                'Unit': 'Count'
            },
            {
                'AlarmName': 'EnhancedLineageAgent-LowContextIdentificationSuccess',
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 3,
                'MetricName': 'ContextIdentificationSuccess',
                'Namespace': self.namespace,
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 0.8,
                'ActionsEnabled': True,
                'AlarmActions': [self.alert_topic_arn] if self.alert_topic_arn else [],
                'AlarmDescription': 'Low context identification success rate',
                'Unit': 'None'
            },
            {
                'AlarmName': 'EnhancedLineageAgent-LowJobValidationConfidence',
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 2,
                'MetricName': 'JobIdValidationConfidence',
                'Namespace': self.namespace,
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 0.5,
                'ActionsEnabled': True,
                'AlarmActions': [self.alert_topic_arn] if self.alert_topic_arn else [],
                'AlarmDescription': 'Low job ID validation confidence',
                'Unit': 'None'
            }
        ]
        
        for alarm in alarms:
            try:
                self.cloudwatch.put_metric_alarm(**alarm)
                self.logger.info(f"Created alarm: {alarm['AlarmName']}")
            except Exception as e:
                self.logger.error(f"Failed to create alarm {alarm['AlarmName']}: {str(e)}")
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取指标摘要"""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time.replace(hour=end_time.hour - hours)
            
            # 获取关键指标
            metrics_to_query = [
                'ContextIdentificationSuccess',
                'JobIdValidationConfidence',
                'LineageMergeStatus',
                'ErrorOccurrence'
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
                        Statistics=['Sum', 'Average', 'Maximum']
                    )
                    
                    if response['Datapoints']:
                        summary[metric_name] = {
                            'datapoints_count': len(response['Datapoints']),
                            'latest_value': response['Datapoints'][-1] if response['Datapoints'] else None,
                            'average': sum(dp['Average'] for dp in response['Datapoints']) / len(response['Datapoints']),
                            'total': sum(dp['Sum'] for dp in response['Datapoints'])
                        }
                    else:
                        summary[metric_name] = {'no_data': True}
                        
                except Exception as e:
                    self.logger.warning(f"Failed to query metric {metric_name}: {str(e)}")
                    summary[metric_name] = {'error': str(e)}
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics summary: {str(e)}")
            return {'error': str(e)}
    
    def _get_confidence_level(self, confidence_score: float) -> str:
        """获取置信度级别"""
        if confidence_score >= 0.8:
            return 'High'
        elif confidence_score >= 0.5:
            return 'Medium'
        else:
            return 'Low'
    
    def _get_events_range(self, events_count: int) -> str:
        """获取事件数量范围"""
        if events_count == 0:
            return 'Zero'
        elif events_count <= 10:
            return 'Low'
        elif events_count <= 100:
            return 'Medium'
        else:
            return 'High'
    
    def _get_duration_range(self, duration_seconds: float) -> str:
        """获取持续时间范围"""
        if duration_seconds < 1:
            return 'Fast'
        elif duration_seconds < 10:
            return 'Normal'
        elif duration_seconds < 60:
            return 'Slow'
        else:
            return 'VerySlow'
    
    def __del__(self):
        """析构函数，确保指标被发送"""
        try:
            self.flush_metrics()
        except:
            pass


# 监控装饰器
def monitor_performance(operation_name: str):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitoring = SimpleMonitoring()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                monitoring.record_processing_duration(operation_name, duration)
                monitoring.record_metric(
                    f'{operation_name}Success',
                    1.0,
                    MetricType.COUNTER
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                monitoring.record_processing_duration(operation_name, duration)
                monitoring.record_error_occurrence(
                    type(e).__name__,
                    operation_name
                )
                
                raise
        
        return wrapper
    return decorator


# 使用示例
if __name__ == "__main__":
    # 创建监控实例
    monitoring = SimpleMonitoring()
    
    # 记录一些示例指标
    monitoring.record_context_identification_success('sagemaker_notebook', True)
    monitoring.record_job_id_validation_confidence(0.85, 'test-job')
    monitoring.record_lineage_merge_status('success', 50, 30)
    
    # 发送告警
    monitoring.send_alert(
        "Test alert message",
        AlertLevel.INFO,
        {'test_key': 'test_value'}
    )
    
    # 刷新指标
    monitoring.flush_metrics()
    
    # 获取指标摘要
    summary = monitoring.get_metrics_summary(1)
    print(f"Metrics summary: {summary}")
    
    # 创建仪表板
    dashboard_url = monitoring.create_dashboard()
    print(f"Dashboard URL: {dashboard_url}")
    
    # 设置告警
    monitoring.setup_alarms()