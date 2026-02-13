#!/usr/bin/env python3
"""
🚀 Spaceport - Complete Beta Readiness Test Runner

This script runs all beta readiness tests in the correct order and provides
a comprehensive assessment of your system's readiness for early beta testing.

Test Suites Included:
1. Beta Readiness Comprehensive Test
2. Multi-User Concurrency Test  
3. Production Monitoring Test

Usage:
    python tests/run_beta_readiness_suite.py [--quick] [--verbose]
    
    --quick:   Run essential tests only (faster execution)
    --verbose: Show detailed output for all tests
"""

import sys
import os
import time
import argparse
import subprocess
from datetime import datetime
from typing import Dict, Any, List

# Add the tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class BetaReadinessRunner:
    """Orchestrates all beta readiness tests"""
    
    def __init__(self, quick_mode: bool = False, verbose: bool = False):
        """Initialize test runner"""
        
        self.quick_mode = quick_mode
        self.verbose = verbose
        self.start_time = time.time()
        
        # Test results
        self.test_suites = {}
        self.overall_results = {
            'suites_passed': 0,
            'suites_failed': 0,
            'total_tests_passed': 0,
            'total_tests_failed': 0,
            'critical_failures': [],
            'warnings': []
        }
        
        print(f"{Colors.BOLD}{Colors.CYAN}🚀 SPACEPORT AI - BETA READINESS TEST SUITE{Colors.END}")
        print(f"{Colors.WHITE}Comprehensive testing for early beta launch readiness{Colors.END}")
        print(f"{Colors.WHITE}{'='*70}{Colors.END}")

        preview_url = os.getenv("BETA_READINESS_PREVIEW_URL") or os.getenv("PREVIEW_URL")
        if preview_url:
            print(f"{Colors.WHITE}Preview URL detected: {preview_url}{Colors.END}")
        
        if quick_mode:
            print(f"{Colors.YELLOW}⚡ Quick mode enabled - running essential tests only{Colors.END}")
        
        print(f"{Colors.BLUE}🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}\n")

    def run_test_suite(self, suite_name: str, test_module: str, critical: bool = True) -> Dict[str, Any]:
        """Run a specific test suite and capture results"""
        
        print(f"{Colors.BOLD}📋 Running {suite_name}...{Colors.END}")
        print(f"{Colors.WHITE}{'─'*50}{Colors.END}")
        
        suite_start = time.time()
        
        try:
            # Import and run the test module
            if test_module == 'beta_readiness_comprehensive_test':
                from beta_readiness_comprehensive_test import BetaReadinessTestSuite
                test_suite = BetaReadinessTestSuite()
                success = test_suite.run_all_tests()
                results = test_suite.test_results
                
            elif test_module == 'multi_user_concurrency_test':
                from multi_user_concurrency_test import MultiUserConcurrencyTest
                test_suite = MultiUserConcurrencyTest()
                success = test_suite.run_all_tests()
                results = test_suite.results
                
            elif test_module == 'production_monitoring_test':
                from production_monitoring_test import ProductionMonitoringTest
                test_suite = ProductionMonitoringTest()
                success = test_suite.run_all_tests()
                results = test_suite.results
                
            else:
                raise ValueError(f"Unknown test module: {test_module}")
                
            suite_end = time.time()
            duration = suite_end - suite_start
            
            # Calculate success metrics
            total_tests = results.get('passed', 0) + results.get('failed', 0)
            success_rate = (results.get('passed', 0) / total_tests) * 100 if total_tests > 0 else 0
            
            suite_result = {
                'name': suite_name,
                'success': success,
                'duration': duration,
                'tests_passed': results.get('passed', 0),
                'tests_failed': results.get('failed', 0),
                'warnings': results.get('warnings', 0),
                'success_rate': success_rate,
                'critical': critical,
                'details': results.get('details', [])
            }
            
            # Update overall results
            if success:
                self.overall_results['suites_passed'] += 1
                status_icon = f"{Colors.GREEN}✅{Colors.END}"
            else:
                self.overall_results['suites_failed'] += 1
                status_icon = f"{Colors.RED}❌{Colors.END}"
                if critical:
                    self.overall_results['critical_failures'].append(suite_name)
            
            self.overall_results['total_tests_passed'] += results.get('passed', 0)
            self.overall_results['total_tests_failed'] += results.get('failed', 0)
            
            # Display suite results
            print(f"\n{status_icon} {suite_name} - {Colors.BOLD}{success_rate:.1f}% success rate{Colors.END}")
            print(f"   Duration: {duration:.1f}s | Passed: {results.get('passed', 0)} | Failed: {results.get('failed', 0)}")
            
            if results.get('warnings', 0) > 0:
                print(f"   {Colors.YELLOW}⚠️  Warnings: {results.get('warnings', 0)}{Colors.END}")
                self.overall_results['warnings'].append(f"{suite_name}: {results.get('warnings', 0)} warnings")
                
            return suite_result
            
        except Exception as e:
            suite_end = time.time()
            duration = suite_end - suite_start
            
            print(f"{Colors.RED}❌ {suite_name} - FAILED TO RUN{Colors.END}")
            print(f"   Error: {str(e)}")
            
            self.overall_results['suites_failed'] += 1
            if critical:
                self.overall_results['critical_failures'].append(f"{suite_name} (execution error)")
            
            return {
                'name': suite_name,
                'success': False,
                'duration': duration,
                'tests_passed': 0,
                'tests_failed': 1,
                'success_rate': 0,
                'critical': critical,
                'error': str(e)
            }

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        
        print(f"{Colors.BOLD}🔍 Checking Prerequisites...{Colors.END}")
        
        prerequisites_met = True
        
        # Check Python packages
        required_packages = ['boto3', 'requests']
        for package in required_packages:
            try:
                __import__(package)
                print(f"   ✅ {package} installed")
            except ImportError:
                print(f"   ❌ {package} not installed")
                prerequisites_met = False
        
        # Check AWS credentials
        try:
            import boto3
            sts = boto3.client('sts')
            sts.get_caller_identity()
            print(f"   ✅ AWS credentials configured")
        except Exception as e:
            print(f"   ❌ AWS credentials not configured: {e}")
            prerequisites_met = False
        
        # Check internet connectivity
        try:
            import requests
            response = requests.get('https://aws.amazon.com', timeout=5)
            if response.status_code == 200:
                print(f"   ✅ Internet connectivity confirmed")
            else:
                print(f"   ⚠️  Internet connectivity issues")
                prerequisites_met = False
        except Exception:
            print(f"   ❌ No internet connectivity")
            prerequisites_met = False
        
        if not prerequisites_met:
            print(f"\n{Colors.RED}❌ Prerequisites not met. Please install required packages and configure AWS credentials.{Colors.END}")
            return False
            
        print(f"   {Colors.GREEN}✅ All prerequisites met{Colors.END}\n")
        return True

    def run_all_tests(self):
        """Run all test suites in the appropriate order"""
        
        if not self.check_prerequisites():
            return False
        
        print(f"{Colors.BOLD}🧪 Running Test Suites{Colors.END}")
        print(f"{Colors.WHITE}{'='*70}{Colors.END}\n")
        
        # Define test suites to run
        test_suites = [
            {
                'name': 'Production Monitoring Test',
                'module': 'production_monitoring_test',
                'critical': False,  # Non-critical for beta
                'skip_quick': False
            },
            {
                'name': 'Beta Readiness Comprehensive Test',
                'module': 'beta_readiness_comprehensive_test',
                'critical': True,
                'skip_quick': False
            },
            {
                'name': 'Multi-User Concurrency Test',
                'module': 'multi_user_concurrency_test',
                'critical': True,
                'skip_quick': False
            }
        ]
        
        # Run test suites
        for suite_config in test_suites:
            if self.quick_mode and suite_config.get('skip_quick', False):
                print(f"{Colors.YELLOW}⏭️  Skipping {suite_config['name']} (quick mode){Colors.END}\n")
                continue
                
            suite_result = self.run_test_suite(
                suite_config['name'],
                suite_config['module'],
                suite_config['critical']
            )
            
            self.test_suites[suite_config['name']] = suite_result
            print()  # Add spacing between suites
        
        return self.generate_final_report()

    def generate_final_report(self) -> bool:
        """Generate final beta readiness report"""
        
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        print(f"{Colors.BOLD}{Colors.CYAN}📊 FINAL BETA READINESS REPORT{Colors.END}")
        print(f"{Colors.WHITE}{'='*70}{Colors.END}")
        
        # Overall Statistics
        total_suites = self.overall_results['suites_passed'] + self.overall_results['suites_failed']
        suite_success_rate = (self.overall_results['suites_passed'] / total_suites) * 100 if total_suites > 0 else 0
        
        total_tests = self.overall_results['total_tests_passed'] + self.overall_results['total_tests_failed']
        test_success_rate = (self.overall_results['total_tests_passed'] / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"{Colors.WHITE}📈 Overall Statistics:{Colors.END}")
        print(f"   Test Suites: {self.overall_results['suites_passed']}/{total_suites} passed ({suite_success_rate:.1f}%)")
        print(f"   Individual Tests: {self.overall_results['total_tests_passed']}/{total_tests} passed ({test_success_rate:.1f}%)")
        print(f"   Total Duration: {total_duration:.1f} seconds")
        print(f"   Test Mode: {'Quick' if self.quick_mode else 'Comprehensive'}")
        
        # Suite Results Summary
        print(f"\n{Colors.WHITE}📋 Test Suite Results:{Colors.END}")
        for suite_name, result in self.test_suites.items():
            icon = "✅" if result['success'] else "❌"
            critical_tag = " (CRITICAL)" if result['critical'] else ""
            print(f"   {icon} {suite_name}{critical_tag}: {result['success_rate']:.1f}% ({result['duration']:.1f}s)")
        
        # Critical Failures
        if self.overall_results['critical_failures']:
            print(f"\n{Colors.RED}🚨 Critical Failures:{Colors.END}")
            for failure in self.overall_results['critical_failures']:
                print(f"   ❌ {failure}")
        
        # Warnings
        if self.overall_results['warnings']:
            print(f"\n{Colors.YELLOW}⚠️  Warnings:{Colors.END}")
            for warning in self.overall_results['warnings']:
                print(f"   ⚠️  {warning}")
        
        # Beta Readiness Assessment
        print(f"\n{Colors.BOLD}🎯 BETA READINESS ASSESSMENT{Colors.END}")
        print(f"{Colors.WHITE}{'='*70}{Colors.END}")
        
        ready_for_beta = False
        
        if len(self.overall_results['critical_failures']) == 0 and test_success_rate >= 85:
            print(f"{Colors.GREEN}🟢 READY FOR BETA LAUNCH{Colors.END}")
            print(f"{Colors.GREEN}   ✅ No critical failures detected{Colors.END}")
            print(f"{Colors.GREEN}   ✅ {test_success_rate:.1f}% overall success rate{Colors.END}")
            print(f"{Colors.GREEN}   ✅ Core functionality is stable{Colors.END}")
            print(f"{Colors.GREEN}   ✅ Multi-user support is working{Colors.END}")
            ready_for_beta = True
            
        elif len(self.overall_results['critical_failures']) == 0 and test_success_rate >= 70:
            print(f"{Colors.YELLOW}🟡 MOSTLY READY - PROCEED WITH CAUTION{Colors.END}")
            print(f"{Colors.YELLOW}   ✅ No critical failures{Colors.END}")
            print(f"{Colors.YELLOW}   ⚠️  {test_success_rate:.1f}% success rate (consider improvements){Colors.END}")
            print(f"{Colors.YELLOW}   ⚠️  Start with limited beta users{Colors.END}")
            ready_for_beta = True
            
        else:
            print(f"{Colors.RED}🔴 NOT READY FOR BETA LAUNCH{Colors.END}")
            print(f"{Colors.RED}   ❌ Critical failures detected{Colors.END}")
            print(f"{Colors.RED}   ❌ {test_success_rate:.1f}% success rate (too low){Colors.END}")
            print(f"{Colors.RED}   ❌ Resolve issues before launch{Colors.END}")
        
        # Recommendations
        print(f"\n{Colors.BOLD}💡 RECOMMENDATIONS{Colors.END}")
        print(f"{Colors.WHITE}{'='*70}{Colors.END}")
        
        if ready_for_beta:
            print(f"{Colors.WHITE}🚀 Launch Recommendations:{Colors.END}")
            print(f"   1. Start with 5-10 trusted beta testers")
            print(f"   2. Monitor CloudWatch logs closely during first week")
            print(f"   3. Set up real-time alerts for errors")
            print(f"   4. Have a rollback plan ready")
            print(f"   5. Schedule daily check-ins during first week")
            print(f"   6. Collect user feedback actively")
            
            if self.overall_results['warnings']:
                print(f"\n{Colors.YELLOW}   ⚠️  Address warnings when possible{Colors.END}")
                
        else:
            print(f"{Colors.RED}🔧 Fix These Issues Before Launch:{Colors.END}")
            for failure in self.overall_results['critical_failures']:
                print(f"   ❌ {failure}")
            
            print(f"\n{Colors.WHITE}   Then re-run this test suite to verify fixes{Colors.END}")
        
        # Next Steps
        print(f"\n{Colors.BOLD}📋 NEXT STEPS{Colors.END}")
        print(f"{Colors.WHITE}{'='*70}{Colors.END}")
        
        if ready_for_beta:
            print(f"1. {Colors.GREEN}✅ Begin beta user invitations{Colors.END}")
            print(f"2. 📧 Send beta testing guidelines to users")
            print(f"3. 📊 Set up monitoring dashboards")
            print(f"4. 📝 Prepare feedback collection system")
            print(f"5. 🔄 Plan for iterative improvements")
        else:
            print(f"1. {Colors.RED}🔧 Fix critical failures listed above{Colors.END}")
            print(f"2. 🧪 Re-run tests: python tests/run_beta_readiness_suite.py")
            print(f"3. 📚 Review documentation for troubleshooting")
            print(f"4. 💬 Consider consulting with team if issues persist")
        
        print(f"\n{Colors.BOLD}🎉 Beta readiness testing completed!{Colors.END}")
        print(f"{Colors.WHITE}Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        
        return ready_for_beta

def main():
    """Main execution function"""
    
    parser = argparse.ArgumentParser(description='Run Spaceport Beta Readiness Test Suite')
    parser.add_argument('--quick', action='store_true', help='Run essential tests only')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    runner = BetaReadinessRunner(quick_mode=args.quick, verbose=args.verbose)
    ready_for_beta = runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if ready_for_beta else 1)

if __name__ == "__main__":
    main()
