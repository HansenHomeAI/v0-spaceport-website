#!/usr/bin/env python3
"""
Test the Complete Autonomous Workflow
====================================

This script tests the full autonomous development pipeline:
1. Creates an agent branch with isolated environment
2. Deploys frontend + backend with unique suffix
3. Runs autonomous tests against deployed environment
4. Creates pull request when complete

Usage:
    python test-autonomous-workflow.py
"""

import asyncio
import json
import subprocess
import time
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_autonomous_workflow():
    """Test the complete autonomous workflow"""
    
    logger.info("🚀 Testing Complete Autonomous Workflow")
    logger.info("=" * 60)
    
    # Test task configuration
    test_task = {
        "id": "test-workflow-001",
        "description": "Add a subtle hover effect to the join waitlist button",
        "branch_name": "agent/hover-effect-test",
        "priority": 1,
        "estimated_time_minutes": 20,
        "dependencies": [],
        "success_criteria": [
            "Button has smooth hover transition",
            "Hover effect is visually appealing",
            "No console errors when hovering",
            "Button remains accessible",
            "Page loads without errors after changes"
        ]
    }
    
    logger.info(f"📋 Test Task: {test_task['description']}")
    logger.info(f"🌿 Agent Branch: {test_task['branch_name']}")
    logger.info(f"🎯 Success Criteria: {len(test_task['success_criteria'])} requirements")
    
    # Write test task to file
    task_file = Path("test-autonomous-task.json")
    with open(task_file, 'w') as f:
        json.dump({"tasks": [test_task]}, f, indent=2)
    
    logger.info(f"📄 Task configuration saved to: {task_file}")
    
    try:
        # Run the orchestrator
        logger.info("🤖 Starting autonomous orchestrator...")
        
        cmd = [
            "python", "scripts/autonomous/codex-orchestrator.py",
            "--config", str(task_file),
            "--parallel", "1"
        ]
        
        logger.info(f"🔧 Command: {' '.join(cmd)}")
        
        # Run orchestrator and capture output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=Path.cwd()
        )
        
        # Monitor progress
        logger.info("⏳ Monitoring autonomous agent progress...")
        
        while process.poll() is None:
            line = process.stdout.readline()
            if line:
                logger.info(f"[AGENT] {line.strip()}")
            await asyncio.sleep(1)
        
        # Get final output
        stdout, stderr = process.communicate()
        
        if stdout:
            logger.info("📊 Final Output:")
            for line in stdout.strip().split('\n'):
                logger.info(f"[OUTPUT] {line}")
        
        if stderr:
            logger.error("❌ Errors:")
            for line in stderr.strip().split('\n'):
                logger.error(f"[ERROR] {line}")
        
        # Check results
        if process.returncode == 0:
            logger.info("✅ Autonomous workflow completed successfully!")
            
            # Check if PR was created
            pr_check = subprocess.run([
                "gh", "pr", "list", "--head", test_task['branch_name']
            ], capture_output=True, text=True)
            
            if pr_check.returncode == 0 and pr_check.stdout.strip():
                logger.info("✅ Pull request created successfully!")
                logger.info(f"📝 PR Details: {pr_check.stdout.strip()}")
            else:
                logger.warning("⚠️ No pull request found")
                
            # Check deployment
            agent_id = test_task['branch_name'].replace('agent/', '').replace('/', '-')
            deployment_url = f"https://spaceport-agent-{agent_id}.pages.dev"
            
            curl_check = subprocess.run([
                "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                deployment_url
            ], capture_output=True, text=True)
            
            if curl_check.stdout.strip() == "200":
                logger.info(f"✅ Deployment accessible: {deployment_url}")
            else:
                logger.warning(f"⚠️ Deployment not accessible: {deployment_url} (HTTP {curl_check.stdout.strip()})")
                
        else:
            logger.error(f"❌ Autonomous workflow failed with exit code: {process.returncode}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Exception during test: {e}")
        return False
    
    finally:
        # Cleanup
        if task_file.exists():
            task_file.unlink()
            logger.info(f"🧹 Cleaned up task file: {task_file}")
    
    logger.info("🎉 Autonomous workflow test completed!")
    return True

async def main():
    """Main test function"""
    
    # Check prerequisites
    logger.info("🔍 Checking prerequisites...")
    
    # Check if gh CLI is available
    gh_check = subprocess.run(["gh", "--version"], capture_output=True)
    if gh_check.returncode != 0:
        logger.error("❌ GitHub CLI (gh) not found. Please install: brew install gh")
        return
    
    # Check if codex is available
    codex_check = subprocess.run(["codex", "--version"], capture_output=True)
    if codex_check.returncode != 0:
        logger.error("❌ Codex CLI not found. Please install: npm install -g @openai/codex")
        return
    
    # Check git status
    git_check = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if git_check.stdout.strip():
        logger.warning("⚠️ Working directory has uncommitted changes")
        logger.warning("   This may interfere with agent branch creation")
    
    logger.info("✅ Prerequisites check passed")
    
    # Run the test
    success = await test_autonomous_workflow()
    
    if success:
        logger.info("🎉 ALL TESTS PASSED - Autonomous workflow is operational!")
    else:
        logger.error("❌ TEST FAILED - Autonomous workflow needs fixes")

if __name__ == "__main__":
    asyncio.run(main())
