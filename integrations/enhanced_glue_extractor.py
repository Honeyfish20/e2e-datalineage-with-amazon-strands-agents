"""
增强的Glue血缘提取器集成
"""

import argparse
import json
import sys
import re
import boto3
from datetime import datetime, timezone, timedelta
from time import sleep, time
import os
from typing import Dict, List, Any, Optional

from ..agents.context_aware_agent import ContextAwareAgent
from ..tools.context_extractor import ExecutionContextExtractor
from ..tools.job_validator import JobIDValidator
from ..tools.log_stream_selector import IntelligentLogStreamSelector
from ..models.execution_context import ExecutionContext
from ..config import get_config
from ..utils.logging_config import get_contextual_logger

# 保持与原始脚本的兼容性
GLUE_LOG_GROUPS = [
    {
        'name': '/aws-glue/jobs/logs-v2',
        'stream_pattern': '{job_run_id}-driver'
    },
    {
        'name': '/aws-glue/jobs/error',
        'stream_pattern': '{job_run_id}'
    }
]

CONSOLE_TRANSPORT_PATTERN = "ConsoleTransport"
WAIT_TIME_SECONDS = 15


class EnhancedGlueLineageExtractor:
    """增强的Glue血缘提取器，集成上下文感知功能"""
    
    def __init__(self, session, lineage_output_path, enable_context_awareness=True):
        self.logs_client = session.client('logs')
        self.s3_client = session.client('s3')
        self.lineage_output_path = lineage_output_path
        self.enable_context_awareness = enable_context_awareness
        
        # 初始化增强功能组件
        if self.enable_context_awareness:
            self.config = get_config()
            self.logger = get_contextual_logger('enhanced_glue_extractor')
            
            # 初始化上下文感知组件
            self.context_extractor = ExecutionContextExtractor()
            self.job_validator = JobIDValidator()
            self.log_stream_selector = IntelligentLogStreamSelector()
            self.context_aware_agent = ContextAwareAgent()
            
            # 提取当前执行上下文
            self.execution_context = self._initialize_execution_context()
        else:
            self.logger = None
            self.execution_context = None
    
    def _initialize_execution_context(self) -> ExecutionContext:
        """初始化执行上下文"""
        try:
            # 提取基本上下文
            context = self.context_extractor.extract_context()
            
            # 使用代理分析上下文
            trigger_info = {
                'script_name': sys.argv[0] if sys.argv else 'unknown',
                'arguments': sys.argv[1:] if len(sys.argv) > 1 else [],
                'working_directory': os.getcwd(),
                'environment_variables': dict(os.environ)
            }
            
            # 让代理识别和验证上下文
            enhanced_context = self.context_aware_agent.identify_execution_context(trigger_info)
            
            self.logger.info(f"Initialized execution context: {enhanced_context.context_id}")
            return enhanced_context
            
        except Exception as e:
            self.logger.error(f"Failed to initialize execution context: {str(e)}")
            # 返回基本上下文作为后备
            return self.context_extractor.extract_context()
    
    def extract_json_from_message(self, message):
        """从日志消息中提取JSON对象（保持原有逻辑）"""
        json_objects = []
        
        # 查找所有可能的JSON起始位置
        start_positions = []
        for match in re.finditer(r'ConsoleTransport:\\s*{', message):
            start_positions.append(match.end() - 1)
        
        if not start_positions:
            for i, char in enumerate(message):
                if char == '{':
                    start_positions.append(i)
        
        for start_pos in start_positions:
            try:
                # 找到匹配的结束括号
                bracket_count = 0
                end_pos = start_pos
                
                for i in range(start_pos, len(message)):
                    if message[i] == '{':
                        bracket_count += 1
                    elif message[i] == '}':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_pos = i + 1
                            break
                
                if end_pos > start_pos:
                    json_str = message[start_pos:end_pos]
                    json_obj = json.loads(json_str)
                    
                    # 验证是否是OpenLineage事件
                    if 'eventType' in json_obj or 'eventTime' in json_obj:
                        json_objects.append(json_obj)
                        
            except Exception:
                pass
        
        return json_objects
    
    def find_log_streams(self, job_name=None, job_run_id=None, start_time=None):
        """查找相关的日志流 - 增强版本"""
        if self.enable_context_awareness and job_run_id:
            return self._find_log_streams_with_context_awareness(job_name, job_run_id, start_time)
        else:
            return self._find_log_streams_legacy(job_name, job_run_id, start_time)
    
    def _find_log_streams_with_context_awareness(self, job_name, job_run_id, start_time):
        """使用上下文感知的日志流查找"""
        try:
            self.logger.info(f"Finding log streams with context awareness for job {job_name}, run {job_run_id}")
            
            # 1. 验证Job Run ID是否属于当前执行上下文
            if job_run_id:
                validation_result = self.context_aware_agent.validate_job_id_selection(
                    job_name, job_run_id, self.execution_context
                )
                
                if not validation_result['is_valid']:
                    self.logger.warning(
                        f"Job Run ID {job_run_id} validation failed: {validation_result.get('reason', 'Unknown')}"
                    )
                    
                    # 根据置信度决定是否继续
                    if validation_result['confidence_score'] < 0.3:
                        self.logger.error("Job Run ID validation confidence too low, aborting")
                        return []
                    else:
                        self.logger.warning("Proceeding with low confidence Job Run ID")
            
            # 2. 获取所有可能的日志流
            all_streams = []
            for log_group_config in GLUE_LOG_GROUPS:
                log_group = log_group_config['name']
                stream_pattern = log_group_config['stream_pattern']
                
                try:
                    # 构造预期的日志流名称
                    expected_stream_name = stream_pattern.format(job_run_id=job_run_id)
                    
                    # 获取日志流列表
                    response = self.logs_client.describe_log_streams(
                        logGroupName=log_group,
                        orderBy='LastEventTime',
                        descending=True,
                        limit=50
                    )
                    
                    for stream in response.get('logStreams', []):
                        stream_info = {
                            'logGroup': log_group,
                            'logStreamName': stream['logStreamName'],
                            'lastEventTime': stream.get('lastEventTime', 0),
                            'storedBytes': stream.get('storedBytes', 0)
                        }
                        all_streams.append(stream_info)
                        
                except Exception as e:
                    self.logger.warning(f"Error accessing log group {log_group}: {e}")
            
            if not all_streams:
                self.logger.warning("No log streams found")
                return []
            
            # 3. 使用智能日志流选择器
            selection_result = self.log_stream_selector.select_log_stream(
                job_name, self.execution_context, all_streams
            )
            
            if selection_result['selected_stream']:
                selected_stream = selection_result['selected_stream']
                self.logger.info(
                    f"Intelligent selection chose: {selected_stream['logGroup']}/{selected_stream['logStreamName']} "
                    f"(score: {selection_result['score']:.2f}, confidence: {selection_result['confidence']:.2f})"
                )
                
                # 记录选择原因
                for reason in selection_result.get('reasons', []):
                    self.logger.info(f"Selection reason: {reason}")
                
                # 返回选中的日志流，但保持原有格式
                return [selected_stream]
            else:
                self.logger.warning("No suitable log stream selected")
                return []
                
        except Exception as e:
            self.logger.error(f"Context-aware log stream selection failed: {str(e)}")
            # 降级到传统方法
            return self._find_log_streams_legacy(job_name, job_run_id, start_time)
    
    def _find_log_streams_legacy(self, job_name, job_run_id, start_time):
        """传统的日志流查找方法（保持原有逻辑）"""
        found_streams = []
        
        for log_group_config in GLUE_LOG_GROUPS:
            log_group = log_group_config['name']
            stream_pattern = log_group_config['stream_pattern']
            
            try:
                # 如果有job_run_id，直接构造日志流名称
                if job_run_id:
                    expected_stream_name = stream_pattern.format(job_run_id=job_run_id)
                    
                    print(f"[INFO] Looking for log stream: {log_group}/{expected_stream_name}")
                    
                    try:
                        response = self.logs_client.describe_log_streams(
                            logGroupName=log_group,
                            logStreamNamePrefix=expected_stream_name,
                            limit=1
                        )
                        
                        if response.get('logStreams'):
                            for stream in response['logStreams']:
                                if stream['logStreamName'] == expected_stream_name:
                                    stream_info = {
                                        'logGroup': log_group,
                                        'logStreamName': stream['logStreamName'],
                                        'lastEventTime': stream.get('lastEventTime', 0)
                                    }
                                    found_streams.append(stream_info)
                                    print(f"[SUCCESS] Found log stream: {log_group}/{expected_stream_name}")
                                    break
                        else:
                            print(f"[WARNING] Log stream not found: {log_group}/{expected_stream_name}")
                    except self.logs_client.exceptions.ResourceNotFoundException:
                        print(f"[WARNING] Log stream does not exist: {log_group}/{expected_stream_name}")
                    except Exception as e:
                        print(f"[WARNING] Error checking log stream: {e}")
                
                # 如果没有job_run_id或没有找到特定的流，列出所有流
                if not job_run_id or not any(s['logGroup'] == log_group for s in found_streams):
                    print(f"[INFO] Listing all log streams in {log_group}...")
                    
                    paginator = self.logs_client.get_paginator('describe_log_streams')
                    params = {
                        'logGroupName': log_group,
                        'limit': 50
                    }
                    
                    if job_run_id:
                        params['logStreamNamePrefix'] = job_run_id
                    elif job_name:
                        params['logStreamNamePrefix'] = job_name
                    
                    stream_count = 0
                    for page in paginator.paginate(**params):
                        for stream in page.get('logStreams', []):
                            stream_count += 1
                            stream_name = stream['logStreamName']
                            
                            if job_run_id and job_run_id not in stream_name:
                                continue
                            
                            if job_name and not job_run_id and job_name not in stream_name:
                                continue
                            
                            stream_info = {
                                'logGroup': log_group,
                                'logStreamName': stream_name,
                                'lastEventTime': stream.get('lastEventTime', 0),
                                'storedBytes': stream.get('storedBytes', 0)
                            }
                            
                            if start_time and stream_info['lastEventTime'] > 0:
                                stream_time = datetime.fromtimestamp(
                                    stream_info['lastEventTime'] / 1000, 
                                    tz=timezone.utc
                                )
                                if stream_time < start_time - timedelta(hours=2):
                                    continue
                            
                            found_streams.append(stream_info)
                            print(f"[INFO] Found log stream: {log_group}/{stream_name}")
                    
                    if stream_count == 0:
                        print(f"[WARNING] No log streams found in {log_group}")
                
            except self.logs_client.exceptions.ResourceNotFoundException:
                print(f"[ERROR] Log group does not exist: {log_group}")
            except Exception as e:
                print(f"[WARNING] Error accessing log group {log_group}: {e}")
        
        # 按最后事件时间排序（最新的在前）
        found_streams.sort(key=lambda x: x['lastEventTime'], reverse=True)
        
        # 打印找到的所有日志流
        if found_streams:
            print(f"\\n[INFO] Summary - Found {len(found_streams)} log streams:")
            for stream in found_streams:
                if stream['lastEventTime'] > 0:
                    last_event = datetime.fromtimestamp(
                        stream['lastEventTime'] / 1000, 
                        tz=timezone.utc
                    ).isoformat()
                else:
                    last_event = "No events"
                    
                size_info = f", Size: {stream.get('storedBytes', 0)} bytes"
                print(f"  - {stream['logGroup']}/{stream['logStreamName']} (Last event: {last_event}{size_info})")
        
        return found_streams
    
    def extract_lineage_from_stream(self, log_group, log_stream, start_time=None):
        """从特定日志流提取血缘信息（保持原有逻辑，添加上下文信息）"""
        lineage_events = []
        
        try:
            print(f"[INFO] Extracting from {log_group}/{log_stream}")
            
            params = {
                'logGroupName': log_group,
                'logStreamNames': [log_stream],
                'filterPattern': f'"{CONSOLE_TRANSPORT_PATTERN}"'
            }
            
            if start_time:
                params['startTime'] = int((start_time - timedelta(minutes=5)).timestamp() * 1000)
                print(f"[INFO] Searching events from: {(start_time - timedelta(minutes=5)).isoformat()}")
            else:
                print(f"[INFO] No start time specified, searching all events")
            
            # 获取初始事件信息
            initial_response = self.logs_client.filter_log_events(
                logGroupName=log_group,
                logStreamNames=[log_stream],
                limit=10
            )
            
            if initial_response.get('events'):
                first_event = initial_response['events'][0]
                first_timestamp = datetime.fromtimestamp(
                    first_event['timestamp'] / 1000, 
                    tz=timezone.utc
                )
                print(f"[INFO] Log stream contains {len(initial_response['events'])} events (sample)")
                print(f"[INFO] First event timestamp: {first_timestamp.isoformat()}")
            else:
                print(f"[WARNING] Log stream appears to be empty")
            
            paginator = self.logs_client.get_paginator('filter_log_events')
            event_count = 0
            matching_event_count = 0
            
            for page in paginator.paginate(**params):
                for event in page.get('events', []):
                    event_count += 1
                    message = event['message']
                    
                    if CONSOLE_TRANSPORT_PATTERN in message:
                        matching_event_count += 1
                        json_objs = self.extract_json_from_message(message)
                        
                        for json_obj in json_objs:
                            if json_obj and 'eventType' in json_obj:
                                # 添加元数据，包括执行上下文信息
                                metadata = {
                                    'captured_at': datetime.fromtimestamp(
                                        event['timestamp'] / 1000, 
                                        tz=timezone.utc
                                    ).isoformat(),
                                    'log_group': log_group,
                                    'log_stream': log_stream
                                }
                                
                                # 如果启用了上下文感知，添加上下文信息
                                if self.enable_context_awareness and self.execution_context:
                                    metadata['execution_context'] = {
                                        'context_id': self.execution_context.context_id,
                                        'environment_type': self.execution_context.environment_type.value,
                                        'process_id': self.execution_context.process_id,
                                        'timestamp': self.execution_context.timestamp.isoformat()
                                    }
                                
                                json_obj['_metadata'] = metadata
                                lineage_events.append(json_obj)
            
            print(f"[INFO] Processed {matching_event_count} log events matching filter, found {len(lineage_events)} lineage events")
            
        except Exception as e:
            print(f"[ERROR] Error extracting from {log_stream}: {e}")
            import traceback
            traceback.print_exc()
        
        return lineage_events
    
    def save_lineage_to_s3(self, events, job_name, job_run_id=None):
        """将血缘信息保存到S3（增强版本，包含上下文信息）"""
        if not events:
            print("[WARNING] No lineage events to save")
            return None
        
        print(f"\\n[INFO] Saving {len(events)} lineage events to S3...")
        
        # 解析S3路径
        if self.lineage_output_path.startswith('s3://'):
            path_parts = self.lineage_output_path[5:].split('/', 1)
            bucket = path_parts[0]
            prefix = path_parts[1] if len(path_parts) > 1 else ''
        else:
            raise ValueError(f"Invalid S3 path: {self.lineage_output_path}")
        
        # 生成文件名
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        run_id_part = f"_{job_run_id}" if job_run_id else ""
        
        # 如果启用了上下文感知，在文件名中包含上下文ID
        context_part = ""
        if self.enable_context_awareness and self.execution_context:
            context_part = f"_{self.execution_context.context_id}"
        
        file_name = f"lineage_{job_name}{run_id_part}{context_part}_{timestamp}.json"
        key = f"{prefix}/{file_name}".strip('/') if prefix else file_name
        
        # 创建血缘文档
        lineage_document = {
            'metadata': {
                'job_name': job_name,
                'job_run_id': job_run_id,
                'extraction_timestamp': datetime.now(timezone.utc).isoformat(),
                'total_events': len(events),
                'event_types': {},
                'data_lineage': {
                    'inputs': [],
                    'outputs': [],
                    'transformations': []
                },
                'enhanced_features': {
                    'context_awareness_enabled': self.enable_context_awareness,
                    'extractor_version': '2.0_enhanced'
                }
            },
            'events': events
        }
        
        # 如果启用了上下文感知，添加执行上下文信息
        if self.enable_context_awareness and self.execution_context:
            lineage_document['metadata']['execution_context'] = {
                'context_id': self.execution_context.context_id,
                'environment_type': self.execution_context.environment_type.value,
                'timestamp': self.execution_context.timestamp.isoformat(),
                'process_id': self.execution_context.process_id,
                'command_line': self.execution_context.command_line,
                'working_directory': self.execution_context.working_directory,
                'user_id': self.execution_context.user_id,
                'unique_identifier': self.execution_context.get_unique_identifier()
            }
        
        # 分析事件（保持原有逻辑）
        for event in events:
            event_type = event.get('eventType', 'unknown')
            lineage_document['metadata']['event_types'][event_type] = \\
                lineage_document['metadata']['event_types'].get(event_type, 0) + 1
            
            # 提取输入/输出数据集
            if 'inputs' in event:
                for input_ds in event['inputs']:
                    ds_info = {
                        'namespace': input_ds.get('namespace'),
                        'name': input_ds.get('name'),
                        'facets': input_ds.get('facets', {})
                    }
                    if ds_info not in lineage_document['metadata']['data_lineage']['inputs']:
                        lineage_document['metadata']['data_lineage']['inputs'].append(ds_info)
            
            if 'outputs' in event:
                for output_ds in event['outputs']:
                    ds_info = {
                        'namespace': output_ds.get('namespace'),
                        'name': output_ds.get('name'),
                        'facets': output_ds.get('facets', {})
                    }
                    if ds_info not in lineage_document['metadata']['data_lineage']['outputs']:
                        lineage_document['metadata']['data_lineage']['outputs'].append(ds_info)
        
        # 上传到S3
        try:
            response = self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(lineage_document, indent=2),
                ContentType='application/json'
            )
            print(f"[SUCCESS] Lineage saved to s3://{bucket}/{key}")
            print(f"[INFO] S3 ETag: {response.get('ETag', 'unknown')}")
            
            # 打印事件统计
            print("\\n[INFO] Event Statistics:")
            for event_type, count in lineage_document['metadata']['event_types'].items():
                print(f"  - {event_type}: {count}")
            
            # 如果启用了上下文感知，记录上下文信息
            if self.enable_context_awareness and self.execution_context:
                print(f"[INFO] Execution Context: {self.execution_context.context_id}")
                print(f"[INFO] Environment: {self.execution_context.environment_type.value}")
            
            return f"s3://{bucket}/{key}"
        except Exception as e:
            print(f"[ERROR] Failed to save lineage to S3: {str(e)}")
            raise
    
    def extract_and_save_lineage(self, job_name, job_run_id=None, start_time=None, 
                                continuous=False):
        """提取并保存血缘信息（增强版本）"""
        all_events = []
        processed_streams = set()
        
        # 如果启用了上下文感知，记录开始信息
        if self.enable_context_awareness:
            self.logger.info(f"Starting enhanced lineage extraction for job {job_name}")
            if job_run_id:
                self.logger.info(f"Target Job Run ID: {job_run_id}")
            self.logger.info(f"Execution context: {self.execution_context.context_id}")
        
        while True:
            print("\\n[INFO] Searching for lineage events...")
            
            # 查找日志流（使用增强方法）
            streams = self.find_log_streams(job_name, job_run_id, start_time)
            
            if not streams:
                print("[WARNING] No log streams found")
                
                # 如果没有找到流，尝试等待一段时间再重试
                if not all_events and job_run_id:
                    print(f"[INFO] Waiting 30 seconds for log streams to be created...")
                    sleep(30)
                    
                    # 再次尝试
                    streams = self.find_log_streams(job_name, job_run_id, start_time)
                    
                    if not streams:
                        print("[ERROR] Still no log streams found after waiting")
                        # 尝试直接搜索（保持原有逻辑）
                        self._attempt_direct_search(job_name, job_run_id, all_events)
            else:
                print(f"[INFO] Found {len(streams)} log streams")
                
                # 从每个流提取事件
                for stream_info in streams:
                    stream_key = f"{stream_info['logGroup']}:{stream_info['logStreamName']}"
                    
                    if stream_key not in processed_streams:
                        events = self.extract_lineage_from_stream(
                            stream_info['logGroup'],
                            stream_info['logStreamName'],
                            start_time
                        )
                        
                        if events:
                            print(f"[SUCCESS] Found {len(events)} events in {stream_key}")
                            all_events.extend(events)
                            processed_streams.add(stream_key)
            
            # 去重
            if all_events:
                unique_events = []
                seen_events = set()
                
                for event in all_events:
                    event_key = json.dumps({
                        'eventType': event.get('eventType'),
                        'eventTime': event.get('eventTime'),
                        'run': {'runId': event.get('run', {}).get('runId')}
                    }, sort_keys=True)
                    
                    if event_key not in seen_events:
                        seen_events.add(event_key)
                        unique_events.append(event)
                
                print(f"[INFO] Total unique events: {len(unique_events)}")
                
                # 保存到S3
                if unique_events:
                    self.save_lineage_to_s3(unique_events, job_name, job_run_id)
            
            if not continuous:
                break
            
            # 持续模式：等待新事件
            print(f"\\n[INFO] Waiting {WAIT_TIME_SECONDS} seconds for new events...")
            sleep(WAIT_TIME_SECONDS)
            
            # 更新开始时间为最后处理的时间
            if all_events:
                last_event_time = max(
                    datetime.fromisoformat(e['eventTime']) 
                    for e in all_events if 'eventTime' in e
                )
                start_time = last_event_time
    
    def _attempt_direct_search(self, job_name, job_run_id, all_events):
        """尝试直接搜索（保持原有逻辑）"""
        print("[INFO] Attempting direct search using filter_log_events...")
        for log_group_config in GLUE_LOG_GROUPS:
            log_group = log_group_config['name']
            stream_pattern = log_group_config['stream_pattern']
            
            if job_run_id:
                expected_stream = stream_pattern.format(job_run_id=job_run_id)
                print(f"[INFO] Searching for events in {log_group} with stream pattern: {expected_stream}")
            
            try:
                response = self.logs_client.filter_log_events(
                    logGroupName=log_group,
                    filterPattern=f'"{CONSOLE_TRANSPORT_PATTERN}"',
                    startTime=int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp() * 1000)
                )
                
                if response.get('events'):
                    print(f"[INFO] Found {len(response['events'])} events in {log_group}")
                    for event in response['events']:
                        event_stream = event.get('logStreamName', '')
                        if job_run_id and (event_stream == expected_stream or job_run_id in event_stream):
                            message = event['message']
                            if CONSOLE_TRANSPORT_PATTERN in message:
                                json_objs = self.extract_json_from_message(message)
                                for json_obj in json_objs:
                                    if json_obj and 'eventType' in json_obj:
                                        metadata = {
                                            'captured_at': datetime.fromtimestamp(
                                                event['timestamp'] / 1000, 
                                                tz=timezone.utc
                                            ).isoformat(),
                                            'log_group': log_group,
                                            'log_stream': event_stream
                                        }
                                        
                                        # 添加上下文信息
                                        if self.enable_context_awareness and self.execution_context:
                                            metadata['execution_context'] = {
                                                'context_id': self.execution_context.context_id,
                                                'environment_type': self.execution_context.environment_type.value
                                            }
                                        
                                        json_obj['_metadata'] = metadata
                                        all_events.append(json_obj)
                                        
            except Exception as e:
                print(f"[WARNING] Direct search failed for {log_group}: {e}")
        
        if all_events:
            print(f"[SUCCESS] Found {len(all_events)} events using direct search")
            self.save_lineage_to_s3(all_events, job_name, job_run_id)


