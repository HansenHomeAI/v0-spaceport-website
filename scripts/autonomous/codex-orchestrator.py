#!/usr/bin/env python3
"""
Codex AI Orchestrator for Autonomous Full-Stack Development
============================================================

This script orchestrates multiple Codex CLI agents to handle parallel development tasks.
It implements the workflow described by the Reddit user: using Cursor/GPT-5 as the 
orchestrator and spawning external Codex CLI agents via subprocess.

Usage:
    python scripts/autonomous/codex-orchestrator.py --task "Fix authentication bug" --parallel 3
    python scripts/autonomous/codex-orchestrator.py --config tasks.json --review-only
"""

import asyncio
import json
import subprocess
import tempfile
import time
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import argparse
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class AgentTask:
    """Represents a task for a Codex agent"""
    id: str
    description: str
    branch_name: str
    priority: int
    estimated_time_minutes: int
    dependencies: List[str]
    success_criteria: List[str]
    status: str = "pending"  # pending, running, completed, failed
    agent_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    output_log: str = ""
    test_results: Dict[str, Any] = None

@dataclass 
class OrchestrationResult:
    """Results from the orchestration session"""
    session_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_time_seconds: float
    tasks: List[AgentTask]
    summary: str

class CodexOrchestrator:
    """Orchestrates multiple Codex CLI agents for parallel development"""
    
    def __init__(self, max_parallel_agents: int = 3, workspace_root: str = "."):
        self.max_parallel_agents = max_parallel_agents
        self.workspace_root = Path(workspace_root)
        self.session_id = str(uuid.uuid4())[:8]
        self.active_agents: Dict[str, subprocess.Popen] = {}
        self.completed_tasks: List[AgentTask] = []
        self.failed_tasks: List[AgentTask] = []
        
    async def create_agent_worktree(self, task: AgentTask) -> str:
        """Create a Git worktree for the agent to work in isolation"""
        worktree_path = self.workspace_root / f".agent-worktrees" / task.branch_name
        
        # Clean up existing worktree if it exists
        if worktree_path.exists():
            subprocess.run(["git", "worktree", "remove", str(worktree_path)], 
                         capture_output=True, cwd=self.workspace_root)
        
        # Create new worktree
        result = subprocess.run([
            "git", "worktree", "add", str(worktree_path), "development"
        ], capture_output=True, text=True, cwd=self.workspace_root)
        
        if result.returncode != 0:
            raise Exception(f"Failed to create worktree: {result.stderr}")
            
        # Create and checkout agent branch
        subprocess.run([
            "git", "checkout", "-b", task.branch_name
        ], capture_output=True, cwd=worktree_path)
        
        return str(worktree_path)

    async def spawn_codex_agent(self, task: AgentTask, worktree_path: str) -> subprocess.Popen:
        """Spawn a Codex CLI agent to work on the task"""
        
        # Create the Codex command
        codex_prompt = f"""
Goal: {task.description}

Success Criteria:
{chr(10).join(f"- {criteria}" for criteria in task.success_criteria)}

Workflow:
1. Analyze the codebase to understand the current implementation
2. Implement the necessary changes
3. Run tests to validate the changes
4. If tests fail, debug and iterate
5. When tests pass, commit the changes
6. Push to the agent branch for deployment
7. Run end-to-end tests on the deployed version
8. If E2E tests fail, iterate until they pass

Environment:
- Working directory: {worktree_path}
- Branch: {task.branch_name}
- Test command: npm run test:autonomous
- Deploy command: git push origin {task.branch_name}

Constraints:
- Maximum execution time: 60 minutes
- Must pass all tests before completing
- Must capture and analyze any errors
- Must provide detailed commit messages

Output JSON status updates to stdout with format:
{{"status": "progress|completed|failed", "message": "...", "timestamp": "..."}}
"""

        # Write prompt to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(codex_prompt)
            prompt_file = f.name

        # Spawn Codex CLI process
        cmd = [
            "codex", "do", "--file", prompt_file,
            "--working-directory", worktree_path,
            "--timeout", "3600",  # 1 hour timeout
            "--output", "json"
        ]
        
        logger.info(f"🤖 Spawning Codex agent for task: {task.description}")
        logger.info(f"   Branch: {task.branch_name}")
        logger.info(f"   Worktree: {worktree_path}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=worktree_path
        )
        
        return process

    async def monitor_agent(self, task: AgentTask, process: subprocess.Popen) -> AgentTask:
        """Monitor a running Codex agent and capture its output"""
        
        task.status = "running"
        task.start_time = time.time()
        
        output_lines = []
        
        try:
            # Read output in real-time
            while process.poll() is None:
                line = process.stdout.readline()
                if line:
                    output_lines.append(line.strip())
                    logger.info(f"[Agent {task.agent_id}] {line.strip()}")
                    
                    # Try to parse JSON status updates
                    try:
                        status_update = json.loads(line)
                        if status_update.get('status') == 'completed':
                            logger.info(f"✅ Agent {task.agent_id} completed task: {task.description}")
                        elif status_update.get('status') == 'failed':
                            logger.error(f"❌ Agent {task.agent_id} failed task: {task.description}")
                    except json.JSONDecodeError:
                        pass  # Not a JSON status update
                
                await asyncio.sleep(0.1)
            
            # Get final output
            stdout, stderr = process.communicate()
            if stdout:
                output_lines.extend(stdout.strip().split('\n'))
            
            task.output_log = '\n'.join(output_lines)
            task.end_time = time.time()
            
            # Determine final status
            if process.returncode == 0:
                task.status = "completed"
                logger.info(f"✅ Task completed: {task.description}")
            else:
                task.status = "failed" 
                logger.error(f"❌ Task failed: {task.description}")
                logger.error(f"Error output: {stderr}")
                
        except Exception as e:
            task.status = "failed"
            task.end_time = time.time()
            logger.error(f"❌ Exception monitoring agent {task.agent_id}: {e}")
            
        return task

    async def run_autonomous_tests(self, task: AgentTask, worktree_path: str) -> Dict[str, Any]:
        """Run autonomous tests on the deployed agent branch"""
        
        logger.info(f"🧪 Running autonomous tests for {task.branch_name}")
        
        # Wait for deployment to be ready (GitHub Actions takes time)
        await asyncio.sleep(60)
        
        # Run Playwright tests against the agent deployment
        agent_id = task.branch_name.replace('agent/', '').replace('/', '-')
        test_url = f"https://spaceport-agent-{agent_id}.pages.dev"
        
        cmd = [
            "npm", "run", "test:autonomous"
        ]
        
        env = {
            **dict(subprocess.os.environ),
            "PLAYWRIGHT_BASE_URL": test_url
        }
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=worktree_path / "web",
            env=env
        )
        
        # Parse test results
        test_results = {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
            "deployment_url": test_url
        }
        
        # Try to parse JSON test results if available
        try:
            results_file = worktree_path / "web" / "test-results" / "results.json"
            if results_file.exists():
                with open(results_file) as f:
                    test_results["detailed_results"] = json.load(f)
        except Exception as e:
            logger.warning(f"Could not parse detailed test results: {e}")
            
        return test_results

    async def orchestrate_tasks(self, tasks: List[AgentTask]) -> OrchestrationResult:
        """Orchestrate multiple tasks with parallel execution"""
        
        start_time = time.time()
        logger.info(f"🚀 Starting orchestration session {self.session_id}")
        logger.info(f"   Total tasks: {len(tasks)}")
        logger.info(f"   Max parallel agents: {self.max_parallel_agents}")
        
        # Create worktrees and spawn agents
        running_tasks = []
        
        for task in tasks[:self.max_parallel_agents]:
            try:
                # Create worktree
                worktree_path = await self.create_agent_worktree(task)
                
                # Spawn agent
                task.agent_id = f"agent-{len(running_tasks) + 1}"
                process = await self.spawn_codex_agent(task, worktree_path)
                self.active_agents[task.agent_id] = process
                
                # Start monitoring
                monitor_task = asyncio.create_task(
                    self.monitor_agent(task, process)
                )
                running_tasks.append((task, monitor_task, worktree_path))
                
            except Exception as e:
                logger.error(f"❌ Failed to start agent for task {task.description}: {e}")
                task.status = "failed"
                self.failed_tasks.append(task)
        
        # Wait for agents to complete and run tests
        for task, monitor_task, worktree_path in running_tasks:
            try:
                # Wait for agent to complete
                completed_task = await monitor_task
                
                if completed_task.status == "completed":
                    # Run autonomous tests
                    test_results = await self.run_autonomous_tests(completed_task, worktree_path)
                    completed_task.test_results = test_results
                    
                    if test_results["success"]:
                        self.completed_tasks.append(completed_task)
                        logger.info(f"✅ Task fully validated: {completed_task.description}")
                    else:
                        completed_task.status = "failed"
                        self.failed_tasks.append(completed_task)
                        logger.error(f"❌ Task failed validation: {completed_task.description}")
                else:
                    self.failed_tasks.append(completed_task)
                    
            except Exception as e:
                logger.error(f"❌ Exception processing task {task.description}: {e}")
                task.status = "failed"
                self.failed_tasks.append(task)
        
        # Generate results
        end_time = time.time()
        total_time = end_time - start_time
        
        all_tasks = self.completed_tasks + self.failed_tasks
        
        result = OrchestrationResult(
            session_id=self.session_id,
            total_tasks=len(tasks),
            completed_tasks=len(self.completed_tasks),
            failed_tasks=len(self.failed_tasks),
            total_time_seconds=total_time,
            tasks=all_tasks,
            summary=self.generate_summary()
        )
        
        return result

    def generate_summary(self) -> str:
        """Generate a human-readable summary of the orchestration session"""
        
        total = len(self.completed_tasks) + len(self.failed_tasks)
        success_rate = (len(self.completed_tasks) / total * 100) if total > 0 else 0
        
        summary = f"""
🤖 Autonomous Development Session Complete
==========================================

Session ID: {self.session_id}
Success Rate: {success_rate:.1f}% ({len(self.completed_tasks)}/{total})
Total Time: {sum(t.end_time - t.start_time for t in self.completed_tasks + self.failed_tasks if t.start_time and t.end_time):.1f} seconds

✅ Completed Tasks:
{chr(10).join(f"  - {t.description} ({t.branch_name})" for t in self.completed_tasks)}

❌ Failed Tasks:
{chr(10).join(f"  - {t.description} ({t.branch_name})" for t in self.failed_tasks)}

Next Steps:
- Review failed tasks for manual intervention
- Merge successful branches to development
- Update task definitions based on learnings
"""
        return summary

