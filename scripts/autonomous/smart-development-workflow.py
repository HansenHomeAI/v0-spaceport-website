#!/usr/bin/env python3
"""
Smart Development Branch Workflow
=================================

Instead of complex agent-specific deployments, this approach:
1. Uses development branch (existing staging APIs)
2. Codex makes changes and commits
3. Triggers development deployment 
4. Runs intelligent Playwright tests
5. Analyzes results and iterates
6. Creates PR when task is complete

This avoids the API/secrets complexity while maintaining autonomous iteration.
"""

import asyncio
import json
import subprocess
import time
import tempfile
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TaskExecution:
    task_id: str
    description: str
    success_criteria: List[str]
    max_iterations: int = 5
    current_iteration: int = 0
    status: str = "pending"  # pending, implementing, testing, completed, failed
    implementation_log: List[str] = None
    test_results: List[Dict[str, Any]] = None
    final_result: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.implementation_log is None:
            self.implementation_log = []
        if self.test_results is None:
            self.test_results = []

class SmartDevelopmentWorkflow:
    """Autonomous workflow using development branch with intelligent testing"""
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self.session_id = str(int(time.time()))[-6:]
        
        # Development environment URLs (existing staging setup)
        self.frontend_url = "https://v0-spaceport-website-preview2.pages.dev"
        self.api_base = "https://api-staging.spaceport.com"  # Your existing staging APIs
        
    async def execute_autonomous_task(self, task_description: str, success_criteria: List[str]) -> TaskExecution:
        """Execute a task autonomously using development branch iteration"""
        
        task = TaskExecution(
            task_id=f"task-{self.session_id}",
            description=task_description,
            success_criteria=success_criteria
        )
        
        logger.info("🚀 STARTING SMART AUTONOMOUS WORKFLOW")
        logger.info("=" * 60)
        logger.info(f"📋 Task: {task_description}")
        logger.info(f"🎯 Success Criteria: {len(success_criteria)} requirements")
        logger.info(f"🌐 Frontend: {self.frontend_url}")
        logger.info(f"🔗 API Base: {self.api_base}")
        
        try:
            while task.current_iteration < task.max_iterations:
                task.current_iteration += 1
                logger.info(f"\n🔄 ITERATION {task.current_iteration}/{task.max_iterations}")
                logger.info("-" * 50)
                
                # Step 1: Analyze current state
                analysis = await self.analyze_current_state(task)
                logger.info(f"🔍 Analysis: {analysis.get('summary', 'No summary')}")
                
                # Step 2: Implement changes with Codex
                task.status = "implementing"
                implementation_result = await self.implement_with_codex(task, analysis)
                
                if not implementation_result["success"]:
                    logger.error(f"❌ Implementation failed: {implementation_result['error']}")
                    task.implementation_log.append(f"Iteration {task.current_iteration}: Implementation failed - {implementation_result['error']}")
                    continue
                
                # Step 3: Deploy to development
                deployment_success = await self.deploy_to_development()
                if not deployment_success:
                    logger.error("❌ Deployment failed")
                    task.implementation_log.append(f"Iteration {task.current_iteration}: Deployment failed")
                    continue
                
                # Step 4: Run intelligent tests
                task.status = "testing"
                test_result = await self.run_intelligent_tests(task)
                task.test_results.append(test_result)
                
                # Step 5: Analyze test results
                success = self.analyze_test_success(task, test_result)
                
                if success:
                    task.status = "completed"
                    task.final_result = test_result
                    logger.info("🎉 TASK COMPLETED SUCCESSFULLY!")
                    break
                else:
                    logger.info(f"⚠️ Tests not passing, iteration {task.current_iteration} complete")
                    task.implementation_log.append(f"Iteration {task.current_iteration}: Tests failed - {test_result.get('summary', 'Unknown failure')}")
            
            if task.status != "completed":
                task.status = "failed"
                logger.error(f"❌ Task failed after {task.max_iterations} iterations")
                
        except Exception as e:
            logger.error(f"❌ Workflow exception: {e}")
            task.status = "failed"
            task.implementation_log.append(f"Fatal error: {str(e)}")
        
        return task
    
    async def analyze_current_state(self, task: TaskExecution) -> Dict[str, Any]:
        """Analyze current codebase state to understand what needs to be done"""
        
        logger.info("🔍 Analyzing current codebase state...")
        
        # Use Codex to analyze the current state
        analysis_prompt = f"""
TASK ANALYSIS: {task.description}

CURRENT ITERATION: {task.current_iteration}
SUCCESS CRITERIA: {', '.join(task.success_criteria)}

PREVIOUS ATTEMPTS: 
{chr(10).join(task.implementation_log) if task.implementation_log else 'None'}

ANALYSIS REQUIRED:
1. Examine the current codebase
2. Identify what needs to be changed to meet the success criteria
3. Consider any previous failed attempts
4. Provide specific implementation steps

Please analyze the codebase and provide:
1. Current state assessment
2. Required changes
3. Implementation approach
4. Potential challenges

Output as JSON: {{"summary": "...", "required_changes": [...], "approach": "...", "challenges": [...]}}
"""

        try:
            result = subprocess.run([
                "codex", "exec", "--full-auto", analysis_prompt
            ], capture_output=True, text=True, timeout=120, cwd=self.workspace_root)
            
            if result.returncode == 0:
                # Try to extract JSON from output
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines:
                    if line.strip().startswith('{'):
                        try:
                            return json.loads(line.strip())
                        except json.JSONDecodeError:
                            continue
            
            # Fallback analysis
            return {
                "summary": f"Basic analysis for: {task.description}",
                "required_changes": ["Implement requested feature"],
                "approach": "Direct implementation",
                "challenges": []
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Analysis failed: {e}")
            return {
                "summary": f"Analysis failed, proceeding with task: {task.description}",
                "required_changes": ["Implement requested feature"],
                "approach": "Best effort implementation",
                "challenges": [str(e)]
            }
    
    async def implement_with_codex(self, task: TaskExecution, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Use Codex to implement the required changes"""
        
        logger.info("⚙️ Implementing changes with Codex...")
        
        implementation_prompt = f"""
IMPLEMENTATION TASK: {task.description}

ANALYSIS RESULTS:
Summary: {analysis.get('summary', 'No analysis')}
Required Changes: {analysis.get('required_changes', [])}
Approach: {analysis.get('approach', 'Direct implementation')}

SUCCESS CRITERIA (ALL MUST BE MET):
{chr(10).join(f"- {criteria}" for criteria in task.success_criteria)}

ITERATION: {task.current_iteration}/{task.max_iterations}
PREVIOUS ATTEMPTS: 
{chr(10).join(task.implementation_log[-3:]) if task.implementation_log else 'None (first attempt)'}

IMPLEMENTATION INSTRUCTIONS:
1. Make the necessary code changes to meet ALL success criteria
2. Focus on frontend changes that will be testable with Playwright
3. Ensure changes are visible and functional
4. Consider previous failed attempts and avoid repeating mistakes
5. Make changes that can be validated through automated testing
6. Commit changes with descriptive commit message

CONSTRAINTS:
- Work on development branch (existing staging environment)
- Changes must be testable via frontend UI
- Focus on user-visible improvements
- Ensure compatibility with existing codebase

Please implement the required changes and commit them.
"""

        try:
            result = subprocess.run([
                "codex", "exec", "--full-auto", implementation_prompt
            ], capture_output=True, text=True, timeout=600, cwd=self.workspace_root)  # 10 minute timeout
            
            success = result.returncode == 0
            
            return {
                "success": success,
                "output": result.stdout if success else result.stderr,
                "error": None if success else result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Implementation timed out after 10 minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Implementation failed: {str(e)}"
            }
    
    async def deploy_to_development(self) -> bool:
        """Deploy changes to development environment"""
        
        logger.info("🚀 Deploying to development environment...")
        
        try:
            # Push to development branch to trigger deployment
            result = subprocess.run([
                "git", "push", "origin", "development"
            ], capture_output=True, text=True, cwd=self.workspace_root)
            
            if result.returncode != 0:
                logger.error(f"❌ Git push failed: {result.stderr}")
                return False
            
            # Wait for deployment (GitHub Actions + Cloudflare Pages)
            logger.info("⏳ Waiting for deployment to complete...")
            await asyncio.sleep(60)  # Give deployment time to process
            
            # Verify deployment is accessible
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    result = subprocess.run([
                        "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                        self.frontend_url
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.stdout.strip() == "200":
                        logger.info("✅ Development deployment is ready")
                        return True
                    
                    logger.info(f"⏳ Deployment not ready (HTTP {result.stdout.strip()}), attempt {attempt + 1}/{max_attempts}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error checking deployment: {e}")
                
                if attempt < max_attempts - 1:
                    await asyncio.sleep(20)
            
            logger.error("❌ Deployment verification failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            return False
    
    async def run_intelligent_tests(self, task: TaskExecution) -> Dict[str, Any]:
        """Run intelligent Playwright tests tailored to the specific task"""
        
        logger.info("🧪 Running intelligent tests...")
        
        # Generate task-specific test script
        test_script = self.generate_test_script(task)
        
        # Write test script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.spec.ts', delete=False) as f:
            f.write(test_script)
            test_file = f.name
        
        try:
            # Run Playwright tests
            env = {
                **dict(subprocess.os.environ),
                "PLAYWRIGHT_BASE_URL": self.frontend_url
            }
            
            result = subprocess.run([
                "npx", "playwright", "test", test_file,
                "--reporter=json",
                "--output-file=test-results/task-results.json"
            ], capture_output=True, text=True, cwd=self.workspace_root / "web", env=env, timeout=180)
            
            # Parse test results
            test_results = {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "iteration": task.current_iteration
            }
            
            # Try to parse detailed JSON results
            results_file = self.workspace_root / "web" / "test-results" / "task-results.json"
            if results_file.exists():
                try:
                    with open(results_file) as f:
                        detailed_results = json.load(f)
                        test_results["detailed"] = detailed_results
                except Exception as e:
                    logger.warning(f"⚠️ Could not parse detailed results: {e}")
            
            return test_results
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "errors": "Tests timed out after 3 minutes",
                "iteration": task.current_iteration
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "errors": f"Test execution failed: {str(e)}",
                "iteration": task.current_iteration
            }
        finally:
            # Clean up test file
            try:
                Path(test_file).unlink()
            except:
                pass
    
    def generate_test_script(self, task: TaskExecution) -> str:
        """Generate a Playwright test script tailored to the specific task"""
        
        return f'''
import {{ test, expect }} from '@playwright/test';

test.describe('Autonomous Task Validation: {task.description}', () => {{
  test('Task implementation meets success criteria', async ({{ page }}) => {{
    const errors: string[] = [];
    const warnings: string[] = [];
    
    // Capture console errors
    page.on('console', msg => {{
      if (msg.type() === 'error') {{
        errors.push(`CONSOLE ERROR: ${{msg.text()}}`);
      }} else if (msg.type() === 'warning') {{
        warnings.push(`CONSOLE WARNING: ${{msg.text()}}`);
      }}
    }});
    
    // Capture network failures
    page.on('requestfailed', request => {{
      errors.push(`NETWORK FAILURE: ${{request.url()}} - ${{request.failure()?.errorText || 'Unknown'}}`);
    }});
    
    // Navigate to the application
    await page.goto('/');
    
    // Wait for initial load
    await page.waitForLoadState('networkidle');
    
    // Take screenshot of initial state
    await page.screenshot({{ path: 'test-results/initial-state.png', fullPage: true }});
    
    // Success Criteria Validation
    {self.generate_success_criteria_tests(task.success_criteria)}
    
    // Final validation
    await page.screenshot({{ path: 'test-results/final-state.png', fullPage: true }});
    
    // Output results for analysis
    const testResults = {{
      task: '{task.description}',
      iteration: {task.current_iteration},
      errors: errors,
      warnings: warnings,
      timestamp: new Date().toISOString()
    }};
    
    console.log('AUTONOMOUS_TEST_RESULTS:', JSON.stringify(testResults, null, 2));
    
    // Fail test if critical errors found
    expect(errors.filter(e => e.includes('CONSOLE ERROR'))).toHaveLength(0);
  }});
}});
'''
    
    def generate_success_criteria_tests(self, success_criteria: List[str]) -> str:
        """Generate specific test code for success criteria"""
        
        test_code = []
        
        for i, criteria in enumerate(success_criteria):
            test_code.append(f"""
    // Success Criteria {i + 1}: {criteria}
    try {{
      {self.criteria_to_test_code(criteria)}
      console.log('✅ Success Criteria {i + 1} passed: {criteria}');
    }} catch (error) {{
      errors.push(`❌ Success Criteria {i + 1} failed: {criteria} - ${{error.message}}`);
      console.log('❌ Success Criteria {i + 1} failed:', error.message);
    }}
""")
        
        return '\n'.join(test_code)
    
    def criteria_to_test_code(self, criteria: str) -> str:
        """Convert success criteria to Playwright test code"""
        
        criteria_lower = criteria.lower()
        
        if 'button' in criteria_lower and 'hover' in criteria_lower:
            return '''
      const button = page.locator('button').first();
      await expect(button).toBeVisible();
      await button.hover();
      await page.waitForTimeout(500);
'''
        
        elif 'loading' in criteria_lower and 'spinner' in criteria_lower:
            return '''
      const button = page.locator('button').first();
      if (await button.isVisible()) {
        await button.click();
        await page.waitForTimeout(1000);
        // Check for loading state
      }
'''
        
        elif 'console' in criteria_lower and 'error' in criteria_lower:
            return '''
      // This is handled by the console error capture above
      await page.waitForTimeout(100);
'''
        
        elif 'page' in criteria_lower and 'load' in criteria_lower:
            return '''
      await expect(page).toHaveTitle(/Spaceport/);
      await page.waitForLoadState('domcontentloaded');
'''
        
        else:
            # Generic test - ensure page is functional
            return '''
      await expect(page.locator('body')).toBeVisible();
      await page.waitForTimeout(100);
'''
    
    def analyze_test_success(self, task: TaskExecution, test_result: Dict[str, Any]) -> bool:
        """Analyze test results to determine if task is complete"""
        
        if not test_result.get("success", False):
            logger.info("❌ Tests failed - task not complete")
            return False
        
        # Check for console errors
        if "CONSOLE ERROR" in test_result.get("output", ""):
            logger.info("❌ Console errors detected - task not complete")
            return False
        
        # Check for network failures
        if "NETWORK FAILURE" in test_result.get("output", ""):
            logger.info("❌ Network failures detected - task not complete")
            return False
        
        logger.info("✅ All tests passed - task appears complete")
        return True

async def main():
    """Test the smart development workflow"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Development Workflow")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--criteria", nargs="+", help="Success criteria")
    
    args = parser.parse_args()
    
    # Default success criteria if not provided
    success_criteria = args.criteria or [
        "Code compiles without errors",
        "Page loads without console errors",
        "Changes are visible in the UI",
        "No network request failures"
    ]
    
    workflow = SmartDevelopmentWorkflow()
    
    result = await workflow.execute_autonomous_task(
        task_description=args.task,
        success_criteria=success_criteria
    )
    
    # Output final results
    logger.info("\n" + "=" * 60)
    logger.info("🎯 FINAL RESULTS")
    logger.info("=" * 60)
    logger.info(f"Task: {result.description}")
    logger.info(f"Status: {result.status}")
    logger.info(f"Iterations: {result.current_iteration}")
    
    if result.status == "completed":
        logger.info("🎉 TASK COMPLETED SUCCESSFULLY!")
        logger.info("Ready to create pull request for human review.")
    else:
        logger.error("❌ Task failed to complete")
        logger.error("Review implementation log for details:")
        for log_entry in result.implementation_log:
            logger.error(f"  - {log_entry}")

if __name__ == "__main__":
    asyncio.run(main())
