"""
配置管理模块
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import json


@dataclass
class BedrockConfig:
    """Amazon Bedrock配置"""
    model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    region: str = "us-west-2"
    max_tokens: int = 4000
    temperature: float = 0.1


@dataclass
class DynamoDBConfig:
    """DynamoDB配置"""
    region: str = "us-west-2"
    execution_context_table: str = "execution-contexts"
    job_mapping_table: str = "job-execution-mappings"
    validation_result_table: str = "lineage-validation-results"


@dataclass
class CloudWatchConfig:
    """CloudWatch配置"""
    region: str = "us-west-2"
    namespace: str = "LineageExtractor/ContextAware"
    log_group: str = "/aws/lambda/enhanced-lineage-agent"


@dataclass
class ValidationConfig:
    """验证配置"""
    time_tolerance_seconds: int = 300  # 5分钟
    min_confidence_score: float = 0.7
    enable_parameter_validation: bool = True
    enable_environment_validation: bool = True


@dataclass
class Config:
    """主配置类"""
    
    # 子配置
    bedrock: BedrockConfig = field(default_factory=BedrockConfig)
    dynamodb: DynamoDBConfig = field(default_factory=DynamoDBConfig)
    cloudwatch: CloudWatchConfig = field(default_factory=CloudWatchConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    
    # 通用配置
    debug: bool = False
    log_level: str = "INFO"
    aws_region: str = "us-west-2"
    
    # 功能开关
    enable_monitoring: bool = True
    enable_error_recovery: bool = True
    enable_context_caching: bool = True
    
    @classmethod
    def from_env(cls) -> 'Config':
        """从环境变量创建配置"""
        config = cls()
        
        # Bedrock配置
        if os.getenv('BEDROCK_MODEL_ID'):
            config.bedrock.model_id = os.getenv('BEDROCK_MODEL_ID')
        if os.getenv('BEDROCK_REGION'):
            config.bedrock.region = os.getenv('BEDROCK_REGION')
        
        # DynamoDB配置
        if os.getenv('DYNAMODB_REGION'):
            config.dynamodb.region = os.getenv('DYNAMODB_REGION')
        if os.getenv('EXECUTION_CONTEXT_TABLE'):
            config.dynamodb.execution_context_table = os.getenv('EXECUTION_CONTEXT_TABLE')
        if os.getenv('JOB_MAPPING_TABLE'):
            config.dynamodb.job_mapping_table = os.getenv('JOB_MAPPING_TABLE')
        
        # CloudWatch配置
        if os.getenv('CLOUDWATCH_NAMESPACE'):
            config.cloudwatch.namespace = os.getenv('CLOUDWATCH_NAMESPACE')
        if os.getenv('LOG_GROUP'):
            config.cloudwatch.log_group = os.getenv('LOG_GROUP')
        
        # 通用配置
        if os.getenv('DEBUG'):
            config.debug = os.getenv('DEBUG').lower() == 'true'
        if os.getenv('LOG_LEVEL'):
            config.log_level = os.getenv('LOG_LEVEL')
        if os.getenv('AWS_REGION'):
            config.aws_region = os.getenv('AWS_REGION')
        
        # 验证配置
        if os.getenv('TIME_TOLERANCE_SECONDS'):
            config.validation.time_tolerance_seconds = int(os.getenv('TIME_TOLERANCE_SECONDS'))
        if os.getenv('MIN_CONFIDENCE_SCORE'):
            config.validation.min_confidence_score = float(os.getenv('MIN_CONFIDENCE_SCORE'))
        
        return config
    
    @classmethod
    def from_file(cls, config_file: str) -> 'Config':
        """从配置文件创建配置"""
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        config = cls()
        
        # 更新配置
        if 'bedrock' in data:
            for key, value in data['bedrock'].items():
                setattr(config.bedrock, key, value)
        
        if 'dynamodb' in data:
            for key, value in data['dynamodb'].items():
                setattr(config.dynamodb, key, value)
        
        if 'cloudwatch' in data:
            for key, value in data['cloudwatch'].items():
                setattr(config.cloudwatch, key, value)
        
        if 'validation' in data:
            for key, value in data['validation'].items():
                setattr(config.validation, key, value)
        
        # 更新通用配置
        for key in ['debug', 'log_level', 'aws_region', 'enable_monitoring', 
                   'enable_error_recovery', 'enable_context_caching']:
            if key in data:
                setattr(config, key, data[key])
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'bedrock': {
                'model_id': self.bedrock.model_id,
                'region': self.bedrock.region,
                'max_tokens': self.bedrock.max_tokens,
                'temperature': self.bedrock.temperature
            },
            'dynamodb': {
                'region': self.dynamodb.region,
                'execution_context_table': self.dynamodb.execution_context_table,
                'job_mapping_table': self.dynamodb.job_mapping_table,
                'validation_result_table': self.dynamodb.validation_result_table
            },
            'cloudwatch': {
                'region': self.cloudwatch.region,
                'namespace': self.cloudwatch.namespace,
                'log_group': self.cloudwatch.log_group
            },
            'validation': {
                'time_tolerance_seconds': self.validation.time_tolerance_seconds,
                'min_confidence_score': self.validation.min_confidence_score,
                'enable_parameter_validation': self.validation.enable_parameter_validation,
                'enable_environment_validation': self.validation.enable_environment_validation
            },
            'debug': self.debug,
            'log_level': self.log_level,
            'aws_region': self.aws_region,
            'enable_monitoring': self.enable_monitoring,
            'enable_error_recovery': self.enable_error_recovery,
            'enable_context_caching': self.enable_context_caching
        }


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config):
    """设置全局配置实例"""
    global _config
    _config = config