"""
配置管理器 - 环境配置管理
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from ..utils.logging_config import get_logger

logger = get_logger('config_manager')


class Environment(Enum):
    """环境枚举"""
    DEVELOPMENT = "dev"
    TEST = "test"
    PRODUCTION = "prod"


@dataclass
class AWSConfig:
    """AWS配置"""
    region: str = "us-east-1"
    profile: Optional[str] = None
    account_id: Optional[str] = None


@dataclass
class DynamoDBConfig:
    """DynamoDB配置"""
    region: str = "us-east-1"
    job_mapping_table: str = "enhanced-lineage-agent-job-execution-mappings"
    context_table: str = "enhanced-lineage-agent-execution-contexts"
    endpoint_url: Optional[str] = None  # 用于本地测试


@dataclass
class BedrockConfig:
    """Bedrock配置"""
    model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    region: str = "us-east-1"
    max_tokens: int = 4000
    temperature: float = 0.1


@dataclass
class ValidationConfig:
    """验证配置"""
    min_confidence_score: float = 0.7
    time_tolerance_seconds: int = 300
    enable_parameter_validation: bool = True
    enable_environment_validation: bool = True
    max_retries: int = 3


@dataclass
class MonitoringConfig:
    """监控配置"""
    namespace: str = "EnhancedLineageAgent"
    batch_size: int = 20
    alert_topic_arn: Optional[str] = None
    dashboard_name: str = "enhanced-lineage-agent"


@dataclass
class ErrorRecoveryConfig:
    """错误恢复配置"""
    max_retries: int = 3
    retry_delay_seconds: int = 5
    enable_fallback: bool = True
    enable_manual_intervention: bool = True


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5


@dataclass
class S3Config:
    """S3配置"""
    lineage_bucket: str = "enhanced-lineage-agent-lineage-data"
    region: str = "us-east-1"
    prefix: str = "lineage"


@dataclass
class EnhancedLineageConfig:
    """增强血缘配置"""
    aws: AWSConfig
    dynamodb: DynamoDBConfig
    bedrock: BedrockConfig
    validation: ValidationConfig
    monitoring: MonitoringConfig
    error_recovery: ErrorRecoveryConfig
    logging: LoggingConfig
    s3: S3Config
    environment: Environment


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, environment: Optional[str] = None):
        self.environment = Environment(environment or os.getenv('ENVIRONMENT', 'dev'))
        self.config_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config'
        )
        self._config: Optional[EnhancedLineageConfig] = None
        
        logger.info(f"Initialized config manager for environment: {self.environment.value}")
    
    def load_config(self) -> EnhancedLineageConfig:
        """加载配置"""
        if self._config is None:
            self._config = self._build_config()
        return self._config
    
    def _build_config(self) -> EnhancedLineageConfig:
        """构建配置"""
        try:
            # 加载基础配置
            base_config = self._load_base_config()
            
            # 加载环境特定配置
            env_config = self._load_environment_config()
            
            # 合并配置
            merged_config = self._merge_configs(base_config, env_config)
            
            # 应用环境变量覆盖
            final_config = self._apply_environment_overrides(merged_config)
            
            # 验证配置
            self._validate_config(final_config)
            
            return self._dict_to_config(final_config)
            
        except Exception as e:
            logger.error(f"Failed to build config: {str(e)}")
            raise
    
    def _load_base_config(self) -> Dict[str, Any]:
        """加载基础配置"""
        base_config_path = os.path.join(self.config_dir, 'config.yaml')
        
        if os.path.exists(base_config_path):
            with open(base_config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        else:
            logger.warning(f"Base config file not found: {base_config_path}")
            return self._get_default_config()
    
    def _load_environment_config(self) -> Dict[str, Any]:
        """加载环境特定配置"""
        env_config_path = os.path.join(
            self.config_dir, 
            f'config-{self.environment.value}.yaml'
        )
        
        if os.path.exists(env_config_path):
            with open(env_config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        else:
            logger.info(f"Environment config file not found: {env_config_path}")
            return {}
    
    def _merge_configs(self, base: Dict[str, Any], env: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置"""
        def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
            result = dict1.copy()
            for key, value in dict2.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(base, env)
    
    def _apply_environment_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖"""
        # 环境变量映射
        env_mappings = {
            'AWS_REGION': ['aws', 'region'],
            'AWS_PROFILE': ['aws', 'profile'],
            'AWS_ACCOUNT_ID': ['aws', 'account_id'],
            
            'DYNAMODB_REGION': ['dynamodb', 'region'],
            'DYNAMODB_JOB_MAPPING_TABLE': ['dynamodb', 'job_mapping_table'],
            'DYNAMODB_CONTEXT_TABLE': ['dynamodb', 'context_table'],
            'DYNAMODB_ENDPOINT_URL': ['dynamodb', 'endpoint_url'],
            
            'BEDROCK_MODEL_ID': ['bedrock', 'model_id'],
            'BEDROCK_REGION': ['bedrock', 'region'],
            'BEDROCK_MAX_TOKENS': ['bedrock', 'max_tokens'],
            'BEDROCK_TEMPERATURE': ['bedrock', 'temperature'],
            
            'VALIDATION_MIN_CONFIDENCE_SCORE': ['validation', 'min_confidence_score'],
            'VALIDATION_TIME_TOLERANCE_SECONDS': ['validation', 'time_tolerance_seconds'],
            'VALIDATION_ENABLE_PARAMETER_VALIDATION': ['validation', 'enable_parameter_validation'],
            'VALIDATION_ENABLE_ENVIRONMENT_VALIDATION': ['validation', 'enable_environment_validation'],
            
            'MONITORING_NAMESPACE': ['monitoring', 'namespace'],
            'MONITORING_BATCH_SIZE': ['monitoring', 'batch_size'],
            'MONITORING_ALERT_TOPIC_ARN': ['monitoring', 'alert_topic_arn'],
            
            'ERROR_RECOVERY_MAX_RETRIES': ['error_recovery', 'max_retries'],
            'ERROR_RECOVERY_RETRY_DELAY_SECONDS': ['error_recovery', 'retry_delay_seconds'],
            
            'LOGGING_LEVEL': ['logging', 'level'],
            'LOGGING_FILE_PATH': ['logging', 'file_path'],
            
            'S3_LINEAGE_BUCKET': ['s3', 'lineage_bucket'],
            'S3_REGION': ['s3', 'region'],
            'S3_PREFIX': ['s3', 'prefix']
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # 类型转换
                if env_var.endswith('_SECONDS') or env_var.endswith('_RETRIES') or env_var.endswith('_SIZE') or env_var.endswith('_TOKENS'):
                    env_value = int(env_value)
                elif env_var.endswith('_SCORE') or env_var.endswith('_TEMPERATURE'):
                    env_value = float(env_value)
                elif env_var.endswith('_VALIDATION') or env_var.endswith('_FALLBACK') or env_var.endswith('_INTERVENTION'):
                    env_value = env_value.lower() in ('true', '1', 'yes', 'on')
                
                # 设置配置值
                current = config
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[config_path[-1]] = env_value
        
        return config
    
    def _validate_config(self, config: Dict[str, Any]):
        """验证配置"""
        required_sections = ['aws', 'dynamodb', 'bedrock', 'validation', 'monitoring']
        
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")
        
        # 验证AWS区域
        aws_region = config.get('aws', {}).get('region')
        if not aws_region:
            raise ValueError("AWS region is required")
        
        # 验证DynamoDB表名
        job_mapping_table = config.get('dynamodb', {}).get('job_mapping_table')
        if not job_mapping_table:
            raise ValueError("DynamoDB job mapping table name is required")
        
        # 验证Bedrock模型ID
        model_id = config.get('bedrock', {}).get('model_id')
        if not model_id:
            raise ValueError("Bedrock model ID is required")
        
        logger.info("Configuration validation passed")
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> EnhancedLineageConfig:
        """将字典转换为配置对象"""
        return EnhancedLineageConfig(
            aws=AWSConfig(**config_dict.get('aws', {})),
            dynamodb=DynamoDBConfig(**config_dict.get('dynamodb', {})),
            bedrock=BedrockConfig(**config_dict.get('bedrock', {})),
            validation=ValidationConfig(**config_dict.get('validation', {})),
            monitoring=MonitoringConfig(**config_dict.get('monitoring', {})),
            error_recovery=ErrorRecoveryConfig(**config_dict.get('error_recovery', {})),
            logging=LoggingConfig(**config_dict.get('logging', {})),
            s3=S3Config(**config_dict.get('s3', {})),
            environment=self.environment
        )
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'aws': {
                'region': 'us-east-1'
            },
            'dynamodb': {
                'region': 'us-east-1',
                'job_mapping_table': f'enhanced-lineage-agent-job-execution-mappings-{self.environment.value}',
                'context_table': f'enhanced-lineage-agent-execution-contexts-{self.environment.value}'
            },
            'bedrock': {
                'model_id': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'region': 'us-east-1',
                'max_tokens': 4000,
                'temperature': 0.1
            },
            'validation': {
                'min_confidence_score': 0.7,
                'time_tolerance_seconds': 300,
                'enable_parameter_validation': True,
                'enable_environment_validation': True,
                'max_retries': 3
            },
            'monitoring': {
                'namespace': 'EnhancedLineageAgent',
                'batch_size': 20,
                'dashboard_name': f'enhanced-lineage-agent-{self.environment.value}'
            },
            'error_recovery': {
                'max_retries': 3,
                'retry_delay_seconds': 5,
                'enable_fallback': True,
                'enable_manual_intervention': True
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            's3': {
                'lineage_bucket': f'enhanced-lineage-agent-lineage-data-{self.environment.value}',
                'region': 'us-east-1',
                'prefix': 'lineage'
            }
        }
    
    def save_config(self, config: EnhancedLineageConfig, file_path: Optional[str] = None):
        """保存配置到文件"""
        if file_path is None:
            file_path = os.path.join(
                self.config_dir, 
                f'config-{self.environment.value}-generated.yaml'
            )
        
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            config_dict = asdict(config)
            # 移除环境字段，因为它不需要保存
            config_dict.pop('environment', None)
            
            with open(file_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {str(e)}")
            raise
    
    def export_config_as_env_vars(self, config: EnhancedLineageConfig) -> str:
        """导出配置为环境变量格式"""
        env_vars = []
        
        # AWS配置
        env_vars.append(f"export AWS_REGION={config.aws.region}")
        if config.aws.profile:
            env_vars.append(f"export AWS_PROFILE={config.aws.profile}")
        if config.aws.account_id:
            env_vars.append(f"export AWS_ACCOUNT_ID={config.aws.account_id}")
        
        # DynamoDB配置
        env_vars.append(f"export DYNAMODB_REGION={config.dynamodb.region}")
        env_vars.append(f"export DYNAMODB_JOB_MAPPING_TABLE={config.dynamodb.job_mapping_table}")
        env_vars.append(f"export DYNAMODB_CONTEXT_TABLE={config.dynamodb.context_table}")
        
        # Bedrock配置
        env_vars.append(f"export BEDROCK_MODEL_ID={config.bedrock.model_id}")
        env_vars.append(f"export BEDROCK_REGION={config.bedrock.region}")
        env_vars.append(f"export BEDROCK_MAX_TOKENS={config.bedrock.max_tokens}")
        env_vars.append(f"export BEDROCK_TEMPERATURE={config.bedrock.temperature}")
        
        # 验证配置
        env_vars.append(f"export VALIDATION_MIN_CONFIDENCE_SCORE={config.validation.min_confidence_score}")
        env_vars.append(f"export VALIDATION_TIME_TOLERANCE_SECONDS={config.validation.time_tolerance_seconds}")
        env_vars.append(f"export VALIDATION_ENABLE_PARAMETER_VALIDATION={config.validation.enable_parameter_validation}")
        env_vars.append(f"export VALIDATION_ENABLE_ENVIRONMENT_VALIDATION={config.validation.enable_environment_validation}")
        
        # 监控配置
        env_vars.append(f"export MONITORING_NAMESPACE={config.monitoring.namespace}")
        env_vars.append(f"export MONITORING_BATCH_SIZE={config.monitoring.batch_size}")
        if config.monitoring.alert_topic_arn:
            env_vars.append(f"export MONITORING_ALERT_TOPIC_ARN={config.monitoring.alert_topic_arn}")
        
        # 错误恢复配置
        env_vars.append(f"export ERROR_RECOVERY_MAX_RETRIES={config.error_recovery.max_retries}")
        env_vars.append(f"export ERROR_RECOVERY_RETRY_DELAY_SECONDS={config.error_recovery.retry_delay_seconds}")
        
        # 日志配置
        env_vars.append(f"export LOGGING_LEVEL={config.logging.level}")
        if config.logging.file_path:
            env_vars.append(f"export LOGGING_FILE_PATH={config.logging.file_path}")
        
        # S3配置
        env_vars.append(f"export S3_LINEAGE_BUCKET={config.s3.lineage_bucket}")
        env_vars.append(f"export S3_REGION={config.s3.region}")
        env_vars.append(f"export S3_PREFIX={config.s3.prefix}")
        
        # 环境
        env_vars.append(f"export ENVIRONMENT={config.environment.value}")
        
        return '\n'.join(env_vars)
    
    def get_config_summary(self, config: EnhancedLineageConfig) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            'environment': config.environment.value,
            'aws_region': config.aws.region,
            'dynamodb_tables': {
                'job_mapping': config.dynamodb.job_mapping_table,
                'context': config.dynamodb.context_table
            },
            'bedrock_model': config.bedrock.model_id,
            'monitoring_namespace': config.monitoring.namespace,
            'validation_confidence_threshold': config.validation.min_confidence_score,
            's3_bucket': config.s3.lineage_bucket
        }


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(environment: Optional[str] = None) -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    
    if _config_manager is None or (environment and _config_manager.environment.value != environment):
        _config_manager = ConfigManager(environment)
    
    return _config_manager


def get_enhanced_config(environment: Optional[str] = None) -> EnhancedLineageConfig:
    """获取增强血缘配置"""
    return get_config_manager(environment).load_config()


# 使用示例
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Configuration Manager')
    parser.add_argument('--environment', '-e', choices=['dev', 'test', 'prod'], 
                       default='dev', help='Environment')
    parser.add_argument('--action', choices=['show', 'export', 'validate'], 
                       default='show', help='Action to perform')
    parser.add_argument('--output', '-o', help='Output file path')
    
    args = parser.parse_args()
    
    # 创建配置管理器
    config_manager = ConfigManager(args.environment)
    config = config_manager.load_config()
    
    if args.action == 'show':
        summary = config_manager.get_config_summary(config)
        print(json.dumps(summary, indent=2))
    
    elif args.action == 'export':
        env_vars = config_manager.export_config_as_env_vars(config)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(env_vars)
            print(f"Environment variables exported to: {args.output}")
        else:
            print(env_vars)
    
    elif args.action == 'validate':
        print(f"Configuration for {args.environment} is valid")
        summary = config_manager.get_config_summary(config)
        print("Configuration summary:")
        print(json.dumps(summary, indent=2))