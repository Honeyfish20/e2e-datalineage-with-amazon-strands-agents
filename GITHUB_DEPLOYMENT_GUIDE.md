# GitHub部署指南

## 目标仓库
https://github.com/Honeyfish20/e2e-datalineage-with-amazon-strands-agents

## 部署前准备

### 1. 确保Git配置
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 2. 克隆目标仓库
```bash
git clone https://github.com/Honeyfish20/e2e-datalineage-with-amazon-strands-agents.git
cd e2e-datalineage-with-amazon-strands-agents
```

## 需要上传的文件和目录

### 核心项目文件
```
enhanced_lineage_agent/
├── __init__.py
├── agents/
│   ├── __init__.py
│   └── context_aware_agent.py
├── models/
│   ├── __init__.py
│   ├── execution_context.py
│   ├── job_mapping.py
│   ├── lineage_data.py
│   ├── lineage_validation.py
│   └── validation_result.py
├── tools/
│   ├── __init__.py
│   ├── context_extractor.py
│   ├── job_validator.py
│   ├── lineage_validator.py
│   ├── lineage_merger.py
│   └── log_stream_selector.py
└── utils/
    ├── __init__.py
    ├── config_manager.py
    ├── monitoring.py
    └── error_recovery.py
```

### 配置文件
```
config/
└── config.yaml
```

### 示例文件
```
examples/
├── basic_usage.py
└── sagemaker_notebook_example.py
```

### 测试文件
```
tests/
└── test_context_aware_agent.py
```

### 脚本文件
```
scripts/
└── setup_project.py
```

### 文档文件
```
docs/
└── CURRENT_STATUS.md
```

### 根目录文件
```
README.md
LICENSE
requirements.txt
setup.py
PROJECT_COMPLETION_SUMMARY.md
GITHUB_DEPLOYMENT_GUIDE.md
.env.sample
.gitignore
```

## 部署步骤

### 步骤1: 复制文件到仓库目录
将以下文件和目录从当前项目复制到克隆的仓库目录中：

```bash
# 假设当前项目在 /path/to/current/project
# 目标仓库在 /path/to/e2e-datalineage-with-amazon-strands-agents

# 复制核心代码
cp -r enhanced_lineage_agent/ /path/to/e2e-datalineage-with-amazon-strands-agents/

# 复制配置文件
cp -r config/ /path/to/e2e-datalineage-with-amazon-strands-agents/

# 复制示例文件
cp -r examples/ /path/to/e2e-datalineage-with-amazon-strands-agents/

# 复制测试文件
cp -r tests/ /path/to/e2e-datalineage-with-amazon-strands-agents/

# 复制脚本文件
cp -r scripts/ /path/to/e2e-datalineage-with-amazon-strands-agents/

# 复制文档文件
cp -r docs/ /path/to/e2e-datalineage-with-amazon-strands-agents/

# 复制根目录文件
cp README.md /path/to/e2e-datalineage-with-amazon-strands-agents/
cp LICENSE /path/to/e2e-datalineage-with-amazon-strands-agents/
cp requirements.txt /path/to/e2e-datalineage-with-amazon-strands-agents/
cp setup.py /path/to/e2e-datalineage-with-amazon-strands-agents/
cp PROJECT_COMPLETION_SUMMARY.md /path/to/e2e-datalineage-with-amazon-strands-agents/
cp GITHUB_DEPLOYMENT_GUIDE.md /path/to/e2e-datalineage-with-amazon-strands-agents/
```

### 步骤2: 创建.env.sample文件
```bash
cd /path/to/e2e-datalineage-with-amazon-strands-agents
cat > .env.sample << 'EOF'
# Enhanced Lineage Agent Environment Variables
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
EOF
```

### 步骤3: 创建.gitignore文件
```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Environment variables
.env

# Logs
logs/
*.log

# Test coverage
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# AWS
.aws/

# Temporary files
tmp/
temp/
*.tmp
*.temp

# Output files
output/
*.json
*.csv
*.parquet

# Jupyter Notebook
.ipynb_checkpoints

# pyenv
.python-version

# Kiro specific
.kiro/
EOF
```

### 步骤4: 添加文件到Git
```bash
cd /path/to/e2e-datalineage-with-amazon-strands-agents

# 添加所有文件
git add .

# 检查状态
git status
```

### 步骤5: 提交更改
```bash
# 提交更改
git commit -m "feat: Add Enhanced Lineage Agent MVP implementation

- Add context-aware intelligent agent for data lineage management
- Implement multi-dimensional Job ID validation and mapping
- Add intelligent lineage validation and merging capabilities
- Support multi-environment detection (SageMaker, Jupyter, Airflow, standalone)
- Include comprehensive examples, tests, and documentation
- Resolve Job ID confusion and cross-contamination issues
- Enable end-to-end data lineage across Glue, Redshift, and SageMaker

Core components:
- Context-aware agent with Claude 3.5 Sonnet integration
- Multi-source lineage validation and quality assurance
- Intelligent lineage merging engine
- Configuration management and monitoring system
- Complete test suite and usage examples"
```

### 步骤6: 推送到GitHub
```bash
# 推送到远程仓库
git push origin main
```

## 验证部署

### 1. 检查GitHub仓库
访问 https://github.com/Honeyfish20/e2e-datalineage-with-amazon-strands-agents 确认文件已成功上传。

### 2. 克隆测试
```bash
# 在新目录中测试克隆
git clone https://github.com/Honeyfish20/e2e-datalineage-with-amazon-strands-agents.git test-clone
cd test-clone

# 运行设置脚本
python scripts/setup_project.py

# 运行测试
python -m pytest tests/ -v

# 运行示例
python examples/basic_usage.py
```

## 部署后配置

### 1. 更新README.md中的仓库链接
确保README.md中的所有仓库链接都指向正确的GitHub地址。

### 2. 设置GitHub Pages（可选）
如果需要文档网站，可以在仓库设置中启用GitHub Pages。

### 3. 配置GitHub Actions（可选）
可以添加CI/CD流水线来自动运行测试。

## 文件清单检查

在推送前，请确认以下文件都已包含：

### 必需文件 ✅
- [ ] README.md
- [ ] LICENSE
- [ ] requirements.txt
- [ ] setup.py
- [ ] .gitignore
- [ ] .env.sample

### 核心代码 ✅
- [ ] enhanced_lineage_agent/agents/context_aware_agent.py
- [ ] enhanced_lineage_agent/models/ (所有模型文件)
- [ ] enhanced_lineage_agent/tools/ (所有工具文件)
- [ ] enhanced_lineage_agent/utils/ (所有工具文件)

### 配置和示例 ✅
- [ ] config/config.yaml
- [ ] examples/basic_usage.py
- [ ] examples/sagemaker_notebook_example.py

### 测试和脚本 ✅
- [ ] tests/test_context_aware_agent.py
- [ ] scripts/setup_project.py

### 文档 ✅
- [ ] docs/CURRENT_STATUS.md
- [ ] PROJECT_COMPLETION_SUMMARY.md
- [ ] GITHUB_DEPLOYMENT_GUIDE.md

## 故障排除

### 常见问题
1. **权限问题**: 确保有仓库的写权限
2. **文件过大**: 检查是否有大文件需要使用Git LFS
3. **路径问题**: 确保文件路径正确，特别是相对路径

### 联系支持
如果遇到问题，可以：
1. 检查GitHub仓库的Issues页面
2. 查看Git操作的错误信息
3. 确认网络连接和权限设置

---

*部署指南版本: 1.0*
*最后更新: 2025年1月*