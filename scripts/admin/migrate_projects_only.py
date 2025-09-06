#!/usr/bin/env python3
"""
Projects Migration Script: Migrate projects data for existing users
"""

import boto3
import json
import sys
from typing import Dict, List
from datetime import datetime

class ProjectsMigrationManager:
    def __init__(self, source_pool_id: str, target_pool_id: str, region: str = 'us-west-2', cross_account_role_arn: str = None):
        self.source_pool_id = source_pool_id
        self.target_pool_id = target_pool_id
        self.region = region
        self.cross_account_role_arn = cross_account_role_arn
        
        # Initialize AWS clients for source (development account)
        self.cognito_client = boto3.client('cognito-idp', region_name=region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=region)
        
        # Initialize AWS clients for target (production account via cross-account role)
        if cross_account_role_arn:
            self.target_credentials = self._assume_cross_account_role()
            self.target_cognito_client = boto3.client(
                'cognito-idp', 
                region_name=region,
                aws_access_key_id=self.target_credentials['AccessKeyId'],
                aws_secret_access_key=self.target_credentials['SecretAccessKey'],
                aws_session_token=self.target_credentials['SessionToken']
            )
            self.target_dynamodb_client = boto3.client(
                'dynamodb', 
                region_name=region,
                aws_access_key_id=self.target_credentials['AccessKeyId'],
                aws_secret_access_key=self.target_credentials['SecretAccessKey'],
                aws_session_token=self.target_credentials['SessionToken']
            )
        else:
            self.target_cognito_client = self.cognito_client
            self.target_dynamodb_client = self.dynamodb_client
        
        self.migration_log = []
        
    def _assume_cross_account_role(self):
        """Assume cross-account role for production access"""
        sts_client = boto3.client('sts', region_name=self.region)
        
        try:
            response = sts_client.assume_role(
                RoleArn=self.cross_account_role_arn,
                RoleSessionName='projects-migration-session',
                ExternalId='spaceport-migration-2025'
            )
            print(f"✅ Successfully assumed cross-account role: {self.cross_account_role_arn}")
            return response['Credentials']
        except Exception as e:
            print(f"❌ Failed to assume cross-account role: {e}")
            raise e
    
    def get_user_id_mapping(self) -> Dict[str, str]:
        """Get mapping of old user IDs to new user IDs"""
        user_mapping = {}
        
        # Get all users from source pool
        paginator = self.cognito_client.get_paginator('list_users')
        for page in paginator.paginate(UserPoolId=self.source_pool_id):
            for user in page['Users']:
                if user['UserStatus'] == 'CONFIRMED':
                    email = None
                    old_user_id = None
                    
                    for attr in user.get('Attributes', []):
                        if attr['Name'] == 'email':
                            email = attr['Value']
                        elif attr['Name'] == 'sub':
                            old_user_id = attr['Value']
                    
                    if email and old_user_id:
                        # Get new user ID from target pool
                        try:
                            response = self.target_cognito_client.list_users(
                                UserPoolId=self.target_pool_id,
                                Filter=f'email = "{email}"'
                            )
                            if response['Users']:
                                new_user_id = response['Users'][0]['Username']
                                user_mapping[old_user_id] = new_user_id
                                print(f"📋 Mapped {email}: {old_user_id} → {new_user_id}")
                        except Exception as e:
                            print(f"❌ Error mapping user {email}: {e}")
        
        return user_mapping
    
    def migrate_projects_data(self, user_mapping: Dict[str, str]):
        """Migrate projects data for all users"""
        projects_table = 'Spaceport-Projects-staging'  # Source table
        target_table = 'Spaceport-Projects'            # Target table (production)
        
        print(f"🔄 Migrating projects from {projects_table} to {target_table}")
        
        # Scan all projects from source
        try:
            response = self.dynamodb_client.scan(TableName=projects_table)
            projects = response.get('Items', [])
            
            print(f"📊 Found {len(projects)} projects to migrate")
            
            for project in projects:
                old_user_id = project.get('userSub', {}).get('S')
                if old_user_id in user_mapping:
                    new_user_id = user_mapping[old_user_id]
                    
                    # Update the project with new user ID
                    project['userSub'] = {'S': new_user_id}
                    
                    # Remove any attributes that shouldn't be copied
                    if 'createdAt' in project:
                        del project['createdAt']
                    if 'updatedAt' in project:
                        del project['updatedAt']
                    
                    # Put item in target table
                    try:
                        self.target_dynamodb_client.put_item(
                            TableName=target_table,
                            Item=project
                        )
                        print(f"✅ Migrated project {project.get('projectId', {}).get('S', 'unknown')} for user {new_user_id}")
                    except Exception as e:
                        print(f"❌ Error migrating project {project.get('projectId', {}).get('S', 'unknown')}: {e}")
                else:
                    print(f"⚠️  No mapping found for user {old_user_id}")
                    
        except Exception as e:
            print(f"❌ Error scanning projects table: {e}")

def main():
    """Main projects migration function"""
    # Configuration
    SOURCE_POOL_ID = "us-west-2_a2jf3ldGV"  # Staging pool (development account)
    TARGET_POOL_ID = "us-west-2_SnOJuAJXa"  # Production pool (production account)
    CROSS_ACCOUNT_ROLE_ARN = "arn:aws:iam::356638455876:role/SpaceportMigrationRole"
    REGION = "us-west-2"
    
    print("🚀 Starting projects migration...")
    print(f"Source Pool: {SOURCE_POOL_ID}")
    print(f"Target Pool: {TARGET_POOL_ID}")
    print("=" * 60)
    
    # Initialize migration manager
    migration_manager = ProjectsMigrationManager(
        source_pool_id=SOURCE_POOL_ID,
        target_pool_id=TARGET_POOL_ID,
        region=REGION,
        cross_account_role_arn=CROSS_ACCOUNT_ROLE_ARN
    )
    
    # Get user ID mapping
    user_mapping = migration_manager.get_user_id_mapping()
    print(f"📋 Mapped {len(user_mapping)} users")
    
    # Migrate projects
    migration_manager.migrate_projects_data(user_mapping)
    
    print("✅ Projects migration completed!")

if __name__ == "__main__":
    main()
