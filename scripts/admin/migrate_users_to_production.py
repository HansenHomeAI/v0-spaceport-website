#!/usr/bin/env python3
"""
User Migration Script: Staging to Production
Migrates users from staging Cognito pool to production pool with data preservation.
"""

import boto3
import json
import os
import sys
from typing import Dict, List, Optional
from datetime import datetime
import time

class UserMigrationManager:
    def __init__(self, source_pool_id: str, target_pool_id: str, region: str = 'us-west-2'):
        self.source_pool_id = source_pool_id
        self.target_pool_id = target_pool_id
        self.region = region
        
        # Initialize AWS clients
        self.cognito_client = boto3.client('cognito-idp', region_name=region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=region)
        
        # Migration tracking
        self.migration_log = []
        self.successful_migrations = 0
        self.failed_migrations = 0
        
    def log_migration(self, user_email: str, status: str, details: str = ""):
        """Log migration attempt"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'user_email': user_email,
            'status': status,
            'details': details
        }
        self.migration_log.append(entry)
        print(f"[{status.upper()}] {user_email}: {details}")
        
    def get_source_users(self) -> List[Dict]:
        """Get all users from source pool"""
        users = []
        paginator = self.cognito_client.get_paginator('list_users')
        
        try:
            for page in paginator.paginate(UserPoolId=self.source_pool_id):
                for user in page['Users']:
                    # Only migrate confirmed users
                    if user['UserStatus'] == 'CONFIRMED':
                        users.append(user)
            print(f"Found {len(users)} confirmed users in source pool")
            return users
        except Exception as e:
            print(f"Error getting source users: {e}")
            return []
    
    def user_exists_in_target(self, email: str) -> bool:
        """Check if user already exists in target pool"""
        try:
            response = self.cognito_client.list_users(
                UserPoolId=self.target_pool_id,
                Filter=f'email = "{email}"'
            )
            return len(response['Users']) > 0
        except Exception as e:
            print(f"Error checking if user exists: {e}")
            return False
    
    def create_user_in_target(self, user: Dict) -> Optional[str]:
        """Create user in target pool"""
        try:
            # Extract user attributes
            email = None
            username = None
            custom_attributes = {}
            
            for attr in user.get('Attributes', []):
                if attr['Name'] == 'email':
                    email = attr['Value']
                elif attr['Name'] == 'preferred_username':
                    username = attr['Value']
                elif attr['Name'].startswith('custom:'):
                    custom_attributes[attr['Name']] = attr['Value']
            
            if not email:
                raise Exception("User has no email attribute")
            
            # Check if user already exists
            if self.user_exists_in_target(email):
                self.log_migration(email, 'SKIPPED', 'User already exists in target pool')
                return None
            
            # Prepare user attributes for creation
            user_attributes = [
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'}
            ]
            
            # Add custom attributes if any
            for attr_name, attr_value in custom_attributes.items():
                user_attributes.append({'Name': attr_name, 'Value': attr_value})
            
            # Create user with temporary password
            response = self.cognito_client.admin_create_user(
                UserPoolId=self.target_pool_id,
                Username=email,
                UserAttributes=user_attributes,
                TemporaryPassword='TempPass123!',  # Will force password reset
                MessageAction='SUPPRESS'  # Don't send welcome email
            )
            
            new_user_id = response['User']['Username']
            self.log_migration(email, 'CREATED', f'User created with ID: {new_user_id}')
            return new_user_id
            
        except Exception as e:
            self.log_migration(email, 'FAILED', f'Error creating user: {str(e)}')
            return None
    
    def migrate_user_data(self, old_user_id: str, new_user_id: str, email: str):
        """Migrate user's DynamoDB data"""
        try:
            # Migrate projects
            self.migrate_projects_data(old_user_id, new_user_id, email)
            
            # Migrate user profile data
            self.migrate_user_profile(old_user_id, new_user_id, email)
            
            self.log_migration(email, 'DATA_MIGRATED', 'User data migrated successfully')
            
        except Exception as e:
            self.log_migration(email, 'DATA_FAILED', f'Error migrating data: {str(e)}')
    
    def migrate_projects_data(self, old_user_id: str, new_user_id: str, email: str):
        """Migrate user's projects from DynamoDB"""
        try:
            # Get projects table name (adjust as needed)
            projects_table = 'Spaceport-Projects-staging'  # Source table
            target_table = 'Spaceport-Projects-prod'      # Target table
            
            # Scan for user's projects
            response = self.dynamodb_client.scan(
                TableName=projects_table,
                FilterExpression='userSub = :user_id',
                ExpressionAttributeValues={':user_id': {'S': old_user_id}}
            )
            
            projects = response.get('Items', [])
            if not projects:
                print(f"No projects found for user {email}")
                return
            
            print(f"Migrating {len(projects)} projects for user {email}")
            
            # Migrate each project
            for project in projects:
                # Update user ID reference
                project['userSub'] = {'S': new_user_id}
                
                # Write to target table
                self.dynamodb_client.put_item(
                    TableName=target_table,
                    Item=project
                )
            
            self.log_migration(email, 'PROJECTS_MIGRATED', f'{len(projects)} projects migrated')
            
        except Exception as e:
            self.log_migration(email, 'PROJECTS_FAILED', f'Error migrating projects: {str(e)}')
    
    def migrate_user_profile(self, old_user_id: str, new_user_id: str, email: str):
        """Migrate user profile data"""
        try:
            # Get users table name (adjust as needed)
            users_table = 'Spaceport-Users-staging'  # Source table
            target_table = 'Spaceport-Users-prod'    # Target table
            
            # Get user profile
            response = self.dynamodb_client.get_item(
                TableName=users_table,
                Key={'id': {'S': old_user_id}}
            )
            
            if 'Item' in response:
                user_profile = response['Item']
                # Update user ID
                user_profile['id'] = {'S': new_user_id}
                
                # Write to target table
                self.dynamodb_client.put_item(
                    TableName=target_table,
                    Item=user_profile
                )
                
                self.log_migration(email, 'PROFILE_MIGRATED', 'User profile migrated')
            else:
                print(f"No profile found for user {email}")
                
        except Exception as e:
            self.log_migration(email, 'PROFILE_FAILED', f'Error migrating profile: {str(e)}')
    
    def send_password_reset_email(self, email: str):
        """Send password reset email to user"""
        try:
            # This will trigger Cognito's built-in password reset flow
            self.cognito_client.forgot_password(
                ClientId=self.get_client_id(self.target_pool_id),
                Username=email
            )
            self.log_migration(email, 'RESET_EMAIL_SENT', 'Password reset email sent')
        except Exception as e:
            self.log_migration(email, 'RESET_EMAIL_FAILED', f'Error sending reset email: {str(e)}')
    
    def get_client_id(self, pool_id: str) -> str:
        """Get the first client ID for the pool"""
        try:
            response = self.cognito_client.list_user_pool_clients(UserPoolId=pool_id)
            if response['UserPoolClients']:
                return response['UserPoolClients'][0]['ClientId']
            else:
                raise Exception("No clients found for pool")
        except Exception as e:
            print(f"Error getting client ID: {e}")
            return ""
    
    def run_migration(self, dry_run: bool = True):
        """Run the complete migration process"""
        print(f"Starting user migration from {self.source_pool_id} to {self.target_pool_id}")
        print(f"DRY RUN: {dry_run}")
        print("=" * 60)
        
        # Get source users
        source_users = self.get_source_users()
        if not source_users:
            print("No users found to migrate")
            return
        
        # Process each user
        for user in source_users:
            email = None
            for attr in user.get('Attributes', []):
                if attr['Name'] == 'email':
                    email = attr['Value']
                    break
            
            if not email:
                self.log_migration('unknown', 'FAILED', 'User has no email')
                continue
            
            if dry_run:
                self.log_migration(email, 'DRY_RUN', 'Would migrate user')
                continue
            
            # Create user in target pool
            new_user_id = self.create_user_in_target(user)
            if new_user_id:
                # Migrate user data
                self.migrate_user_data(user['Username'], new_user_id, email)
                
                # Send password reset email
                self.send_password_reset_email(email)
                
                self.successful_migrations += 1
            else:
                self.failed_migrations += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        # Print summary
        self.print_migration_summary()
    
    def print_migration_summary(self):
        """Print migration results summary"""
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Successful migrations: {self.successful_migrations}")
        print(f"Failed migrations: {self.failed_migrations}")
        print(f"Total processed: {len(self.migration_log)}")
        
        # Save migration log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"migration_log_{timestamp}.json"
        
        with open(log_filename, 'w') as f:
            json.dump(self.migration_log, f, indent=2)
        
        print(f"Migration log saved to: {log_filename}")

def main():
    """Main migration function"""
    # Configuration
    SOURCE_POOL_ID = "us-west-2_a2jf3ldGV"  # Staging pool
    TARGET_POOL_ID = "us-west-2_XXXXX"      # Production pool (update this)
    REGION = "us-west-2"
    
    # Check if this is a dry run
    dry_run = '--dry-run' in sys.argv or '--dryrun' in sys.argv
    
    # Confirm before proceeding
    if not dry_run:
        print("⚠️  WARNING: This will perform a REAL migration!")
        print(f"Source Pool: {SOURCE_POOL_ID}")
        print(f"Target Pool: {TARGET_POOL_ID}")
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Migration cancelled")
            return
    
    # Initialize migration manager
    migration_manager = UserMigrationManager(
        source_pool_id=SOURCE_POOL_ID,
        target_pool_id=TARGET_POOL_ID,
        region=REGION
    )
    
    # Run migration
    migration_manager.run_migration(dry_run=dry_run)

if __name__ == "__main__":
    main()
