"""
Branch name sanitization utilities for AWS resource naming.

Converts branch names to AWS-compliant resource identifiers for use in:
- ECR repository names
- S3 bucket names
- CloudFormation stack names
- IAM role names
"""

import re


def sanitize_branch_name(branch_name: str, max_length: int = 50) -> str:
    """
    Sanitize a branch name to be AWS-compliant for resource naming.
    
    AWS naming rules:
    - ECR repos: lowercase, alphanumeric, hyphens, underscores, forward slashes
    - S3 buckets: lowercase, alphanumeric, hyphens (no underscores)
    - IAM/CFN: alphanumeric, hyphens (no underscores)
    
    This function creates a safe identifier that works for all resource types
    by removing invalid characters and converting to lowercase.
    
    Args:
        branch_name: The branch name (e.g., "agent-48291375-3dgs-testing")
        max_length: Maximum length for the sanitized name (default: 50)
    
    Returns:
        Sanitized branch name suitable for AWS resources
        Example: "agent-48291375-3dgs-testing" -> "agent482913753dgstesting"
    
    Examples:
        >>> sanitize_branch_name("agent-48291375-3dgs-testing")
        'agent482913753dgstesting'
        >>> sanitize_branch_name("main")
        'main'
        >>> sanitize_branch_name("development")
        'development'
        >>> sanitize_branch_name("feature/new-feature_123")
        'featurenewfeature123'
    """
    if not branch_name:
        return "default"
    
    # Convert to lowercase
    sanitized = branch_name.lower()
    
    # Remove invalid characters - keep only alphanumeric and hyphens
    # Remove hyphens for stricter compatibility (works for all AWS resources)
    sanitized = re.sub(r'[^a-z0-9]', '', sanitized)
    
    # Ensure it doesn't start or end with invalid characters
    sanitized = sanitized.strip('-_')
    
    # Truncate to max_length if needed
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    # Ensure minimum length (AWS requires at least 1 char, but we'll use 3 for safety)
    if len(sanitized) < 3:
        sanitized = sanitized + "br"  # Add "br" suffix for "branch"
    
    return sanitized


def get_resource_suffix(branch_name: str) -> str:
    """
    Get the resource suffix for a branch name.
    
    For standard branches (main, development), returns the standard suffix.
    For agent/feature branches, returns the sanitized branch name.
    
    Args:
        branch_name: The branch name
    
    Returns:
        Resource suffix to use in resource names
    """
    # Standard branch mappings
    if branch_name == "main":
        return "prod"
    elif branch_name == "development":
        return "staging"
    else:
        # For agent branches and other branches, use sanitized name
        return sanitize_branch_name(branch_name)


def is_agent_branch(branch_name: str) -> bool:
    """
    Check if a branch is an agent branch.
    
    Args:
        branch_name: The branch name
    
    Returns:
        True if the branch appears to be an agent branch
    """
    return branch_name.startswith("agent-") or "agent" in branch_name.lower()