def create_enhanced_extractor(session, lineage_output_path, enable_context_awareness=True):
    """创建增强的Glue血缘提取器实例"""
    return EnhancedGlueLineageExtractor(session, lineage_output_path, enable_context_awareness)


def parse_arguments():
    """解析命令行参数（保持与原脚本兼容）"""
    parser = argparse.ArgumentParser(
        description="Enhanced Glue lineage extractor with context awareness."
    )
    parser.add_argument('-p', '--profile', help="AWS profile name")
    parser.add_argument('-r', '--region', help="AWS region", required=True)
    parser.add_argument('-j', '--job-name', help="Glue job name", required=True)
    parser.add_argument('-i', '--job-run-id', help="Specific job run ID")
    parser.add_argument('-o', '--output-path', help="S3 path for lineage output", required=True)
    parser.add_argument('-s', '--start-time', 
                       help="Start time in ISO format (default: 1 hour ago)")
    parser.add_argument('-c', '--continuous', action='store_true',
                       help="Continuously monitor for new lineage events")
    parser.add_argument('--no-time-filter', action='store_true',
                       help="Disable time filtering, search all events in the log stream")
    parser.add_argument('--disable-context-awareness', action='store_true',
                       help="Disable context awareness features (use legacy mode)")
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    print(f"\\n=== Enhanced Glue Lineage Extractor ===")
    print(f"Region: {args.region}")
    print(f"Job Name: {args.job_name}")
    print(f"Job Run ID: {args.job_run_id if args.job_run_id else 'Not specified'}")
    print(f"Output Path: {args.output_path}")
    print(f"Mode: {'Continuous' if args.continuous else 'One-time'}")
    print(f"Context Awareness: {'Disabled' if args.disable_context_awareness else 'Enabled'}")
    
    # 创建AWS会话
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    
    # 解析开始时间
    start_time = None
    if args.no_time_filter:
        print(f"Time Filter: Disabled (searching all events)")
    elif args.start_time:
        start_time = datetime.fromisoformat(args.start_time)
        print(f"Start Time: {start_time.isoformat()}")
    else:
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        print(f"Start Time: {start_time.isoformat()} (default: 1 hour ago)")
    
    # 创建增强的提取器并运行
    extractor = EnhancedGlueLineageExtractor(
        session, 
        args.output_path, 
        enable_context_awareness=not args.disable_context_awareness
    )
    
    try:
        extractor.extract_and_save_lineage(
            job_name=args.job_name,
            job_run_id=args.job_run_id,
            start_time=start_time,
            continuous=args.continuous
        )
    except KeyboardInterrupt:
        print("\\n[INFO] Extraction stopped by user")
    except Exception as e:
        print(f"\\n[ERROR] Extraction failed: {e}")
        import traceback
        traceback.print_exc()