async def main():
    """Main entry point for the orchestrator"""
    
    parser = argparse.ArgumentParser(description="Codex AI Orchestrator")
    parser.add_argument("--task", help="Single task description")
    parser.add_argument("--config", help="JSON file with multiple tasks")
    parser.add_argument("--parallel", type=int, default=3, help="Max parallel agents")
    parser.add_argument("--review-only", action="store_true", help="Generate review only")
    
    args = parser.parse_args()
    
    # Load tasks
    tasks = []
    
    if args.task:
        # Single task from command line
        task_id = str(uuid.uuid4())[:8]
        task = AgentTask(
            id=task_id,
            description=args.task,
            branch_name=f"agent/{task_id}",
            priority=1,
            estimated_time_minutes=30,
            dependencies=[],
            success_criteria=[
                "Code compiles without errors",
                "All tests pass",
                "Frontend loads without console errors",
                "Deployment succeeds"
            ]
        )
        tasks.append(task)
        
    elif args.config:
        # Multiple tasks from JSON file
        with open(args.config) as f:
            task_data = json.load(f)
            tasks = [AgentTask(**t) for t in task_data["tasks"]]
    
    else:
        print("Please provide either --task or --config")
        return
    
    # Run orchestration
    orchestrator = CodexOrchestrator(max_parallel_agents=args.parallel)
    result = await orchestrator.orchestrate_tasks(tasks)
    
    # Output results
    print(result.summary)
    
    # Save detailed results
    results_file = f"orchestration-results-{result.session_id}.json"
    with open(results_file, 'w') as f:
        json.dump(asdict(result), f, indent=2, default=str)
    
    logger.info(f"📊 Detailed results saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())
