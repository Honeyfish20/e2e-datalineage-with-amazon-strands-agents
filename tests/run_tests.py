#!/usr/bin/env python3
"""
测试运行器 - 运行所有测试套件
"""

import unittest
import sys
import os
import time
from io import StringIO

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


class TestResult:
    """测试结果类"""
    
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.skipped_tests = 0
        self.failures = []
        self.errors = []
        self.start_time = None
        self.end_time = None
    
    @property
    def duration(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    @property
    def success_rate(self):
        if self.total_tests == 0:
            return 0
        return (self.passed_tests / self.total_tests) * 100


class EnhancedTestRunner:
    """增强的测试运行器"""
    
    def __init__(self, verbosity=2):
        self.verbosity = verbosity
        self.result = TestResult()
    
    def discover_tests(self, test_dir=None):
        """发现测试"""
        if test_dir is None:
            test_dir = os.path.dirname(__file__)
        
        loader = unittest.TestLoader()
        suite = loader.discover(test_dir, pattern='test_*.py')
        return suite
    
    def run_tests(self, test_suite=None):
        """运行测试"""
        if test_suite is None:
            test_suite = self.discover_tests()
        
        print("=" * 70)
        print("Enhanced Lineage Agent - Test Suite")
        print("=" * 70)
        
        self.result.start_time = time.time()
        
        # 创建测试运行器
        stream = StringIO()
        runner = unittest.TextTestRunner(
            stream=stream,
            verbosity=self.verbosity,
            buffer=True
        )
        
        # 运行测试
        unittest_result = runner.run(test_suite)
        
        self.result.end_time = time.time()
        
        # 收集结果
        self.result.total_tests = unittest_result.testsRun
        self.result.failed_tests = len(unittest_result.failures)
        self.result.error_tests = len(unittest_result.errors)
        self.result.skipped_tests = len(unittest_result.skipped)
        self.result.passed_tests = (
            self.result.total_tests - 
            self.result.failed_tests - 
            self.result.error_tests - 
            self.result.skipped_tests
        )
        self.result.failures = unittest_result.failures
        self.result.errors = unittest_result.errors
        
        # 打印结果
        self._print_results()
        
        return self.result
    
    def run_specific_test(self, test_module, test_class=None, test_method=None):
        """运行特定测试"""
        if test_class and test_method:
            suite = unittest.TestSuite()
            suite.addTest(test_class(test_method))
        elif test_class:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        else:
            suite = unittest.TestLoader().loadTestsFromModule(test_module)
        
        return self.run_tests(suite)
    
    def _print_results(self):
        """打印测试结果"""
        print(f"\nTest Results:")
        print(f"{'='*50}")
        print(f"Total Tests:    {self.result.total_tests}")
        print(f"Passed:         {self.result.passed_tests}")
        print(f"Failed:         {self.result.failed_tests}")
        print(f"Errors:         {self.result.error_tests}")
        print(f"Skipped:        {self.result.skipped_tests}")
        print(f"Success Rate:   {self.result.success_rate:.1f}%")
        print(f"Duration:       {self.result.duration:.2f}s")
        print(f"{'='*50}")
        
        # 打印失败详情
        if self.result.failures:
            print(f"\nFAILURES ({len(self.result.failures)}):")
            print("-" * 50)
            for test, traceback in self.result.failures:
                print(f"FAIL: {test}")
                print(traceback)
                print("-" * 50)
        
        # 打印错误详情
        if self.result.errors:
            print(f"\nERRORS ({len(self.result.errors)}):")
            print("-" * 50)
            for test, traceback in self.result.errors:
                print(f"ERROR: {test}")
                print(traceback)
                print("-" * 50)
        
        # 总结
        if self.result.failed_tests == 0 and self.result.error_tests == 0:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n❌ {self.result.failed_tests + self.result.error_tests} TESTS FAILED")


def run_unit_tests():
    """运行单元测试"""
    print("Running Unit Tests...")
    
    runner = EnhancedTestRunner(verbosity=2)
    
    # 导入测试模块
    try:
        from . import test_context_extractor
        from . import test_job_validator
        
        # 创建测试套件
        suite = unittest.TestSuite()
        
        # 添加上下文提取器测试
        suite.addTests(unittest.TestLoader().loadTestsFromModule(test_context_extractor))
        
        # 添加Job验证器测试
        suite.addTests(unittest.TestLoader().loadTestsFromModule(test_job_validator))
        
        return runner.run_tests(suite)
        
    except ImportError as e:
        print(f"Failed to import test modules: {e}")
        return None


def run_integration_tests():
    """运行集成测试"""
    print("Running Integration Tests...")
    
    runner = EnhancedTestRunner(verbosity=2)
    
    try:
        from . import test_lineage_integration
        
        suite = unittest.TestLoader().loadTestsFromModule(test_lineage_integration)
        return runner.run_tests(suite)
        
    except ImportError as e:
        print(f"Failed to import integration test module: {e}")
        return None


def run_performance_tests():
    """运行性能测试"""
    print("Running Performance Tests...")
    
    runner = EnhancedTestRunner(verbosity=2)
    
    try:
        from .test_lineage_integration import TestPerformance
        
        suite = unittest.TestLoader().loadTestsFromTestCase(TestPerformance)
        return runner.run_tests(suite)
        
    except ImportError as e:
        print(f"Failed to import performance test module: {e}")
        return None


def run_all_tests():
    """运行所有测试"""
    print("Running All Tests...")
    
    runner = EnhancedTestRunner(verbosity=2)
    suite = runner.discover_tests()
    return runner.run_tests(suite)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Lineage Agent Test Runner')
    parser.add_argument('--type', '-t', 
                       choices=['unit', 'integration', 'performance', 'all'],
                       default='all',
                       help='Type of tests to run')
    parser.add_argument('--verbosity', '-v', type=int, default=2,
                       help='Test output verbosity (0-2)')
    parser.add_argument('--module', '-m', 
                       help='Specific test module to run')
    parser.add_argument('--class', '-c', dest='test_class',
                       help='Specific test class to run')
    parser.add_argument('--method', dest='test_method',
                       help='Specific test method to run')
    parser.add_argument('--coverage', action='store_true',
                       help='Run tests with coverage analysis')
    
    args = parser.parse_args()
    
    # 设置覆盖率分析
    if args.coverage:
        try:
            import coverage
            cov = coverage.Coverage()
            cov.start()
        except ImportError:
            print("Coverage package not installed. Install with: pip install coverage")
            args.coverage = False
    
    try:
        # 运行指定类型的测试
        if args.module:
            # 运行特定模块
            runner = EnhancedTestRunner(verbosity=args.verbosity)
            module = __import__(f'enhanced_lineage_agent.tests.{args.module}', fromlist=[''])
            
            if args.test_class and args.test_method:
                test_class = getattr(module, args.test_class)
                result = runner.run_specific_test(module, test_class, args.test_method)
            elif args.test_class:
                test_class = getattr(module, args.test_class)
                result = runner.run_specific_test(module, test_class)
            else:
                result = runner.run_specific_test(module)
        
        elif args.type == 'unit':
            result = run_unit_tests()
        elif args.type == 'integration':
            result = run_integration_tests()
        elif args.type == 'performance':
            result = run_performance_tests()
        else:
            result = run_all_tests()
        
        # 停止覆盖率分析
        if args.coverage:
            cov.stop()
            cov.save()
            
            print("\nCoverage Report:")
            print("=" * 50)
            cov.report()
            
            # 生成HTML报告
            cov.html_report(directory='coverage_html_report')
            print("HTML coverage report generated in: coverage_html_report/")
        
        # 返回适当的退出码
        if result and result.failed_tests == 0 and result.error_tests == 0:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test execution failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()