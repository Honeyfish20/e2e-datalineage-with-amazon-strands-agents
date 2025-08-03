#!/usr/bin/env python3
"""
项目设置脚本

自动化设置Enhanced Lineage Agent项目环境。
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_directory_structure():
    """创建项目目录结构"""
    logger.info("Creating project directory structure...")
    
    directories = [
        'agents',
        'models',
        'tools',
        'utils',
        'integrations',
        'deployment',
        'monitoring',
        'config',
        'examples',
        'tests',
        'scripts',
        'docs',
        'logs',
        'output'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    # 创建__init__.py文件
    init_files = [
        '__init__.py',
        'agents/__init__.py',
        'models/__init__.py',
        'tools/__init__.py',
        'utils/__init__.py',
        'integrations/__init__.py',
        'deployment/__init__.py',
        'monitoring/__init__.py'
    ]
    
    for init_file in init_files:
        Path(init_file).touch()
        logger.info(f"Created __init__.py: {init_file}")

def install_dependencies():
    """安装项目依赖"""
    logger.info("Installing project dependencies...")
    
    try:
        # 检查是否存在requirements.txt
        if Path('requirements.txt').exists():
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
            ], check=True)
            logger.info("Dependencies installed successfully")
        else:
            logger.warning("requirements.txt not found, skipping dependency installation")
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False
    
    return True

def setup_aws_credentials():
    """设置AWS凭证（如果需要）"""
    logger.info("Checking AWS credentials...")
    
    try:
        # 检查AWS CLI是否已配置
        result = subprocess.run([
            'aws', 'sts', 'get-caller-identity'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("AWS credentials are configured")
            return True
        else:
            logger.warning("AWS credentials not configured")
            logger.info("Please run 'aws configure' to set up your AWS credentials")
            return False
    
    except FileNotFoundError:
        logger.warning("AWS CLI not found")
        logger.info("Please install AWS CLI and configure your credentials")
        return False

def create_sample_config():
    """创建示例配置文件"""
    logger.info("Creating sample configuration files...")
    
    # 创建环境变量示例文件
    env_sample = """# Enhanced Lineage Agent Environment Variables
# Copy this file to .env and update with your values

# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# DynamoDB Configuration
DYNAMODB_TABLE_PREFIX=enhanced-lineage

# S3 Configuration
S3_LINEAGE_BUCKET=enhanced-lineage-data
S3_BACKUP_BUCKET=enhanced-lineage-backup

# Monitoring Configuration
CLOUDWATCH_NAMESPACE=EnhancedLineageAgent
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:lineage-alerts

# Security Configuration
KMS_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012

# Development Configuration
DEBUG=false
LOG_LEVEL=INFO
"""
    
    with open('.env.sample', 'w') as f:
        f.write(env_sample)
    
    logger.info("Created .env.sample file")

def run_initial_tests():
    """运行初始测试"""
    logger.info("Running initial tests...")
    
    try:
        # 运行基础导入测试
        test_imports = """
import sys
import os
sys.path.insert(0, '.')

try:
    from models.execution_context import ExecutionContext, EnvironmentType
    from models.job_mapping import JobExecutionMapping, ValidationStatus
    from utils.config_manager import ConfigManager
    print("✓ All core modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
"""
        
        result = subprocess.run([
            sys.executable, '-c', test_imports
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Initial import tests passed")
            print(result.stdout)
            return True
        else:
            logger.error("Initial import tests failed")
            print(result.stderr)
            return False
    
    except Exception as e:
        logger.error(f"Failed to run initial tests: {e}")
        return False

def create_development_scripts():
    """创建开发脚本"""
    logger.info("Creating development scripts...")
    
    # 创建运行测试的脚本
    test_script = """#!/bin/bash
# 运行所有测试

echo "Running Enhanced Lineage Agent tests..."

# 运行单元测试
python -m pytest tests/ -v

# 运行示例脚本
echo "Running basic usage example..."
python examples/basic_usage.py

echo "Tests completed!"
"""
    
    with open('scripts/run_tests.sh', 'w') as f:
        f.write(test_script)
    
    os.chmod('scripts/run_tests.sh', 0o755)
    
    # 创建启动开发环境的脚本
    dev_script = """#!/bin/bash
# 启动开发环境

echo "Setting up Enhanced Lineage Agent development environment..."

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Virtual environment activated"
fi

# 设置Python路径
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 加载环境变量
if [ -f ".env" ]; then
    export $(cat .env | xargs)
    echo "Environment variables loaded"
fi

echo "Development environment ready!"
echo "You can now run:"
echo "  python examples/basic_usage.py"
echo "  python examples/sagemaker_notebook_example.py"
echo "  python -m pytest tests/"
"""
    
    with open('scripts/setup_dev.sh', 'w') as f:
        f.write(dev_script)
    
    os.chmod('scripts/setup_dev.sh', 0o755)
    
    logger.info("Created development scripts")

def print_setup_summary():
    """打印设置摘要"""
    print("\n" + "="*60)
    print("Enhanced Lineage Agent Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Copy .env.sample to .env and update with your AWS configuration")
    print("2. Configure AWS credentials: aws configure")
    print("3. Install dependencies: pip install -r requirements.txt")
    print("4. Run setup script: ./scripts/setup_dev.sh")
    print("5. Run tests: ./scripts/run_tests.sh")
    print("6. Try examples:")
    print("   - python examples/basic_usage.py")
    print("   - python examples/sagemaker_notebook_example.py")
    print("\nProject structure:")
    print("├── agents/                  # Agent implementations")
    print("├── models/                  # Data models")
    print("├── tools/                   # Tools and utilities")
    print("├── utils/                   # Utility functions")
    print("├── integrations/            # System integrations")
    print("├── deployment/              # Deployment configurations")
    print("├── monitoring/              # Monitoring components")
    print("├── config/                   # Configuration files")
    print("├── examples/                 # Usage examples")
    print("├── tests/                    # Test files")
    print("├── scripts/                  # Setup and utility scripts")
    print("└── docs/                     # Documentation")
    print("\nFor more information, see the README.md file.")
    print("="*60)

def main():
    """主函数"""
    logger.info("Starting Enhanced Lineage Agent project setup...")
    
    try:
        # 1. 创建目录结构
        create_directory_structure()
        
        # 2. 创建示例配置
        create_sample_config()
        
        # 3. 创建开发脚本
        create_development_scripts()
        
        # 4. 安装依赖（可选）
        install_dependencies()
        
        # 5. 检查AWS凭证
        setup_aws_credentials()
        
        # 6. 运行初始测试
        run_initial_tests()
        
        # 7. 打印设置摘要
        print_setup_summary()
        
        logger.info("Project setup completed successfully!")
        return 0
    
    except Exception as e:
        logger.error(f"Project setup failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)