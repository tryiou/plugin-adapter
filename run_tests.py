#!/usr/bin/env python3
"""
Plugin-Adapter Test Runner

This script provides a unified interface for running different types of tests
and generating comprehensive reports. It supports unit tests, integration tests,
end-to-end tests, and performance benchmarks.

Usage:
    python run_tests.py [options]

Examples:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run unit tests only
    python run_tests.py --coverage         # Run with coverage
    python run_tests.py --performance      # Run performance benchmarks
    python run_tests.py --report           # Generate test report
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pytest


class TestRunner:
    """Unified test runner for the plugin-adapter application."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.project_root = Path(__file__).parent
        self.src_path = self.project_root / "src"
        self.tests_path = self.project_root / "tests"
        
        # Test configuration
        self.test_config = {
            'unit': {
                'path': self.tests_path / "unit",
                'markers': ['unit'],
                'timeout': 300,  # 5 minutes
                'description': 'Unit tests for individual components'
            },
            'integration': {
                'path': self.tests_path / "integration",
                'markers': ['integration'],
                'timeout': 600,  # 10 minutes
                'description': 'Integration tests for component interactions'
            },
            'e2e': {
                'path': self.tests_path / "e2e",
                'markers': ['e2e'],
                'timeout': 1200,  # 20 minutes
                'description': 'End-to-end workflow tests'
            },
            'performance': {
                'path': self.tests_path / "performance",
                'markers': ['performance', 'benchmark'],
                'timeout': 1800,  # 30 minutes
                'description': 'Performance benchmarks and load tests'
            }
        }
        
        # Output directories
        self.output_dir = self.project_root / "test_output"
        self.reports_dir = self.output_dir / "reports"
        self.coverage_dir = self.output_dir / "coverage"
        
        # Ensure output directories exist
        self.output_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        self.coverage_dir.mkdir(exist_ok=True)
    
    def run_tests(self, test_type: str = "all", coverage: bool = False, 
                  verbose: bool = False, parallel: bool = False) -> Dict:
        """
        Run tests of the specified type.
        
        Args:
            test_type: Type of tests to run ('all', 'unit', 'integration', 'e2e', 'performance')
            coverage: Whether to run with coverage
            verbose: Whether to show verbose output
            parallel: Whether to run tests in parallel
            
        Returns:
            Test results dictionary
        """
        print(f"🚀 Running {test_type} tests...")
        print(f"📁 Project root: {self.project_root}")
        
        start_time = time.time()
        results = {
            'test_type': test_type,
            'start_time': start_time,
            'end_time': None,
            'duration': 0,
            'success': True,
            'tests_run': 0,
            'failures': 0,
            'errors': 0,
            'skipped': 0,
            'coverage': None,
            'reports': []
        }
        
        try:
            if test_type == "all":
                # Run all test types
                for test_category in ['unit', 'integration', 'e2e', 'performance']:
                    category_results = self._run_single_test_type(
                        test_category, coverage and test_category == 'unit',
                        verbose, parallel
                    )
                    results['success'] &= category_results['success']
                    results['tests_run'] += category_results['tests_run']
                    results['failures'] += category_results['failures']
                    results['errors'] += category_results['errors']
                    results['skipped'] += category_results['skipped']
                    
            else:
                # Run specific test type
                category_results = self._run_single_test_type(
                    test_type, coverage, verbose, parallel
                )
                results.update(category_results)
        
        except Exception as e:
            print(f"❌ Error running tests: {e}")
            results['success'] = False
            results['errors'] += 1
        
        finally:
            results['end_time'] = time.time()
            results['duration'] = results['end_time'] - results['start_time']
            
            # Generate summary report
            self._generate_summary_report(results)
            
            # Print results
            self._print_results(results)
        
        return results
    
    def _run_single_test_type(self, test_type: str, coverage: bool, 
                             verbose: bool, parallel: bool) -> Dict:
        """Run a single type of test."""
        config = self.test_config[test_type]
        
        print(f"\n📋 Running {test_type} tests...")
        print(f"   Description: {config['description']}")
        print(f"   Path: {config['path']}")
        
        # Build pytest arguments
        args = []
        
        # Add test path
        if config['path'].exists():
            args.extend([str(config['path'])])
        else:
            print(f"   ⚠️  Test path {config['path']} does not exist")
            return {'success': True, 'tests_run': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
        
        # Add markers
        if config['markers']:
            args.extend(['-m', ' or '.join(config['markers'])])
        
        # Add coverage options
        if coverage:
            args.extend([
                '--cov=src',
                f'--cov-report=html:{self.coverage_dir}/{test_type}',
                f'--cov-report=xml:{self.reports_dir}/coverage-{test_type}.xml',
                '--cov-report=term-missing'
            ])
        
        # Add verbosity
        if verbose:
            args.extend(['-v', '-s'])
        else:
            args.append('-q')
        
        # Add parallel execution
        if parallel:
            args.extend(['-n', 'auto'])
        
        # Add output options
        args.extend([
            f'--html={self.reports_dir}/{test_type}-report.html',
            f'--json-report-file={self.reports_dir}/{test_type}-report.json',
            '--json-report'
        ])
        
        # Run pytest
        print(f"   🧪 Command: pytest {' '.join(args)}")
        
        try:
            result = pytest.main(args)
            
            # Parse results
            return self._parse_pytest_result(result, test_type)
            
        except Exception as e:
            print(f"   ❌ Error running {test_type} tests: {e}")
            return {'success': False, 'tests_run': 0, 'failures': 0, 'errors': 1, 'skipped': 0}
    
    def _parse_pytest_result(self, result_code: int, test_type: str) -> Dict:
        """Parse pytest result code and extract statistics."""
        # Pytest return codes:
        # 0: All tests passed
        # 1: Tests failed
        # 2: Test execution interrupted
        # 3: Internal error
        # 4: pytest command line usage error
        # 5: No tests collected
        
        success = result_code == 0
        
        # Try to read JSON report for detailed statistics
        json_report_path = self.reports_dir / f"{test_type}-report.json"
        stats = {'tests_run': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
        
        if json_report_path.exists():
            try:
                with open(json_report_path, 'r') as f:
                    report_data = json.load(f)
                
                if 'summary' in report_data:
                    summary = report_data['summary']
                    stats['tests_run'] = summary.get('num_tests', 0)
                    stats['failures'] = summary.get('failed', 0)
                    stats['errors'] = summary.get('error', 0)
                    stats['skipped'] = summary.get('skipped', 0)
                    
            except Exception as e:
                print(f"   ⚠️  Could not parse JSON report: {e}")
        
        return {
            'success': success,
            'tests_run': stats['tests_run'],
            'failures': stats['failures'],
            'errors': stats['errors'] + (1 if result_code in [2, 3] else 0),
            'skipped': stats['skipped']
        }
    
    def _generate_summary_report(self, results: Dict):
        """Generate a summary report."""
        report_path = self.reports_dir / "test-summary.md"
        
        with open(report_path, 'w') as f:
            f.write("# Test Summary Report\n\n")
            f.write(f"**Test Type:** {results['test_type']}\n")
            f.write(f"**Start Time:** {time.ctime(results['start_time'])}\n")
            f.write(f"**End Time:** {time.ctime(results['end_time'])}\n")
            f.write(f"**Duration:** {results['duration']:.2f} seconds\n\n")
            
            f.write("## Results\n\n")
            f.write(f"- **Tests Run:** {results['tests_run']}\n")
            f.write(f"- **Failures:** {results['failures']}\n")
            f.write(f"- **Errors:** {results['errors']}\n")
            f.write(f"- **Skipped:** {results['skipped']}\n")
            f.write(f"- **Success:** {'Yes' if results['success'] else 'No'}\n\n")
            
            if results['coverage']:
                f.write("## Coverage\n\n")
                f.write(f"- **Coverage:** {results['coverage']}%\n\n")
            
            f.write("## Reports\n\n")
            for report in results.get('reports', []):
                f.write(f"- [{report['name']}]({report['path']})\n")
        
        print(f"📄 Summary report saved to: {report_path}")
    
    def _print_results(self, results: Dict):
        """Print test results to console."""
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        print(f"Test Type: {results['test_type']}")
        print(f"Duration: {results['duration']:.2f} seconds")
        print(f"Tests Run: {results['tests_run']}")
        print(f"Failures: {results['failures']}")
        print(f"Errors: {results['errors']}")
        print(f"Skipped: {results['skipped']}")
        
        if results['success']:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        
        print("="*60)
    
    def run_performance_benchmarks(self) -> Dict:
        """Run performance benchmarks specifically."""
        print("⚡ Running performance benchmarks...")
        
        # Run benchmark script directly
        benchmark_script = self.tests_path / "performance" / "test_benchmarks.py"
        
        if benchmark_script.exists():
            try:
                result = subprocess.run([
                    sys.executable, str(benchmark_script)
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode == 0:
                    print("✅ Performance benchmarks completed successfully")
                    return {'success': True, 'output': result.stdout}
                else:
                    print("❌ Performance benchmarks failed")
                    print(result.stderr)
                    return {'success': False, 'error': result.stderr}
                    
            except Exception as e:
                print(f"❌ Error running benchmarks: {e}")
                return {'success': False, 'error': str(e)}
        else:
            print("⚠️  Benchmark script not found")
            return {'success': False, 'error': 'Benchmark script not found'}
    
    def generate_coverage_report(self):
        """Generate coverage reports."""
        print("📈 Generating coverage report...")
        
        try:
            # Run coverage
            subprocess.run([
                sys.executable, '-m', 'coverage', 'run', '-m', 'pytest', 
                str(self.tests_path / "unit")
            ], cwd=self.project_root, check=True)
            
            # Generate reports
            subprocess.run([
                sys.executable, '-m', 'coverage', 'html', 
                f'-d', str(self.coverage_dir / "html")
            ], cwd=self.project_root, check=True)
            
            subprocess.run([
                sys.executable, '-m', 'coverage', 'xml',
                '-o', str(self.reports_dir / "coverage.xml")
            ], cwd=self.project_root, check=True)
            
            # Get coverage percentage
            result = subprocess.run([
                sys.executable, '-m', 'coverage', 'report', '--format=json'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                coverage_data = json.loads(result.stdout)
                total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
                print(f"✅ Coverage report generated. Total coverage: {total_coverage:.1f}%")
                return {'success': True, 'coverage': total_coverage}
            else:
                print("❌ Could not get coverage percentage")
                return {'success': False}
                
        except Exception as e:
            print(f"❌ Error generating coverage report: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run plugin-adapter tests")
    
    parser.add_argument(
        '--type', '-t', 
        choices=['all', 'unit', 'integration', 'e2e', 'performance'],
        default='all',
        help='Type of tests to run'
    )
    
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Run with coverage reporting'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--parallel', '-p',
        action='store_true',
        help='Run tests in parallel'
    )
    
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate test report'
    )
    
    parser.add_argument(
        '--benchmarks',
        action='store_true',
        help='Run performance benchmarks'
    )
    
    args = parser.parse_args()
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    runner = TestRunner()
    
    # Handle special cases
    if args.benchmarks:
        results = runner.run_performance_benchmarks()
        sys.exit(0 if results['success'] else 1)
    
    # Run tests
    results = runner.run_tests(
        test_type=args.type,
        coverage=args.coverage,
        verbose=args.verbose,
        parallel=args.parallel
    )
    
    # Generate additional reports if requested
    if args.report:
        if args.coverage:
            runner.generate_coverage_report()
    
    # Exit with appropriate code
    sys.exit(0 if results['success'] else 1)


if __name__ == "__main__":
    main()