#!/bin/bash

# User Migration Script Runner
# This script handles the migration of users from staging to production pools

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATION_SCRIPT="$SCRIPT_DIR/migrate_users_to_production.py"
AWS_PROFILE="spaceport-migration"  # Use migration user profile for cross-account access

echo -e "${BLUE}🚀 Spaceport User Migration Tool${NC}"
echo "=================================="

# Check if migration script exists
if [ ! -f "$MIGRATION_SCRIPT" ]; then
    echo -e "${RED}❌ Migration script not found: $MIGRATION_SCRIPT${NC}"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 is required but not installed${NC}"
    exit 1
fi

# Check if boto3 is installed
if ! python3 -c "import boto3" &> /dev/null; then
    echo -e "${RED}❌ boto3 is required but not installed${NC}"
    echo "Install with: pip3 install boto3"
    exit 1
fi

# Check AWS credentials
echo -e "${YELLOW}🔍 Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured for profile: $AWS_PROFILE${NC}"
    echo "Please configure AWS credentials first:"
    echo "aws configure --profile $AWS_PROFILE"
    exit 1
fi

# Get current user info
CURRENT_USER=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query 'Arn' --output text)
echo -e "${GREEN}✅ Using AWS profile: $AWS_PROFILE${NC}"
echo -e "${GREEN}✅ Authenticated as: $CURRENT_USER${NC}"

# Parse command line arguments
DRY_RUN=true
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --live)
            DRY_RUN=false
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --live     Perform actual migration (default is dry run)"
            echo "  --force    Skip confirmation prompts"
            echo "  --help     Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Dry run (safe)"
            echo "  $0 --live             # Real migration with confirmation"
            echo "  $0 --live --force     # Real migration without confirmation"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set AWS profile for the script
export AWS_PROFILE="$AWS_PROFILE"

# Show migration mode
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 Running in DRY RUN mode (no changes will be made)${NC}"
else
    echo -e "${RED}⚠️  Running in LIVE mode (real migration will be performed)${NC}"
fi

# Confirm before proceeding (unless --force is used)
if [ "$DRY_RUN" = false ] && [ "$FORCE" = false ]; then
    echo ""
    echo -e "${RED}⚠️  WARNING: This will perform a REAL migration!${NC}"
    echo "This will:"
    echo "  • Create users in production pool"
    echo "  • Migrate all user data"
    echo "  • Send password reset emails"
    echo "  • This action cannot be easily undone"
    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${YELLOW}Migration cancelled${NC}"
        exit 0
    fi
fi

# Run the migration script
echo ""
echo -e "${BLUE}🚀 Starting migration...${NC}"
echo "=================================="

if [ "$DRY_RUN" = true ]; then
    python3 "$MIGRATION_SCRIPT" --dry-run
else
    python3 "$MIGRATION_SCRIPT"
fi

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Migration completed successfully!${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}💡 To perform the actual migration, run: $0 --live${NC}"
    else
        echo -e "${GREEN}📧 Users have been migrated and password reset emails sent${NC}"
        echo -e "${GREEN}🔗 Users can now reset their passwords and sign in${NC}"
    fi
else
    echo ""
    echo -e "${RED}❌ Migration failed with errors${NC}"
    echo "Check the migration log for details"
    exit 1
fi
