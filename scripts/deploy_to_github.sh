#!/bin/bash

# Enhanced Lineage Agent GitHub部署脚本
# 使用方法: ./scripts/deploy_to_github.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查Git配置
check_git_config() {
    print_step "检查Git配置..."
    
    if ! git config user.name > /dev/null 2>&1; then
        print_error "Git用户名未配置"
        echo "请运行: git config --global user.name \"Your Name\""
        exit 1
    fi
    
    if ! git config user.email > /dev/null 2>&1; then
        print_error "Git邮箱未配置"
        echo "请运行: git config --global user.email \"your.email@example.com\""
        exit 1
    fi
    
    print_message "Git配置检查通过"
}

# 检查必需文件
check_required_files() {
    print_step "检查必需文件..."
    
    required_files=(
        "README.md"
        "LICENSE"
        "requirements.txt"
        "setup.py"
        ".gitignore"
        ".env.sample"
        "enhanced_lineage_agent/agents/context_aware_agent.py"
        "enhanced_lineage_agent/models/execution_context.py"
        "enhanced_lineage_agent/tools/lineage_validator.py"
        "enhanced_lineage_agent/utils/config_manager.py"
        "config/config.yaml"
        "examples/basic_usage.py"
        "tests/test_context_aware_agent.py"
        "scripts/setup_project.py"
    )
    
    missing_files=()
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        print_error "以下必需文件缺失:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        exit 1
    fi
    
    print_message "所有必需文件检查通过"
}

# 检查Python语法
check_python_syntax() {
    print_step "检查Python语法..."
    
    python_files=$(find enhanced_lineage_agent examples tests scripts -name "*.py" 2>/dev/null || true)
    
    if [[ -n "$python_files" ]]; then
        for file in $python_files; do
            if ! python -m py_compile "$file" 2>/dev/null; then
                print_error "Python语法错误: $file"
                exit 1
            fi
        done
        print_message "Python语法检查通过"
    else
        print_warning "未找到Python文件"
    fi
}

# 运行基础测试
run_basic_tests() {
    print_step "运行基础测试..."
    
    # 检查导入是否正常
    if python -c "
import sys
import os
sys.path.insert(0, '.')

try:
    from enhanced_lineage_agent.models.execution_context import ExecutionContext, EnvironmentType
    from enhanced_lineage_agent.models.job_mapping import JobExecutionMapping, ValidationStatus
    from enhanced_lineage_agent.utils.config_manager import ConfigManager
    print('✓ 所有核心模块导入成功')
except ImportError as e:
    print(f'✗ 导入错误: {e}')
    sys.exit(1)
" 2>/dev/null; then
        print_message "基础测试通过"
    else
        print_error "基础测试失败"
        exit 1
    fi
}

# Git操作
perform_git_operations() {
    print_step "执行Git操作..."
    
    # 检查是否在Git仓库中
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "当前目录不是Git仓库"
        echo "请先运行: git init"
        exit 1
    fi
    
    # 添加所有文件
    print_message "添加文件到Git..."
    git add .
    
    # 检查是否有更改
    if git diff --cached --quiet; then
        print_warning "没有检测到更改，跳过提交"
        return
    fi
    
    # 显示将要提交的文件
    print_message "将要提交的文件:"
    git diff --cached --name-only | sed 's/^/  /'
    
    # 提交更改
    commit_message="feat: Add Enhanced Lineage Agent MVP implementation

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

    print_message "提交更改..."
    git commit -m "$commit_message"
    
    # 推送到远程仓库
    print_message "推送到远程仓库..."
    if git remote get-url origin > /dev/null 2>&1; then
        git push origin main || git push origin master
        print_message "成功推送到远程仓库"
    else
        print_warning "未配置远程仓库，请手动添加远程仓库并推送"
        echo "示例命令:"
        echo "  git remote add origin https://github.com/Honeyfish20/e2e-datalineage-with-amazon-strands-agents.git"
        echo "  git push -u origin main"
    fi
}

# 生成部署报告
generate_deployment_report() {
    print_step "生成部署报告..."
    
    report_file="deployment_report_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << EOF
# Enhanced Lineage Agent 部署报告

**部署时间**: $(date)
**Git提交**: $(git rev-parse HEAD 2>/dev/null || echo "N/A")
**分支**: $(git branch --show-current 2>/dev/null || echo "N/A")

## 部署文件统计

### 核心代码文件
$(find enhanced_lineage_agent -name "*.py" | wc -l) 个Python文件

### 配置文件
$(find config -name "*.yaml" -o -name "*.yml" | wc -l) 个配置文件

### 示例文件
$(find examples -name "*.py" | wc -l) 个示例文件

### 测试文件
$(find tests -name "*.py" | wc -l) 个测试文件

### 文档文件
$(find docs -name "*.md" | wc -l) 个文档文件

## 文件清单

### 根目录文件
$(ls -la *.md *.txt *.py LICENSE .env.sample .gitignore 2>/dev/null | awk '{print "- " $9}' | grep -v "^- $")

### 目录结构
\`\`\`
$(tree -I '__pycache__|*.pyc|.git' -L 3 2>/dev/null || find . -type d -not -path '*/.*' | head -20 | sort)
\`\`\`

## 部署状态

✅ 文件检查通过
✅ Python语法检查通过
✅ 基础测试通过
✅ Git操作完成

## 下一步

1. 访问GitHub仓库确认文件上传成功
2. 运行完整测试: \`python -m pytest tests/ -v\`
3. 尝试运行示例: \`python examples/basic_usage.py\`
4. 查看文档: \`docs/CURRENT_STATUS.md\`

---
*自动生成于 $(date)*
EOF

    print_message "部署报告已生成: $report_file"
}

# 主函数
main() {
    echo "=========================================="
    echo "Enhanced Lineage Agent GitHub部署脚本"
    echo "=========================================="
    echo
    
    check_git_config
    check_required_files
    check_python_syntax
    run_basic_tests
    perform_git_operations
    generate_deployment_report
    
    echo
    print_message "🎉 部署完成！"
    echo
    echo "下一步:"
    echo "1. 访问 https://github.com/Honeyfish20/e2e-datalineage-with-amazon-strands-agents"
    echo "2. 确认文件已成功上传"
    echo "3. 查看部署报告了解详细信息"
    echo
}

# 运行主函数
main "$@"