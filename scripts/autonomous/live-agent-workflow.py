#!/usr/bin/env python3
"""
Live Agent Workflow - No Timeouts, Real-Time Codex Output
========================================================

FEATURES:
✅ NO TIMEOUTS - Let Codex work for hours if needed
✅ LIVE OUTPUT - See Codex thinking and working in real-time
✅ COMPLEX TASKS - Handle multi-component implementations
✅ ISOLATED BRANCHES - Each agent gets unique deployment URL
✅ DEVELOPMENT SECRETS - Reuse existing staging configuration

This workflow is designed for complex, long-running tasks.
"""

import asyncio
import subprocess
import time
import logging
import uuid
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# Configure logging for live output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class LiveAgentTask:
    task_id: str
    description: str
    success_criteria: List[str]
    branch_name: str = ""
    deployment_url: str = ""
    max_iterations: int = 5  # More iterations for complex tasks
    current_iteration: int = 0
    status: str = "pending"
    logs: List[str] = field(default_factory=list)

class LiveAgentWorkflow:
    """Live autonomous workflow with no timeouts and real-time Codex visibility"""
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self.session_id = str(uuid.uuid4())[:8]
        
    async def execute_task(self, task_description: str, success_criteria: List[str]) -> LiveAgentTask:
        """Execute task with live Codex output and no timeouts"""
        
        task = LiveAgentTask(
            task_id=f"task-{self.session_id}",
            description=task_description,
            success_criteria=success_criteria,
            branch_name=f"agent-{self.session_id}",
            deployment_url=f"https://agent-{self.session_id}.v0-spaceport-website-preview2.pages.dev"
        )
        
        print("\n" + "="*80)
        print("🚀 LIVE AGENT WORKFLOW - NO TIMEOUTS")
        print("="*80)
        print(f"📋 Task: {task_description}")
        print(f"🌿 Branch: {task.branch_name}")
        print(f"🌐 URL: {task.deployment_url}")
        print(f"⏰ No timeouts - Codex can work as long as needed")
        print(f"👁️  Live output - You'll see Codex thinking in real-time")
        print("="*80 + "\n")
        
        try:
            # Create agent branch
            if not await self.create_agent_branch(task):
                task.status = "failed"
                return task
            
            # Execute iterations with no timeout limits
            while task.current_iteration < task.max_iterations:
                task.current_iteration += 1
                print(f"\n🔄 ITERATION {task.current_iteration}/{task.max_iterations}")
                print("-" * 60)
                
                # Implement with live Codex output
                if not await self.implement_with_live_codex(task):
                    print(f"⚠️ Iteration {task.current_iteration} failed, trying again...")
                    continue
                
                # Build validation (also no timeout)
                if not await self.validate_build_live(task):
                    print(f"⚠️ Build failed in iteration {task.current_iteration}, trying again...")
                    continue
                
                # Deploy and verify
                if await self.deploy_and_verify(task):
                    task.status = "completed"
                    print("\n🎉 TASK COMPLETED SUCCESSFULLY!")
                    print(f"🌐 Live at: {task.deployment_url}")
                    break
                else:
                    print(f"⚠️ Deployment failed in iteration {task.current_iteration}")
            
            if task.status != "completed":
                task.status = "failed"
                print(f"\n❌ Task failed after {task.max_iterations} iterations")
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Task interrupted by user")
            task.status = "interrupted"
        except Exception as e:
            print(f"\n❌ Workflow exception: {e}")
            task.status = "failed"
        
        return task
    
    async def create_agent_branch(self, task: LiveAgentTask) -> bool:
        """Create agent branch with live feedback"""
        print(f"🌿 Creating agent branch: {task.branch_name}")
        
        try:
            # Show git operations
            print("   📥 Checking out development...")
            subprocess.run(["git", "checkout", "development"], check=True, cwd=self.workspace_root)
            
            print("   🔄 Pulling latest changes...")
            subprocess.run(["git", "pull", "origin", "development"], check=True, cwd=self.workspace_root)
            
            print(f"   🌿 Creating branch {task.branch_name}...")
            subprocess.run(["git", "checkout", "-b", task.branch_name], check=True, cwd=self.workspace_root)
            
            print("✅ Agent branch created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Branch creation failed: {e}")
            return False
    
    async def implement_with_live_codex(self, task: LiveAgentTask) -> bool:
        """Run Codex with live, streaming output and NO TIMEOUT"""
        
        print("⚙️ Starting Codex implementation...")
        print("👁️  LIVE CODEX OUTPUT (no timeout - let it work as long as needed):")
        print("-" * 60)
        
        prompt = f"""
COMPLEX TASK IMPLEMENTATION: {task.description}

SUCCESS CRITERIA (ALL MUST BE MET):
{chr(10).join(f"- {criteria}" for criteria in task.success_criteria)}

DEPLOYMENT INFO:
- Branch: {task.branch_name}
- Will deploy to: {task.deployment_url}
- Use existing staging/development secrets and APIs

IMPLEMENTATION REQUIREMENTS:
1. Analyze what needs to be changed across the full stack
2. Make all necessary changes (frontend, backend, infrastructure)
3. Ensure proper error handling and user feedback
4. Test locally if possible
5. Commit all changes with clear messages
6. Take as much time as needed - no rush!

AVAILABLE TECHNOLOGIES:
- Frontend: Next.js, React, TypeScript
- Backend: AWS Lambda, API Gateway
- Infrastructure: AWS CDK (Python)
- Email: Resend API
- Database: DynamoDB (if needed)

Please implement the complete solution step by step.
Take your time and be thorough.
"""

        try:
            # Run Codex with live streaming output and NO TIMEOUT
            print("🤖 Codex is now working on your task...")
            print("📝 Live output:")
            
            process = subprocess.Popen([
                "codex", "exec", "--full-auto", prompt
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
               text=True, cwd=self.workspace_root, bufsize=1, universal_newlines=True)
            
            # Stream output in real-time
            output_lines = []
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # Print live output with timestamp
                    timestamp = time.strftime("%H:%M:%S")
                    line = output.rstrip()
                    print(f"[{timestamp}] 🤖 {line}")
                    output_lines.append(line)
                    sys.stdout.flush()  # Ensure immediate output
            
            # Wait for process to complete (no timeout!)
            return_code = process.wait()
            
            print(f"\n⚙️ Codex completed with return code: {return_code}")
            
            if return_code == 0:
                print("✅ Implementation completed successfully")
                task.logs.append(f"Iteration {task.current_iteration}: Success")
                return True
            else:
                print("❌ Implementation failed")
                task.logs.append(f"Iteration {task.current_iteration}: Failed")
                return False
                
        except Exception as e:
            print(f"❌ Implementation exception: {e}")
            task.logs.append(f"Iteration {task.current_iteration}: Exception - {str(e)}")
            return False
    
    async def validate_build_live(self, task: LiveAgentTask) -> bool:
        """Validate build with live output and NO TIMEOUT"""
        
        print("\n🔨 Validating build...")
        print("📝 Build output:")
        
        try:
            # Run build with live output and NO TIMEOUT
            process = subprocess.Popen([
                "npm", "run", "build"
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
               text=True, cwd=self.workspace_root / "web", bufsize=1, universal_newlines=True)
            
            # Stream build output
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    timestamp = time.strftime("%H:%M:%S")
                    line = output.rstrip()
                    print(f"[{timestamp}] 🔨 {line}")
                    sys.stdout.flush()
            
            return_code = process.wait()
            
            if return_code == 0:
                print("✅ Build successful")
                return True
            else:
                print("❌ Build failed")
                return False
                
        except Exception as e:
            print(f"❌ Build validation failed: {e}")
            return False
    
    async def deploy_and_verify(self, task: LiveAgentTask) -> bool:
        """Deploy and verify with live monitoring"""
        
        print("\n🚀 Deploying to agent branch...")
        
        try:
            # Push to trigger deployment
            print("   📤 Pushing to GitHub...")
            result = subprocess.run([
                "git", "push", "origin", task.branch_name
            ], capture_output=True, text=True, cwd=self.workspace_root)
            
            if result.returncode != 0:
                print(f"❌ Git push failed: {result.stderr}")
                return False
            
            print("✅ Pushed successfully - GitHub Actions will deploy")
            print(f"⏳ Waiting for deployment at: {task.deployment_url}")
            
            # Wait for deployment with live updates
            max_wait = 600  # 10 minutes max for deployment
            check_interval = 15
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                try:
                    result = subprocess.run([
                        "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                        task.deployment_url
                    ], capture_output=True, text=True, timeout=10)
                    
                    status_code = result.stdout.strip()
                    elapsed = int(time.time() - start_time)
                    
                    if status_code == "200":
                        print(f"✅ Deployment ready! ({elapsed}s)")
                        print(f"🌐 Live at: {task.deployment_url}")
                        return True
                    elif status_code in ["404", "000"]:
                        print(f"⏳ [{elapsed}s] Deployment not ready ({status_code}), waiting...")
                    else:
                        print(f"⚠️ [{elapsed}s] Status: {status_code}")
                    
                except Exception as e:
                    print(f"⚠️ Error checking deployment: {e}")
                
                await asyncio.sleep(check_interval)
            
            print(f"❌ Deployment timeout after {max_wait}s")
            return False
            
        except Exception as e:
            print(f"❌ Deploy and verify failed: {e}")
            return False

async def main():
    """Run the live agent workflow"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Live Agent Workflow (No Timeouts)")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--criteria", nargs="+", help="Success criteria")
    
    args = parser.parse_args()
    
    # Default success criteria
    success_criteria = args.criteria or [
        "Implementation works as described",
        "Code builds without errors",
        "Changes are visible and functional",
        "No console errors",
        "Maintains existing functionality"
    ]
    
    print("\n🎯 LIVE AUTONOMOUS AGENT")
    print("This agent will work without timeouts and show live Codex output.")
    print("Press Ctrl+C at any time to interrupt.")
    
    workflow = LiveAgentWorkflow()
    result = await workflow.execute_task(args.task, success_criteria)
    
    # Final summary
    print("\n" + "="*80)
    print("🎯 FINAL RESULTS")
    print("="*80)
    print(f"Task: {result.description}")
    print(f"Branch: {result.branch_name}")
    print(f"URL: {result.deployment_url}")
    print(f"Status: {result.status}")
    print(f"Iterations: {result.current_iteration}")
    
    if result.status == "completed":
        print("\n🎉 SUCCESS! Task completed autonomously!")
        print("The agent analyzed, implemented, built, deployed, and verified the solution.")
    elif result.status == "interrupted":
        print("\n⚠️ Task was interrupted by user")
    else:
        print("\n❌ Task failed to complete")
        print("Check the logs above for details.")

if __name__ == "__main__":
    asyncio.run(main())
