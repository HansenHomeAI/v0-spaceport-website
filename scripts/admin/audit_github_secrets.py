#!/usr/bin/env python3
"""
GitHub Secrets Audit Script
Compares current GitHub secrets with working API Gateway URLs
"""

import subprocess
import json
import sys
from typing import Dict, List, Tuple

class GitHubSecretsAuditor:
    def __init__(self):
        self.working_urls = {
            'WAITLIST_API_URL_PREVIEW': 'https://h6ogvocgk4.execute-api.us-west-2.amazonaws.com/prod',
            'DRONE_PATH_API_URL_PREVIEW': 'https://yhpjmfhdxf.execute-api.us-west-2.amazonaws.com/prod',
            'FILE_UPLOAD_API_URL_PREVIEW': 'https://xv4bpkwlb8.execute-api.us-west-2.amazonaws.com/prod',
            'PROJECTS_API_URL_PREVIEW': 'https://mca9yf1vgl.execute-api.us-west-2.amazonaws.com/prod',
            'PASSWORD_RESET_API_URL_PREVIEW': 'https://mx549qsbel.execute-api.us-west-2.amazonaws.com/prod',
            'INVITE_API_URL_PREVIEW': 'https://xtmhni13l2.execute-api.us-west-2.amazonaws.com/prod',
            'BETA_ACCESS_API_URL_PREVIEW': 'https://y5fej7zgx8.execute-api.us-west-2.amazonaws.com/prod',
            'SUBSCRIPTION_API_URL_PREVIEW': 'https://xduxbyklm1.execute-api.us-west-2.amazonaws.com/prod',
            'FEEDBACK_API_URL_PREVIEW': 'https://pending-feedback-api.execute-api.us-west-2.amazonaws.com/prod/feedback'
        }
        
        self.required_secrets = [
            'WAITLIST_API_URL_PREVIEW',
            'DRONE_PATH_API_URL_PREVIEW', 
            'FILE_UPLOAD_API_URL_PREVIEW',
            'PROJECTS_API_URL_PREVIEW',
            'PASSWORD_RESET_API_URL_PREVIEW',
            'INVITE_API_URL_PREVIEW',
            'BETA_ACCESS_API_URL_PREVIEW',
            'SUBSCRIPTION_API_URL_PREVIEW',
            'FEEDBACK_API_URL_PREVIEW',
            'ML_PIPELINE_API_URL_PREVIEW'  # This one we need to check separately
        ]
    
    def get_github_secrets(self) -> Dict[str, str]:
        """Get current GitHub secrets using gh CLI"""
        try:
            result = subprocess.run(
                ['gh', 'secret', 'list', '--json', 'name,updatedAt'],
                capture_output=True,
                text=True,
                check=True
            )
            secrets_data = json.loads(result.stdout)
            return {secret['name']: secret['updatedAt'] for secret in secrets_data}
        except subprocess.CalledProcessError as e:
            print(f"❌ Error getting GitHub secrets: {e}")
            print("Make sure you're authenticated with 'gh auth login'")
            return {}
        except FileNotFoundError:
            print("❌ GitHub CLI not found. Install with: brew install gh")
            return {}
    
    def check_secret_exists(self, secret_name: str) -> bool:
        """Check if a specific secret exists"""
        try:
            result = subprocess.run(
                ['gh', 'secret', 'get', secret_name],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def audit_secrets(self) -> Dict[str, Dict]:
        """Audit all required secrets"""
        print("🔍 Auditing GitHub Secrets")
        print("=" * 40)
        
        existing_secrets = self.get_github_secrets()
        audit_results = {}
        
        for secret_name in self.required_secrets:
            result = {
                'exists': secret_name in existing_secrets,
                'last_updated': existing_secrets.get(secret_name, 'Unknown'),
                'has_working_url': secret_name in self.working_urls,
                'working_url': self.working_urls.get(secret_name, 'Not available'),
                'status': 'unknown'
            }
            
            if result['exists'] and result['has_working_url']:
                result['status'] = 'needs_verification'
            elif result['exists'] and not result['has_working_url']:
                result['status'] = 'needs_update'
            elif not result['exists'] and result['has_working_url']:
                result['status'] = 'needs_creation'
            else:
                result['status'] = 'unknown'
            
            audit_results[secret_name] = result
        
        return audit_results
    
    def generate_report(self, audit_results: Dict[str, Dict]) -> str:
        """Generate audit report"""
        report = []
        report.append("\n📊 GITHUB SECRETS AUDIT REPORT")
        report.append("=" * 50)
        
        # Count by status
        status_counts = {}
        for result in audit_results.values():
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        report.append(f"Total Secrets: {len(audit_results)}")
        for status, count in status_counts.items():
            report.append(f"{status.replace('_', ' ').title()}: {count}")
        
        report.append("\n📋 DETAILED RESULTS:")
        report.append("-" * 30)
        
        for secret_name, result in audit_results.items():
            status_icon = {
                'needs_verification': '🔍',
                'needs_update': '⚠️',
                'needs_creation': '➕',
                'unknown': '❓'
            }.get(result['status'], '❓')
            
            report.append(f"{status_icon} {secret_name}")
            report.append(f"   Exists: {'Yes' if result['exists'] else 'No'}")
            report.append(f"   Last Updated: {result['last_updated']}")
            report.append(f"   Working URL: {result['working_url']}")
            report.append(f"   Status: {result['status'].replace('_', ' ').title()}")
            report.append("")
        
        return "\n".join(report)
    
    def generate_update_commands(self, audit_results: Dict[str, Dict]) -> str:
        """Generate commands to update GitHub secrets"""
        commands = []
        commands.append("\n🔧 GITHUB SECRETS UPDATE COMMANDS:")
        commands.append("=" * 40)
        commands.append("# Run these commands to update your GitHub secrets")
        commands.append("")
        
        for secret_name, result in audit_results.items():
            if result['has_working_url'] and result['status'] in ['needs_update', 'needs_creation']:
                url = result['working_url']
                commands.append(f"# {secret_name}")
                commands.append(f"gh secret set {secret_name} --body '{url}'")
                commands.append("")
        
        # Add ML Pipeline API URL (we need to get this from CloudFormation)
        commands.append("# ML Pipeline API URL (get from CloudFormation)")
        commands.append("ML_PIPELINE_URL=$(aws cloudformation describe-stacks --stack-name SpaceportMLPipelineStagingStack --query \"Stacks[0].Outputs[?OutputKey=='MLPipelineApiUrl'].OutputValue\" --output text)")
        commands.append("gh secret set ML_PIPELINE_API_URL_PREVIEW --body \"$ML_PIPELINE_URL\"")
        commands.append("")
        
        return "\n".join(commands)
    
    def check_production_urls(self) -> str:
        """Check if production URLs are available"""
        info = []
        info.append("\n🏭 PRODUCTION URLS STATUS:")
        info.append("=" * 30)
        info.append("Production URLs will be available after:")
        info.append("1. Deploying to main branch")
        info.append("2. CDK creates production stacks")
        info.append("3. CloudFormation outputs are generated")
        info.append("")
        info.append("Then run:")
        info.append("aws cloudformation describe-stacks --stack-name SpaceportStack --query \"Stacks[0].Outputs[?contains(OutputKey, 'ApiUrl')].{Key:OutputKey,Value:OutputValue}\" --output table")
        info.append("")
        info.append("And update the corresponding *_PROD secrets")
        
        return "\n".join(info)

def main():
    auditor = GitHubSecretsAuditor()
    
    # Run audit
    audit_results = auditor.audit_secrets()
    
    # Generate and print report
    report = auditor.generate_report(audit_results)
    print(report)
    
    # Generate update commands
    update_commands = auditor.generate_update_commands(audit_results)
    print(update_commands)
    
    # Check production status
    production_info = auditor.check_production_urls()
    print(production_info)
    
    # Exit with error code if any secrets need attention
    needs_attention = sum(1 for r in audit_results.values() if r['status'] in ['needs_update', 'needs_creation'])
    if needs_attention > 0:
        print(f"\n⚠️  {needs_attention} secrets need attention. Check the commands above.")
        sys.exit(1)
    else:
        print("\n🎉 All secrets are up to date!")

if __name__ == "__main__":
    main()
