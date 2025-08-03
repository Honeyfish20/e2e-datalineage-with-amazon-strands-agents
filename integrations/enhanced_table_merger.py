"""
增强的表血缘合并器集成
"""

import json
import boto3
from datetime import datetime
from collections import defaultdict
import os
from urllib.parse import urlparse
import re
from typing import Dict, List, Any, Optional, Tuple

from ..agents.lineage_validator import LineageValidator
from ..models.execution_context import ExecutionContext
from ..models.lineage_validation import LineageValidationResult, ValidationStatus
from ..config import get_config
from ..utils.logging_config import get_contextual_logger


class EnhancedTableLineageMerger:
    """增强的表血缘合并器，集成血缘验证功能"""
    
    def __init__(self, output_dir=None, enable_validation=True):
        self.s3_client = boto3.client('s3')
        self.bucket_name = 'sales-forecast-demo-new'
        self.enable_validation = enable_validation
        
        # 设置输出目录
        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = os.path.expanduser("~/lineage_output")
            if not os.access(os.path.dirname(self.output_dir), os.W_OK):
                self.output_dir = "/tmp/lineage_output"
        
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory: {self.output_dir}")
        
        # 初始化增强功能组件
        if self.enable_validation:
            self.config = get_config()
            self.logger = get_contextual_logger('enhanced_table_merger')
            self.lineage_validator = LineageValidator()
        else:
            self.logger = None
            self.lineage_validator = None
    
    def list_s3_files(self, prefix):
        """列出S3路径下的所有文件（保持原有逻辑）"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                print(f"No files found in {prefix}")
                return []
                
            files = []
            for obj in response['Contents']:
                if obj['Key'].endswith('.json'):
                    files.append({
                        'key': obj['Key'],
                        'last_modified': obj['LastModified'],
                        'size': obj['Size']
                    })
            
            # 按修改时间排序，最新的在前
            files.sort(key=lambda x: x['last_modified'], reverse=True)
            return files
            
        except Exception as e:
            print(f"Error listing files from S3: {e}")
            return []
    
    def download_json_from_s3(self, s3_key):
        """从S3下载JSON文件（保持原有逻辑）"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except Exception as e:
            print(f"Error downloading {s3_key}: {e}")
            return None
    
    def extract_execution_context_from_lineage(self, lineage_data: Dict[str, Any]) -> Optional[ExecutionContext]:
        """从血缘数据中提取执行上下文信息"""
        if not self.enable_validation:
            return None
        
        try:
            # 检查是否有执行上下文信息
            metadata = lineage_data.get('metadata', {})
            context_info = metadata.get('execution_context')
            
            if context_info:
                # 从元数据重建执行上下文
                context = ExecutionContext(
                    context_id=context_info.get('context_id', 'unknown'),
                    environment_type=context_info.get('environment_type', 'unknown'),
                    timestamp=datetime.fromisoformat(context_info.get('timestamp', datetime.now().isoformat())),
                    process_id=context_info.get('process_id', 0),
                    command_line=context_info.get('command_line', ''),
                    working_directory=context_info.get('working_directory', ''),
                    user_id=context_info.get('user_id')
                )
                
                self.logger.info(f"Extracted execution context: {context.context_id}")
                return context
            else:
                # 尝试从事件元数据中提取
                events = lineage_data.get('events', [])
                for event in events:
                    event_metadata = event.get('_metadata', {})
                    event_context = event_metadata.get('execution_context')
                    
                    if event_context:
                        context = ExecutionContext(
                            context_id=event_context.get('context_id', 'unknown'),
                            environment_type=event_context.get('environment_type', 'unknown'),
                            timestamp=datetime.fromisoformat(event_context.get('timestamp', datetime.now().isoformat())),
                            process_id=event_context.get('process_id', 0)
                        )
                        
                        self.logger.info(f"Extracted context from event metadata: {context.context_id}")
                        return context
                
                self.logger.warning("No execution context found in lineage data")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to extract execution context: {str(e)}")
            return None
    
    def validate_lineage_compatibility(
        self, 
        glue_data: Dict[str, Any], 
        redshift_data: Dict[str, Any]
    ) -> LineageValidationResult:
        """验证Glue和Redshift血缘数据的兼容性"""
        if not self.enable_validation:
            # 如果未启用验证，返回默认通过结果
            return LineageValidationResult(
                is_valid=True,
                validation_status=ValidationStatus.PASSED,
                confidence_score=1.0,
                validation_timestamp=datetime.now(),
                issues=[],
                recommendations=[]
            )
        
        try:
            self.logger.info("Validating lineage compatibility between Glue and Redshift data")
            
            # 提取执行上下文
            glue_context = self.extract_execution_context_from_lineage(glue_data)
            redshift_context = self.extract_execution_context_from_lineage(redshift_data)
            
            # 使用血缘验证器进行验证
            validation_result = self.lineage_validator.validate_lineage_context_match(
                glue_lineage=glue_data,
                redshift_lineage=redshift_data,
                glue_context=glue_context,
                redshift_context=redshift_context
            )
            
            # 记录验证结果
            self.logger.info(
                f"Lineage validation completed: valid={validation_result.is_valid}, "
                f"confidence={validation_result.confidence_score:.2f}"
            )
            
            if validation_result.issues:
                self.logger.warning(f"Validation issues found: {len(validation_result.issues)}")
                for issue in validation_result.issues:
                    self.logger.warning(f"  - {issue}")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Lineage validation failed: {str(e)}")
            return LineageValidationResult(
                is_valid=False,
                validation_status=ValidationStatus.ERROR,
                confidence_score=0.0,
                validation_timestamp=datetime.now(),
                issues=[f"Validation error: {str(e)}"],
                recommendations=["Review lineage data and retry validation"]
            )
    
    def is_valid_table_or_dataset(self, name):
        """判断是否是有效的表或数据集（保持原有逻辑）"""
        invalid_patterns = [
            'analytics-output',
            '/logs/',
            '/temp/',
            'iam_role',
            '.log',
            '.txt'
        ]
        
        name_lower = name.lower()
        for pattern in invalid_patterns:
            if pattern in name_lower:
                return False
        
        return True
    
    def normalize_table_name(self, table_name):
        """标准化表名（保持原有逻辑）"""
        if 'temp_parquet_data' in table_name:
            return 'temp_parquet_data'
        
        if table_name.startswith('dev.public.'):
            table_name = table_name.replace('dev.public.', 'public.')
        elif table_name.startswith('dev.') and '.public.' not in table_name:
            return table_name
        
        return table_name
    
    def extract_glue_lineage(self, glue_data):
        """提取Glue作业的TABLE级血缘关系（保持原有逻辑）"""
        lineage_map = defaultdict(list)
        
        if 'events' not in glue_data:
            return lineage_map
            
        for event in glue_data['events']:
            if 'inputs' in event and 'outputs' in event:
                for input_ds in event['inputs']:
                    input_name = self.normalize_dataset_name(input_ds['namespace'], input_ds['name'])
                    
                    if not self.is_valid_table_or_dataset(input_name):
                        continue
                    
                    for output_ds in event['outputs']:
                        output_name = self.normalize_dataset_name(output_ds['namespace'], output_ds['name'])
                        
                        if not self.is_valid_table_or_dataset(output_name):
                            continue
                        
                        if output_name not in lineage_map[input_name]:
                            lineage_map[input_name].append(output_name)
        
        return lineage_map
    
    def extract_redshift_lineage(self, redshift_data):
        """提取Redshift的TABLE级血缘关系（保持原有逻辑）"""
        lineage_map = defaultdict(list)
        copy_operations = []
        
        if 'events' not in redshift_data:
            return lineage_map, copy_operations
            
        for event in redshift_data['events']:
            # 处理常规查询
            if 'inputs' in event and 'outputs' in event and event['inputs'] and event['outputs']:
                for input_ds in event['inputs']:
                    if input_ds['namespace'].startswith('redshift://'):
                        input_name = self.normalize_table_name(input_ds['name'])
                    else:
                        input_name = self.normalize_dataset_name(input_ds['namespace'], input_ds['name'])
                    
                    if not self.is_valid_table_or_dataset(input_name):
                        continue
                    
                    for output_ds in event['outputs']:
                        if output_ds['namespace'].startswith('redshift://'):
                            output_name = self.normalize_table_name(output_ds['name'])
                        else:
                            output_name = self.normalize_dataset_name(output_ds['namespace'], output_ds['name'])
                        
                        if not self.is_valid_table_or_dataset(output_name):
                            continue
                        
                        if output_name not in lineage_map[input_name]:
                            lineage_map[input_name].append(output_name)
            
            # 特殊处理COPY命令
            if 'job' in event and 'facets' in event['job']:
                if 'sql' in event['job']['facets']:
                    sql = event['job']['facets']['sql']['query']
                    if 'COPY' in sql.upper() and 'FROM' in sql.upper():
                        s3_path = self.extract_s3_path_from_sql(sql)
                        table_name = self.extract_table_name_from_sql(sql)
                        
                        if s3_path and table_name:
                            table_name = self.normalize_table_name(table_name)
                            copy_operations.append({
                                's3_path': s3_path,
                                'table_name': table_name,
                                'event_time': event.get('eventTime', '')
                            })
        
        return lineage_map, copy_operations
    
    def extract_s3_path_from_sql(self, sql):
        """从COPY SQL中提取S3路径（保持原有逻辑）"""
        pattern = r"FROM\\s+'([^']+)'|FROM\\s+\"([^\"]+)\""
        match = re.search(pattern, sql, re.IGNORECASE)
        if match:
            path = match.group(1) or match.group(2)
            return path.rstrip('/')
        return None
    
    def extract_table_name_from_sql(self, sql):
        """从COPY SQL中提取表名（保持原有逻辑）"""
        pattern = r"COPY\\s+(\\w+(?:\\.\\w+)*)\\s*[\\(\\s]"
        match = re.search(pattern, sql, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            if '.' not in table_name:
                table_name = f"public.{table_name}"
            return table_name
        return None
    
    def normalize_dataset_name(self, namespace, name):
        """标准化数据集名称（保持原有逻辑）"""
        if namespace.startswith('s3://'):
            return f"{namespace.replace('s3://', '')}/{name}".rstrip('/')
        elif namespace == 's3':
            return name.replace('s3://', '').rstrip('/')
        else:
            return f"{namespace}/{name}"
    
    def normalize_path(self, path):
        """标准化路径格式（保持原有逻辑）"""
        path = path.rstrip('/')
        path = path.replace('s3/s3://', '')
        path = path.replace('s3://', '')
        return path
    
    def merge_lineages_with_validation(
        self, 
        glue_lineage, 
        redshift_lineage, 
        copy_operations,
        validation_result: LineageValidationResult
    ):
        """合并血缘数据，考虑验证结果"""
        # 如果验证失败且置信度很低，可能需要特殊处理
        if not validation_result.is_valid and validation_result.confidence_score < 0.3:
            if self.enable_validation:
                self.logger.warning(
                    f"Lineage validation failed with low confidence ({validation_result.confidence_score:.2f}). "
                    "Proceeding with caution."
                )
                
                # 可以选择阻止合并或添加警告标记
                print(f"\\n[WARNING] Lineage validation failed:")
                for issue in validation_result.issues:
                    print(f"  - {issue}")
                
                # 询问用户是否继续
                if os.isatty(0):  # 检查是否在交互式终端中
                    response = input("\\nContinue with merge despite validation issues? (y/n): ").lower()
                    if response != 'y':
                        print("Merge aborted by user")
                        return None
        
        # 执行标准合并逻辑
        merged = self.merge_lineages(glue_lineage, redshift_lineage, copy_operations)
        
        # 如果启用验证，添加验证信息到结果中
        if self.enable_validation:
            merged['_validation_info'] = {
                'validation_performed': True,
                'validation_result': validation_result.to_dict(),
                'merge_timestamp': datetime.now().isoformat()
            }
        
        return merged
    
    def merge_lineages(self, glue_lineage, redshift_lineage, copy_operations):
        """合并Glue和Redshift的TABLE级血缘（保持原有逻辑）"""
        merged = defaultdict(list)
        
        # 首先添加所有Glue血缘
        for upstream, downstreams in glue_lineage.items():
            normalized_upstream = self.normalize_path(upstream)
            for downstream in downstreams:
                normalized_downstream = self.normalize_path(downstream)
                
                if not self.is_valid_table_or_dataset(normalized_downstream):
                    continue
                    
                if normalized_downstream not in merged[normalized_upstream]:
                    merged[normalized_upstream].append(normalized_downstream)
        
        # 处理COPY操作
        print("\\nProcessing COPY operations:")
        for copy_op in copy_operations:
            s3_path = self.normalize_path(copy_op['s3_path'])
            table_name = copy_op['table_name']
            
            print(f"  COPY: {s3_path} -> {table_name}")
            
            if table_name not in merged[s3_path]:
                merged[s3_path].append(table_name)
        
        # 然后添加Redshift血缘
        for upstream, downstreams in redshift_lineage.items():
            normalized_upstream = self.normalize_table_name(upstream) if not upstream.startswith('s3') else self.normalize_path(upstream)
            
            for downstream in downstreams:
                normalized_downstream = self.normalize_table_name(downstream)
                
                if not self.is_valid_table_or_dataset(normalized_downstream):
                    continue
                
                if normalized_downstream not in merged[normalized_upstream]:
                    merged[normalized_upstream].append(normalized_downstream)
        
        # 清理和验证最终结果
        cleaned_merged = {}
        for upstream, downstreams in merged.items():
            if not self.is_valid_table_or_dataset(upstream):
                continue
            
            cleaned_downstreams = []
            for downstream in downstreams:
                if not self.is_valid_table_or_dataset(downstream):
                    continue
                
                # 避免CSV直接连到temp表
                if '.csv' in upstream and 'temp_parquet_data' in downstream:
                    print(f"  Skipping invalid connection: {upstream} -> {downstream}")
                    continue
                
                if downstream not in cleaned_downstreams:
                    cleaned_downstreams.append(downstream)
            
            if cleaned_downstreams:
                cleaned_merged[upstream] = cleaned_downstreams
        
        return cleaned_merged
    
    def find_complete_paths(self, lineage):
        """查找完整的血缘路径（保持原有逻辑）"""
        print("\\nFinding complete lineage paths...")
        
        # 找出所有的源头（没有上游的节点）
        all_downstreams = set()
        for downstreams in lineage.values():
            all_downstreams.update(downstreams)
        
        sources = set(lineage.keys()) - all_downstreams
        sinks = all_downstreams - set(lineage.keys())
        
        print(f"  Sources: {sources}")
        print(f"  Sinks: {sinks}")
        
        # 查找从源到终点的所有路径
        all_paths = []
        for source in sources:
            for sink in sinks:
                paths = self.find_paths(source, sink, lineage)
                all_paths.extend(paths)
        
        return all_paths
    
    def find_paths(self, start, end, lineage, path=None):
        """递归查找从start到end的所有路径（保持原有逻辑）"""
        if path is None:
            path = []
        
        path = path + [start]
        
        if start == end:
            return [path]
        
        if start not in lineage:
            return []
        
        paths = []
        for node in lineage[start]:
            if node not in path:  # 避免循环
                newpaths = self.find_paths(node, end, lineage, path)
                paths.extend(newpaths)
        
        return paths
    
    def process_lineage_with_validation(self):
        """主处理函数 - 增强版本，包含验证功能"""
        print("Starting enhanced TABLE-level lineage processing with validation...")
        
        # 1. 获取最新的Glue血缘文件
        glue_files = self.list_s3_files('lineage-reports/glue-jobs/')
        if not glue_files:
            print("No Glue lineage files found")
            return None
            
        latest_glue = glue_files[0]
        print(f"Latest Glue file: {latest_glue['key']} (Modified: {latest_glue['last_modified']})")
        
        # 2. 获取最新的Redshift血缘文件
        redshift_files = self.list_s3_files('lineage/redshift/')
        if not redshift_files:
            print("No Redshift lineage files found")
            return None
            
        latest_redshift = redshift_files[0]
        print(f"Latest Redshift file: {latest_redshift['key']} (Modified: {latest_redshift['last_modified']})")
        
        # 3. 下载并解析文件
        print("\\nDownloading and parsing files...")
        glue_data = self.download_json_from_s3(latest_glue['key'])
        redshift_data = self.download_json_from_s3(latest_redshift['key'])
        
        if not glue_data or not redshift_data:
            print("Failed to download lineage files")
            return None
        
        # 4. 验证血缘兼容性
        print("\\nValidating lineage compatibility...")
        validation_result = self.validate_lineage_compatibility(glue_data, redshift_data)
        
        if self.enable_validation:
            print(f"Validation result: {'PASSED' if validation_result.is_valid else 'FAILED'}")
            print(f"Confidence score: {validation_result.confidence_score:.2f}")
            
            if validation_result.issues:
                print("Validation issues:")
                for issue in validation_result.issues:
                    print(f"  - {issue}")
            
            if validation_result.recommendations:
                print("Recommendations:")
                for rec in validation_result.recommendations:
                    print(f"  - {rec}")
        
        # 5. 提取血缘关系
        print("\\nExtracting TABLE-level lineage relationships...")
        glue_lineage = self.extract_glue_lineage(glue_data)
        print(f"Found {len(glue_lineage)} table relationships in Glue")
        
        redshift_lineage, copy_operations = self.extract_redshift_lineage(redshift_data)
        print(f"Found {len(redshift_lineage)} table relationships in Redshift")
        print(f"Found {len(copy_operations)} COPY operations")
        
        # 6. 合并血缘（考虑验证结果）
        print("\\nMerging TABLE-level lineages with validation...")
        merged_lineage = self.merge_lineages_with_validation(
            glue_lineage, redshift_lineage, copy_operations, validation_result
        )
        
        if merged_lineage is None:
            print("Merge was aborted")
            return None
        
        # 移除验证信息以进行路径查找
        validation_info = merged_lineage.pop('_validation_info', None)
        
        # 7. 查找完整路径
        complete_paths = self.find_complete_paths(merged_lineage)
        
        # 8. 创建输出
        output = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "lineage_type": "TABLE_LEVEL_ENHANCED",
                "glue_source": latest_glue['key'],
                "redshift_source": latest_redshift['key'],
                "total_tables": len(merged_lineage),
                "total_relationships": sum(len(v) for v in merged_lineage.values()),
                "complete_paths_found": len(complete_paths),
                "enhanced_features": {
                    "validation_enabled": self.enable_validation,
                    "merger_version": "2.0_enhanced"
                }
            },
            "table_lineage": merged_lineage,
            "complete_paths": [
                {
                    "path": path,
                    "length": len(path),
                    "source": path[0],
                    "target": path[-1]
                }
                for path in complete_paths
            ]
        }
        
        # 添加验证信息
        if validation_info:
            output["validation_info"] = validation_info
        
        # 9. 保存到本地文件
        output_filename = f"enhanced_table_lineage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = os.path.join(self.output_dir, output_filename)
        
        try:
            with open(output_path, 'w') as f:
                json.dump(output, f, indent=2)
            
            print(f"\\nEnhanced TABLE-level lineage merged successfully!")
            print(f"Output saved to: {output_path}")
            print(f"Total tables: {len(merged_lineage)}")
            print(f"Total relationships: {output['metadata']['total_relationships']}")
            print(f"Complete paths found: {len(complete_paths)}")
            
            if self.enable_validation:
                print(f"Validation status: {'PASSED' if validation_result.is_valid else 'FAILED'}")
                print(f"Validation confidence: {validation_result.confidence_score:.2f}")
            
            # 显示完整路径
            if complete_paths:
                print("\\nComplete lineage paths:")
                for i, path_info in enumerate(output['complete_paths']):
                    print(f"\\nPath {i+1}:")
                    path = path_info['path']
                    for j, node in enumerate(path):
                        print(f"  {'  ' * j}{'└─ ' if j > 0 else ''}{node}")
            
        except Exception as e:
            print(f"Error saving output file: {e}")
            alt_path = f"/tmp/{output_filename}"
            try:
                with open(alt_path, 'w') as f:
                    json.dump(output, f, indent=2)
                print(f"Output saved to alternative location: {alt_path}")
            except:
                print("Failed to save output file")
                return None
        
        # 10. 可选：上传到S3
        upload_choice = input("\\nUpload enhanced table lineage to S3? (y/n): ").lower()
        if upload_choice == 'y':
            s3_key = f"lineage/merged/enhanced_table_level/{output_filename}"
            self.upload_to_s3(output_path, s3_key)
        
        return output_path
    
    def process_lineage(self):
        """主处理函数 - 保持向后兼容性"""
        if self.enable_validation:
            return self.process_lineage_with_validation()
        else:
            # 调用原有的处理逻辑（简化版本）
            return self._process_lineage_legacy()
    
    def _process_lineage_legacy(self):
        """传统的处理逻辑（简化版本，保持向后兼容）"""
        print("Starting TABLE-level lineage processing (legacy mode)...")
        
        # 获取文件
        glue_files = self.list_s3_files('lineage-reports/glue-jobs/')
        redshift_files = self.list_s3_files('lineage/redshift/')
        
        if not glue_files or not redshift_files:
            print("Required lineage files not found")
            return None
        
        # 下载数据
        glue_data = self.download_json_from_s3(glue_files[0]['key'])
        redshift_data = self.download_json_from_s3(redshift_files[0]['key'])
        
        if not glue_data or not redshift_data:
            return None
        
        # 提取和合并
        glue_lineage = self.extract_glue_lineage(glue_data)
        redshift_lineage, copy_operations = self.extract_redshift_lineage(redshift_data)
        merged_lineage = self.merge_lineages(glue_lineage, redshift_lineage, copy_operations)
        complete_paths = self.find_complete_paths(merged_lineage)
        
        # 创建输出
        output = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "lineage_type": "TABLE_LEVEL",
                "glue_source": glue_files[0]['key'],
                "redshift_source": redshift_files[0]['key'],
                "total_tables": len(merged_lineage),
                "total_relationships": sum(len(v) for v in merged_lineage.values()),
                "complete_paths_found": len(complete_paths)
            },
            "table_lineage": merged_lineage,
            "complete_paths": [
                {
                    "path": path,
                    "length": len(path),
                    "source": path[0],
                    "target": path[-1]
                }
                for path in complete_paths
            ]
        }
        
        # 保存文件
        output_filename = f"table_lineage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = os.path.join(self.output_dir, output_filename)
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"TABLE-level lineage merged successfully!")
        print(f"Output saved to: {output_path}")
        
        return output_path
    
    def upload_to_s3(self, local_file, s3_key):
        """上传文件到S3（保持原有逻辑）"""
        try:
            self.s3_client.upload_file(local_file, self.bucket_name, s3_key)
            print(f"Uploaded to S3: s3://{self.bucket_name}/{s3_key}")
        except Exception as e:
            print(f"Error uploading to S3: {e}")


def create_enhanced_merger(output_dir=None, enable_validation=True):
    """创建增强的表血缘合并器实例"""
    return EnhancedTableLineageMerger(output_dir, enable_validation)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced table lineage merger with validation")
    parser.add_argument('--output-dir', help="Output directory for lineage files")
    parser.add_argument('--disable-validation', action='store_true', 
                       help="Disable lineage validation features")
    
    args = parser.parse_args()
    
    # 创建增强的合并器
    merger = EnhancedTableLineageMerger(
        output_dir=args.output_dir,
        enable_validation=not args.disable_validation
    )
    
    # 执行处理
    merger.process_lineage()


if __name__ == "__main__":
    main()