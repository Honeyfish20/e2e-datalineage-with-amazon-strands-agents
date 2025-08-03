"""
兼容性包装器 - 为现有脚本提供增强功能的无缝集成
"""

import sys
import os
import importlib.util
from typing import Any, Dict, Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from enhanced_lineage_agent.integrations.enhanced_glue_extractor import EnhancedGlueLineageExtractor
from enhanced_lineage_agent.integrations.enhanced_table_merger import EnhancedTableLineageMerger


class CompatibilityWrapper:
    """兼容性包装器，提供渐进式增强功能"""
    
    @staticmethod
    def enhance_glue_extractor_class():
        """增强现有的GlueLineageExtractor类"""
        def create_enhanced_extractor(session, lineage_output_path):
            """创建增强的Glue血缘提取器"""
            try:
                # 尝试创建增强版本
                return EnhancedGlueLineageExtractor(
                    session=session,
                    lineage_output_path=lineage_output_path,
                    enable_context_awareness=True
                )
            except Exception as e:
                print(f"[WARNING] Failed to create enhanced extractor: {e}")
                print("[INFO] Falling back to legacy mode")
                
                # 降级到传统模式
                return EnhancedGlueLineageExtractor(
                    session=session,
                    lineage_output_path=lineage_output_path,
                    enable_context_awareness=False
                )
        
        return create_enhanced_extractor
    
    @staticmethod
    def enhance_table_merger_class():
        """增强现有的TableLineageMerger类"""
        def create_enhanced_merger(output_dir=None):
            """创建增强的表血缘合并器"""
            try:
                # 尝试创建增强版本
                return EnhancedTableLineageMerger(
                    output_dir=output_dir,
                    enable_validation=True
                )
            except Exception as e:
                print(f"[WARNING] Failed to create enhanced merger: {e}")
                print("[INFO] Falling back to legacy mode")
                
                # 降级到传统模式
                return EnhancedTableLineageMerger(
                    output_dir=output_dir,
                    enable_validation=False
                )
        
        return create_enhanced_merger
    
    @staticmethod
    def patch_existing_script(script_path: str, backup: bool = True) -> bool:
        """
        为现有脚本添加增强功能的补丁
        
        Args:
            script_path: 脚本文件路径
            backup: 是否创建备份文件
        
        Returns:
            bool: 是否成功应用补丁
        """
        try:
            if not os.path.exists(script_path):
                print(f"[ERROR] Script not found: {script_path}")
                return False
            
            # 读取原始脚本
            with open(script_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # 创建备份
            if backup:
                backup_path = f"{script_path}.backup"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                print(f"[INFO] Backup created: {backup_path}")
            
            # 应用补丁
            if 'extract-lineage-to-s3.py' in script_path:
                patched_content = CompatibilityWrapper._patch_glue_extractor(original_content)
            elif 'table_lineage_merger.py' in script_path:
                patched_content = CompatibilityWrapper._patch_table_merger(original_content)
            else:
                print(f"[WARNING] Unknown script type: {script_path}")
                return False
            
            # 写入补丁后的内容
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(patched_content)
            
            print(f"[SUCCESS] Enhanced functionality added to: {script_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to patch script: {e}")
            return False
    
    @staticmethod
    def _patch_glue_extractor(content: str) -> str:
        """为Glue提取器脚本添加增强功能补丁"""
        # 添加导入语句
        import_patch = '''
# Enhanced lineage extractor integration
try:
    from enhanced_lineage_agent.integrations.compatibility_wrapper import CompatibilityWrapper
    ENHANCED_MODE_AVAILABLE = True
except ImportError:
    ENHANCED_MODE_AVAILABLE = False
    print("[INFO] Enhanced lineage features not available, using legacy mode")
'''
        
        # 修改GlueLineageExtractor类的创建
        class_patch = '''
    # Create extractor with enhanced capabilities if available
    if ENHANCED_MODE_AVAILABLE:
        try:
            extractor_factory = CompatibilityWrapper.enhance_glue_extractor_class()
            extractor = extractor_factory(session, args.output_path)
            print("[INFO] Using enhanced Glue lineage extractor")
        except Exception as e:
            print(f"[WARNING] Enhanced mode failed: {e}")
            extractor = GlueLineageExtractor(session, args.output_path)
            print("[INFO] Falling back to legacy extractor")
    else:
        extractor = GlueLineageExtractor(session, args.output_path)
'''
        
        # 在导入部分后添加增强功能导入
        if 'import boto3' in content:
            content = content.replace('import boto3', f'import boto3{import_patch}')
        
        # 替换extractor创建部分
        if 'extractor = GlueLineageExtractor(session, args.output_path)' in content:
            content = content.replace(
                'extractor = GlueLineageExtractor(session, args.output_path)',
                class_patch.strip()
            )
        
        return content
    
    @staticmethod
    def _patch_table_merger(content: str) -> str:
        """为表血缘合并器脚本添加增强功能补丁"""
        # 添加导入语句
        import_patch = '''
# Enhanced table merger integration
try:
    from enhanced_lineage_agent.integrations.compatibility_wrapper import CompatibilityWrapper
    ENHANCED_MODE_AVAILABLE = True
except ImportError:
    ENHANCED_MODE_AVAILABLE = False
    print("[INFO] Enhanced merger features not available, using legacy mode")
'''
        
        # 修改TableLineageMerger类的创建
        class_patch = '''
    # Create merger with enhanced capabilities if available
    if ENHANCED_MODE_AVAILABLE:
        try:
            merger_factory = CompatibilityWrapper.enhance_table_merger_class()
            merger = merger_factory(output_dir)
            print("[INFO] Using enhanced table lineage merger")
        except Exception as e:
            print(f"[WARNING] Enhanced mode failed: {e}")
            merger = TableLineageMerger(output_dir)
            print("[INFO] Falling back to legacy merger")
    else:
        merger = TableLineageMerger(output_dir)
'''
        
        # 在导入部分后添加增强功能导入
        if 'import json' in content:
            content = content.replace('import json', f'import json{import_patch}')
        
        # 替换merger创建部分
        if 'merger = TableLineageMerger(output_dir)' in content:
            content = content.replace(
                'merger = TableLineageMerger(output_dir)',
                class_patch.strip()
            )
        
        return content
    
    @staticmethod
    def create_migration_script():
        """创建迁移脚本，帮助用户升级现有脚本"""
        migration_script = '''#!/usr/bin/env python3
"""
血缘提取器增强功能迁移脚本
"""

import os
import sys
import argparse
from enhanced_lineage_agent.integrations.compatibility_wrapper import CompatibilityWrapper

def main():
    parser = argparse.ArgumentParser(description="Migrate existing lineage scripts to enhanced version")
    parser.add_argument('--script-dir', default='script', help="Directory containing scripts to migrate")
    parser.add_argument('--no-backup', action='store_true', help="Skip creating backup files")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    script_dir = args.script_dir
    if not os.path.exists(script_dir):
        print(f"[ERROR] Script directory not found: {script_dir}")
        return 1
    
    # 查找需要迁移的脚本
    scripts_to_migrate = []
    
    # Glue提取器脚本
    glue_script = os.path.join(script_dir, 'glue', 'extract-lineage-to-s3.py')
    if os.path.exists(glue_script):
        scripts_to_migrate.append(glue_script)
    
    # 表血缘合并器脚本
    merger_script = os.path.join(script_dir, 'table_lineage_merger.py')
    if os.path.exists(merger_script):
        scripts_to_migrate.append(merger_script)
    
    if not scripts_to_migrate:
        print("[INFO] No scripts found to migrate")
        return 0
    
    print(f"[INFO] Found {len(scripts_to_migrate)} scripts to migrate:")
    for script in scripts_to_migrate:
        print(f"  - {script}")
    
    if args.dry_run:
        print("[INFO] Dry run mode - no changes will be made")
        return 0
    
    # 执行迁移
    success_count = 0
    for script in scripts_to_migrate:
        print(f"\\n[INFO] Migrating: {script}")
        if CompatibilityWrapper.patch_existing_script(script, backup=not args.no_backup):
            success_count += 1
        else:
            print(f"[ERROR] Failed to migrate: {script}")
    
    print(f"\\n[INFO] Migration completed: {success_count}/{len(scripts_to_migrate)} scripts migrated successfully")
    
    if success_count > 0:
        print("\\n[INFO] Migration successful! Your scripts now have enhanced lineage capabilities.")
        print("[INFO] The enhanced features include:")
        print("  - Context-aware execution tracking")
        print("  - Intelligent log stream selection")
        print("  - Job ID validation")
        print("  - Lineage data validation")
        print("\\n[INFO] Enhanced features will be used automatically when available.")
        print("[INFO] If enhanced features fail, scripts will fall back to legacy mode.")
    
    return 0 if success_count == len(scripts_to_migrate) else 1

if __name__ == "__main__":
    sys.exit(main())
'''
        
        # 保存迁移脚本
        migration_path = os.path.join(project_root, 'migrate_lineage_scripts.py')
        with open(migration_path, 'w', encoding='utf-8') as f:
            f.write(migration_script)
        
        # 设置执行权限
        os.chmod(migration_path, 0o755)
        
        print(f"[INFO] Migration script created: {migration_path}")
        return migration_path
    
    @staticmethod
    def verify_integration():
        """验证增强功能集成是否正常工作"""
        print("=== Enhanced Lineage Integration Verification ===\\n")
        
        try:
            # 测试增强的Glue提取器
            print("[INFO] Testing enhanced Glue extractor...")
            import boto3
            session = boto3.Session()
            
            extractor_factory = CompatibilityWrapper.enhance_glue_extractor_class()
            extractor = extractor_factory(session, "s3://test-bucket/test-path")
            
            print("  ✓ Enhanced Glue extractor created successfully")
            print(f"  ✓ Context awareness: {'Enabled' if extractor.enable_context_awareness else 'Disabled'}")
            
            # 测试增强的表合并器
            print("\\n[INFO] Testing enhanced table merger...")
            merger_factory = CompatibilityWrapper.enhance_table_merger_class()
            merger = merger_factory()
            
            print("  ✓ Enhanced table merger created successfully")
            print(f"  ✓ Validation features: {'Enabled' if merger.enable_validation else 'Disabled'}")
            
            print("\\n[SUCCESS] All enhanced features are working correctly!")
            return True
            
        except Exception as e:
            print(f"\\n[ERROR] Integration verification failed: {e}")
            print("[INFO] Enhanced features may not be available")
            return False


def main():
    """主函数 - 提供命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced lineage compatibility wrapper")
    parser.add_argument('--verify', action='store_true', help="Verify enhanced integration")
    parser.add_argument('--create-migration', action='store_true', help="Create migration script")
    parser.add_argument('--patch-script', help="Patch a specific script file")
    
    args = parser.parse_args()
    
    if args.verify:
        CompatibilityWrapper.verify_integration()
    elif args.create_migration:
        CompatibilityWrapper.create_migration_script()
    elif args.patch_script:
        CompatibilityWrapper.patch_existing_script(args.patch_script)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()