"""
配置管理器

管理系统的配置参数和环境设置。
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(__name__)
        self._config = {}
        
        # 加载默认配置
        self._load_default_config()
        
        # 加载环境配置
        self._load_environment_config()
        
        # 应用传入的配置
        if config:
            self._config.update(config)
        
        self.logger.info("Configuration manager initialized")
    
    def _load_default_config(self):
        """加载默认配置"""
        self._config = {
            # 代理配置
            'agent': {
                'model_id': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'max_retries': 3,
                'timeout_seconds': 300
            },
            
            # Job ID验证配置
            'job_validation': {
                'time_tolerance_seconds': 300,  # 5分钟
                'confidence_thresholds': {
                    'high': 0.8,
                    'medium': 0.6,
                    'low': 0.4
                },
                'max_candidates': 10
            },
            
            # 日志流选择配置
            'log_stream_selection': {
                'time_window_hours': 2,
                'max_streams': 50,
                'scoring_weights': {
                    'time_match': 0.4,
                    'environment_match': 0.25,
                    'content_quality': 0.2,
                    'size_relevance': 0.15
                }
            },
            
            # 监控配置
            'monitoring': {
                'enabled': True,
                'cloudwatch_namespace': 'EnhancedLineage/MVP',
                'metric_buffer_size': 100,
                'flush_interval_seconds': 60
            },
            
            # 存储配置
            'storage': {
                'dynamodb_table_prefix': 'enhanced-lineage',
                's3_bucket_prefix': 'enhanced-lineage-data',
                'region': 'us-east-1'
            },
            
            # 日志配置
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'enable_structured_logging': True
            }
        }
    
    def _load_environment_config(self):
        """从环境变量加载配置"""
        env_mappings = {
            'ENHANCED_LINEAGE_MODEL_ID': ['agent', 'model_id'],
            'ENHANCED_LINEAGE_REGION': ['storage', 'region'],
            'ENHANCED_LINEAGE_TABLE_PREFIX': ['storage', 'dynamodb_table_prefix'],
            'ENHANCED_LINEAGE_BUCKET_PREFIX': ['storage', 's3_bucket_prefix'],
            'ENHANCED_LINEAGE_LOG_LEVEL': ['logging', 'level'],
            'ENHANCED_LINEAGE_TIME_TOLERANCE': ['job_validation', 'time_tolerance_seconds'],
            'ENHANCED_LINEAGE_MONITORING_ENABLED': ['monitoring', 'enabled']
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                # 处理不同类型的值
                if config_path[-1] in ['time_tolerance_seconds', 'max_retries', 'timeout_seconds', 
                                      'metric_buffer_size', 'flush_interval_seconds']:
                    try:
                        value = int(value)
                    except ValueError:
                        self.logger.warning(f"Invalid integer value for {env_var}: {value}")
                        continue
                elif config_path[-1] in ['enabled']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                
                # 设置配置值
                self._set_nested_config(config_path, value)
    
    def _set_nested_config(self, path: list, value: Any):
        """设置嵌套配置值"""
        config = self._config
        for key in path[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[path[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """设置配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_agent_config(self) -> Dict[str, Any]:
        """获取代理配置"""
        return self._config.get('agent', {})
    
    def get_job_validation_config(self) -> Dict[str, Any]:
        """获取Job验证配置"""
        return self._config.get('job_validation', {})
    
    def get_log_stream_config(self) -> Dict[str, Any]:
        """获取日志流选择配置"""
        return self._config.get('log_stream_selection', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """获取监控配置"""
        return self._config.get('monitoring', {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """获取存储配置"""
        return self._config.get('storage', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self._config.get('logging', {})
    
    def load_from_file(self, config_file: str):
        """从文件加载配置"""
        config_path = Path(config_file)
        
        if not config_path.exists():
            self.logger.warning(f"Configuration file not found: {config_file}")
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() == '.json':
                    file_config = json.load(f)
                else:
                    # 支持其他格式（如YAML）的扩展点
                    raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
            
            # 深度合并配置
            self._deep_merge(self._config, file_config)
            self.logger.info(f"Configuration loaded from file: {config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration from file {config_file}: {e}")
            raise
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]):
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def save_to_file(self, config_file: str):
        """保存配置到文件"""
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration saved to file: {config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration to file {config_file}: {e}")
            raise
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置的有效性"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 验证必需的配置项
        required_configs = [
            'agent.model_id',
            'storage.region',
            'storage.dynamodb_table_prefix'
        ]
        
        for config_key in required_configs:
            if self.get(config_key) is None:
                validation_result['errors'].append(f"Missing required configuration: {config_key}")
                validation_result['is_valid'] = False
        
        # 验证数值范围
        numeric_validations = {
            'job_validation.time_tolerance_seconds': (1, 3600),  # 1秒到1小时
            'job_validation.confidence_thresholds.high': (0.5, 1.0),
            'job_validation.confidence_thresholds.medium': (0.3, 0.8),
            'job_validation.confidence_thresholds.low': (0.1, 0.6),
            'log_stream_selection.time_window_hours': (1, 24),
            'monitoring.flush_interval_seconds': (10, 300)
        }
        
        for config_key, (min_val, max_val) in numeric_validations.items():
            value = self.get(config_key)
            if value is not None and not (min_val <= value <= max_val):
                validation_result['warnings'].append(
                    f"Configuration {config_key} value {value} is outside recommended range [{min_val}, {max_val}]"
                )
        
        # 验证置信度阈值的逻辑关系
        high_threshold = self.get('job_validation.confidence_thresholds.high', 0.8)
        medium_threshold = self.get('job_validation.confidence_thresholds.medium', 0.6)
        low_threshold = self.get('job_validation.confidence_thresholds.low', 0.4)
        
        if not (high_threshold > medium_threshold > low_threshold):
            validation_result['errors'].append(
                "Confidence thresholds must be in descending order: high > medium > low"
            )
            validation_result['is_valid'] = False
        
        return validation_result
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"ConfigManager(keys={list(self._config.keys())})"