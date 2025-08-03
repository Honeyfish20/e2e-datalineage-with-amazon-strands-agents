#!/usr/bin/env python3
"""
部署脚本 - Enhanced Lineage Agent
"""

import argparse
import boto3
import json
import time
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config import get_config
from utils.logging_config import get_logger

logger = get_logger('deployment')


class DeploymentManager:
    """部署管理器"""
    
    def __init__(self, environment: str, region: str, profile: Optional[str] = None):
        self.environment = environment
        self.region = region
        self.profile = profile
        
        # 初始化AWS会话
        session = boto3.Session(profile_name=profile, region_name=region)
        self.cloudformation = session.client('cloudformation')
        self.s3 = session.client('s3')
        self.lambda_client = session.client('lambda')
        
        # 配置
        self.stack_name = f"enhanced-lineage-agent-{environment}"
        self.template_path = os.path.join(
            os.path.dirname(__file__), 
            'cloudformation_template.yaml'
        )
        
        logger.info(f"Initialized deployment manager for {environment} in {region}")
    
    def deploy_infrastructure(self, parameters: Dict[str, str]) -> bool:
        """
        部署基础设施
        
        Args:
            parameters: CloudFormation参数
        
        Returns:
            bool: 部署是否成功
        """
        try:
            logger.info(f"Starting infrastructure deployment for {self.stack_name}")
            
            # 读取CloudFormation模板
            with open(self.template_path, 'r') as f:
                template_body = f.read()
            
            # 准备参数
            cf_parameters = [
                {'ParameterKey': key, 'ParameterValue': value}
                for key, value in parameters.items()
            ]
            
            # 检查堆栈是否存在
            stack_exists = self._stack_exists()
            
            if stack_exists:
                logger.info("Stack exists, updating...")
                operation = self._update_stack(template_body, cf_parameters)
            else:
                logger.info("Stack does not exist, creating...")
                operation = self._create_stack(template_body, cf_parameters)
            
            if operation:
                # 等待操作完成
                success = self._wait_for_stack_operation()
                if success:
                    logger.info("Infrastructure deployment completed successfully")
                    self._print_stack_outputs()
                    return True
                else:
                    logger.error("Infrastructure deployment failed")
                    return False
            else:
                logger.error("Failed to initiate stack operation")
                return False
                
        except Exception as e:
            logger.error(f"Infrastructure deployment failed: {str(e)}")
            return False
    
    def deploy_lambda_code(self, code_package_path: str) -> bool:
        """
        部署Lambda代码
        
        Args:
            code_package_path: 代码包路径
        
        Returns:
            bool: 部署是否成功
        """
        try:
            logger.info("Deploying Lambda code...")
            
            # 获取Lambda函数名
            function_name = f"enhanced-lineage-agent-context-aware-agent-{self.environment}"
            
            # 读取代码包
            with open(code_package_path, 'rb') as f:
                code_data = f.read()
            
            # 更新Lambda函数代码
            response = self.lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=code_data
            )
            
            logger.info(f"Lambda code updated successfully: {response['LastModified']}")
            return True
            
        except Exception as e:
            logger.error(f"Lambda code deployment failed: {str(e)}")
            return False
    
    def create_deployment_package(self) -> str:
        """
        创建部署包
        
        Returns:
            str: 部署包路径
        """
        try:
            import zipfile
            import tempfile
            
            logger.info("Creating deployment package...")
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
            package_path = temp_file.name
            temp_file.close()
            
            # 创建ZIP文件
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加项目文件
                project_dir = os.path.dirname(os.path.dirname(__file__))
                
                for root, dirs, files in os.walk(project_dir):
                    # 跳过不需要的目录
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'tests']]
                    
                    for file in files:
                        if file.endswith(('.py', '.yaml', '.json', '.txt')):
                            file_path = os.path.join(root, file)
                            arc_path = os.path.relpath(file_path, project_dir)
                            zipf.write(file_path, arc_path)
                
                # 添加Lambda处理函数
                lambda_handler_code = '''
import json
import sys
import os

# 添加项目路径
sys.path.insert(0, '/opt/python')
sys.path.insert(0, os.path.dirname(__file__))

from agents.context_aware_agent import ContextAwareAgent
from utils.logging_config import get_logger

logger = get_logger('lambda_handler')

def lambda_handler(event, context):
    """Lambda处理函数"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # 创建上下文感知代理
        agent = ContextAwareAgent()
        
        # 处理不同类型的事件
        action = event.get('action', 'health_check')
        
        if action == 'health_check':
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'healthy',
                    'timestamp': context.aws_request_id,
                    'environment': os.environ.get('ENVIRONMENT', 'unknown')
                })
            }
        elif action == 'monitoring_check':
            # 执行监控检查
            result = perform_monitoring_check()
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unknown action: {action}'
                })
            }
            
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'request_id': context.aws_request_id
            })
        }

def perform_monitoring_check():
    """执行监控检查"""
    try:
        from monitoring.simple_monitoring import SimpleMonitoring
        
        monitoring = SimpleMonitoring()
        
        # 记录健康检查指标
        monitoring.record_metric('HealthCheck', 1.0)
        
        # 获取指标摘要
        summary = monitoring.get_metrics_summary(1)
        
        return {
            'status': 'monitoring_check_completed',
            'metrics_summary': summary,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Monitoring check failed: {str(e)}")
        return {
            'status': 'monitoring_check_failed',
            'error': str(e)
        }
'''
                zipf.writestr('lambda_function.py', lambda_handler_code)
            
            logger.info(f"Deployment package created: {package_path}")
            return package_path
            
        except Exception as e:
            logger.error(f"Failed to create deployment package: {str(e)}")
            raise
    
    def validate_deployment(self) -> bool:
        """
        验证部署
        
        Returns:
            bool: 验证是否成功
        """
        try:
            logger.info("Validating deployment...")
            
            # 检查堆栈状态
            if not self._stack_exists():
                logger.error("Stack does not exist")
                return False
            
            stack_status = self._get_stack_status()
            if stack_status not in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                logger.error(f"Stack is in invalid state: {stack_status}")
                return False
            
            # 测试Lambda函数
            function_name = f"enhanced-lineage-agent-context-aware-agent-{self.environment}"
            
            try:
                test_event = {
                    'action': 'health_check',
                    'test': True
                }
                
                response = self.lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='RequestResponse',
                    Payload=json.dumps(test_event)
                )
                
                result = json.loads(response['Payload'].read())
                
                if result.get('statusCode') == 200:
                    logger.info("Lambda function test passed")
                else:
                    logger.error(f"Lambda function test failed: {result}")
                    return False
                    
            except Exception as e:
                logger.error(f"Lambda function test failed: {str(e)}")
                return False
            
            logger.info("Deployment validation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Deployment validation failed: {str(e)}")
            return False
    
    def rollback_deployment(self) -> bool:
        """
        回滚部署
        
        Returns:
            bool: 回滚是否成功
        """
        try:
            logger.info("Rolling back deployment...")
            
            # 取消堆栈更新（如果正在进行）
            try:
                self.cloudformation.cancel_update_stack(StackName=self.stack_name)
                logger.info("Stack update cancelled")
            except:
                pass
            
            # 等待堆栈稳定
            self._wait_for_stack_operation()
            
            logger.info("Deployment rollback completed")
            return True
            
        except Exception as e:
            logger.error(f"Deployment rollback failed: {str(e)}")
            return False
    
    def cleanup_deployment(self) -> bool:
        """
        清理部署
        
        Returns:
            bool: 清理是否成功
        """
        try:
            logger.info("Cleaning up deployment...")
            
            # 删除堆栈
            self.cloudformation.delete_stack(StackName=self.stack_name)
            
            # 等待删除完成
            waiter = self.cloudformation.get_waiter('stack_delete_complete')
            waiter.wait(
                StackName=self.stack_name,
                WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
            )
            
            logger.info("Deployment cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"Deployment cleanup failed: {str(e)}")
            return False
    
    def _stack_exists(self) -> bool:
        """检查堆栈是否存在"""
        try:
            self.cloudformation.describe_stacks(StackName=self.stack_name)
            return True
        except self.cloudformation.exceptions.ClientError:
            return False
    
    def _get_stack_status(self) -> str:
        """获取堆栈状态"""
        try:
            response = self.cloudformation.describe_stacks(StackName=self.stack_name)
            return response['Stacks'][0]['StackStatus']
        except:
            return 'UNKNOWN'
    
    def _create_stack(self, template_body: str, parameters: list) -> bool:
        """创建堆栈"""
        try:
            self.cloudformation.create_stack(
                StackName=self.stack_name,
                TemplateBody=template_body,
                Parameters=parameters,
                Capabilities=['CAPABILITY_NAMED_IAM'],
                Tags=[
                    {'Key': 'Environment', 'Value': self.environment},
                    {'Key': 'Project', 'Value': 'enhanced-lineage-agent'},
                    {'Key': 'DeployedBy', 'Value': 'deployment-script'},
                    {'Key': 'DeployedAt', 'Value': datetime.now().isoformat()}
                ]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create stack: {str(e)}")
            return False
    
    def _update_stack(self, template_body: str, parameters: list) -> bool:
        """更新堆栈"""
        try:
            self.cloudformation.update_stack(
                StackName=self.stack_name,
                TemplateBody=template_body,
                Parameters=parameters,
                Capabilities=['CAPABILITY_NAMED_IAM']
            )
            return True
        except self.cloudformation.exceptions.ClientError as e:
            if 'No updates are to be performed' in str(e):
                logger.info("No updates needed for stack")
                return True
            else:
                logger.error(f"Failed to update stack: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Failed to update stack: {str(e)}")
            return False
    
    def _wait_for_stack_operation(self) -> bool:
        """等待堆栈操作完成"""
        try:
            logger.info("Waiting for stack operation to complete...")
            
            # 确定等待器类型
            status = self._get_stack_status()
            
            if 'CREATE' in status:
                waiter = self.cloudformation.get_waiter('stack_create_complete')
            elif 'UPDATE' in status:
                waiter = self.cloudformation.get_waiter('stack_update_complete')
            else:
                logger.warning(f"Unknown stack status: {status}")
                return False
            
            waiter.wait(
                StackName=self.stack_name,
                WaiterConfig={'Delay': 30, 'MaxAttempts': 60}
            )
            
            final_status = self._get_stack_status()
            logger.info(f"Stack operation completed with status: {final_status}")
            
            return final_status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']
            
        except Exception as e:
            logger.error(f"Stack operation failed: {str(e)}")
            return False
    
    def _print_stack_outputs(self):
        """打印堆栈输出"""
        try:
            response = self.cloudformation.describe_stacks(StackName=self.stack_name)
            outputs = response['Stacks'][0].get('Outputs', [])
            
            if outputs:
                logger.info("Stack Outputs:")
                for output in outputs:
                    logger.info(f"  {output['OutputKey']}: {output['OutputValue']}")
            
        except Exception as e:
            logger.warning(f"Failed to get stack outputs: {str(e)}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Deploy Enhanced Lineage Agent')
    parser.add_argument('--environment', '-e', required=True, 
                       choices=['dev', 'test', 'prod'],
                       help='Deployment environment')
    parser.add_argument('--region', '-r', required=True,
                       help='AWS region')
    parser.add_argument('--profile', '-p',
                       help='AWS profile name')
    parser.add_argument('--alert-email', required=True,
                       help='Email address for alerts')
    parser.add_argument('--action', choices=['deploy', 'validate', 'rollback', 'cleanup'],
                       default='deploy', help='Action to perform')
    parser.add_argument('--bedrock-model-id', 
                       default='anthropic.claude-3-5-sonnet-20241022-v2:0',
                       help='Bedrock model ID')
    
    args = parser.parse_args()
    
    # 创建部署管理器
    deployment_manager = DeploymentManager(
        environment=args.environment,
        region=args.region,
        profile=args.profile
    )
    
    success = False
    
    try:
        if args.action == 'deploy':
            # 准备参数
            parameters = {
                'Environment': args.environment,
                'ProjectName': 'enhanced-lineage-agent',
                'BedrockModelId': args.bedrock_model_id,
                'AlertEmail': args.alert_email
            }
            
            # 部署基础设施
            logger.info("Starting deployment process...")
            success = deployment_manager.deploy_infrastructure(parameters)
            
            if success:
                # 创建并部署代码包
                logger.info("Creating deployment package...")
                package_path = deployment_manager.create_deployment_package()
                
                logger.info("Deploying Lambda code...")
                success = deployment_manager.deploy_lambda_code(package_path)
                
                # 清理临时文件
                os.unlink(package_path)
                
                if success:
                    # 验证部署
                    logger.info("Validating deployment...")
                    success = deployment_manager.validate_deployment()
        
        elif args.action == 'validate':
            success = deployment_manager.validate_deployment()
        
        elif args.action == 'rollback':
            success = deployment_manager.rollback_deployment()
        
        elif args.action == 'cleanup':
            success = deployment_manager.cleanup_deployment()
        
        if success:
            logger.info(f"Action '{args.action}' completed successfully")
            sys.exit(0)
        else:
            logger.error(f"Action '{args.action}' failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Deployment failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()