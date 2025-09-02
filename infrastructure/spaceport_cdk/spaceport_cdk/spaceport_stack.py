from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_ssm as ssm,
    RemovalPolicy,
    Duration,
    CfnOutput,
    CfnParameter,
    # BundlingOptions,  # Not needed since we're importing existing Lambda functions
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_sagemaker as sagemaker,
    aws_ecr as ecr,
    aws_logs as logs,
    aws_sns as sns,
    aws_events as events,
    aws_events_targets as targets,
    aws_cloudwatch as cloudwatch,
    aws_cognito as cognito,
)
from constructs import Construct
import os
import aws_cdk as cdk
import boto3

class SpaceportStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, env_config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Environment configuration
        self.env_config = env_config
        suffix = env_config['resourceSuffix']
        region = env_config['region']
        # Account will be dynamically resolved from deployment context
        
        # Initialize AWS clients for resource checking
        self.s3_client = boto3.client('s3', region_name=region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=region)

        # Track enhanced dynamic logic behavior
        self._enhanced_logic_actions = []

        # Create a CloudFormation parameter for the API key
        api_key_param = CfnParameter(
            self, "GoogleMapsApiKey",
            type="String",
            description="Google Maps API Key",
            no_echo=True  # This will mask the value in CloudFormation
        )

        # Upload bucket - this stack owns this bucket (ML Pipeline stack imports it)
        self.upload_bucket = self._get_or_create_s3_bucket(
            construct_id="SpaceportUploadBucket",
            preferred_name=f"spaceport-uploads-{suffix}",
            fallback_name="spaceport-uploads"
        )
        print(f"🆕 Main Spaceport stack owns upload bucket: {self.upload_bucket.bucket_name}")
        
        # Dynamic DynamoDB tables - import if exist, create if not
        self.file_metadata_table = self._get_or_create_dynamodb_table(
            construct_id="FileMetadataTable",
            preferred_name=f"Spaceport-FileMetadata-{suffix}",
            fallback_name="Spaceport-FileMetadata",
            partition_key_name="id",
            partition_key_type=dynamodb.AttributeType.STRING
        )

        self.drone_path_table = self._get_or_create_dynamodb_table(
            construct_id="DroneFlightPathsTable",
            preferred_name=f"Spaceport-DroneFlightPaths-{suffix}",
            fallback_name="Spaceport-DroneFlightPaths",
            partition_key_name="id",
            partition_key_type=dynamodb.AttributeType.STRING
        )
        
        # Dynamic waitlist table
        self.waitlist_table = self._get_or_create_dynamodb_table(
            construct_id="WaitlistTable",
            preferred_name=f"Spaceport-Waitlist-{suffix}",
            fallback_name="Spaceport-Waitlist",
            partition_key_name="email",
            partition_key_type=dynamodb.AttributeType.STRING
        )
        
        # Create Lambda execution role with permissions and environment-specific naming
        self.lambda_role = iam.Role(
            self, 
            "SpaceportLambdaRole",
            role_name=f"Spaceport-Lambda-Role-{suffix}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Add S3 permissions to the Lambda role
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:DeleteObject",
                    "s3:AbortMultipartUpload",
                    "s3:ListMultipartUploadParts",
                    "s3:ListBucketMultipartUploads"
                ],
                resources=[
                    f"arn:aws:s3:::{self.upload_bucket.bucket_name}",
                    f"arn:aws:s3:::{self.upload_bucket.bucket_name}/*"
                ]
            )
        )
        
        # Add ML bucket permissions
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:DeleteObject"
                ],
                resources=[
                    f"arn:aws:s3:::spaceport-ml-processing-{suffix}",
                    f"arn:aws:s3:::spaceport-ml-processing-{suffix}/*"
                ]
            )
        )
        
        # Grant DynamoDB permissions
        self.file_metadata_table.grant_read_write_data(self.lambda_role)
        self.drone_path_table.grant_read_write_data(self.lambda_role)
        self.waitlist_table.grant_read_write_data(self.lambda_role)
        
        # Add SES permissions for sending emails
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                resources=["*"]
            )
        )
        
        # Create Lambda functions with environment-specific naming
        self.drone_path_lambda = lambda_.Function(
            self, 
            "SpaceportDronePathFunction",
            function_name=f"Spaceport-DronePathFunction-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/drone_path"),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "UPLOAD_BUCKET": self.upload_bucket.bucket_name,
                "FILE_METADATA_TABLE": self.file_metadata_table.table_name,
                "DRONE_PATH_TABLE": self.drone_path_table.table_name,
                "ML_BUCKET": f"spaceport-ml-processing-{suffix}"
            }
        )
        
        self.file_upload_lambda = lambda_.Function(
            self, 
            "SpaceportFileUploadFunction",
            function_name=f"Spaceport-FileUploadFunction-{suffix}",
            runtime=lambda_.Runtime.NODEJS_18_X,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda/file_upload"),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "UPLOAD_BUCKET": self.upload_bucket.bucket_name,
                "FILE_METADATA_TABLE": self.file_metadata_table.table_name
            }
        )
        
        self.csv_upload_lambda = lambda_.Function(
            self, 
            "SpaceportCsvUploadFunction",
            function_name=f"Spaceport-CsvUploadFunction-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/csv_upload_url"),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "ML_BUCKET": f"spaceport-ml-processing-{suffix}"
            }
        )
        
        self.waitlist_lambda = lambda_.Function(
            self, 
            "SpaceportWaitlistFunction",
            function_name=f"Spaceport-WaitlistFunction-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/waitlist"),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "WAITLIST_TABLE": self.waitlist_table.table_name
            }
        )
        
        # ========== API GATEWAY CONFIGURATION ==========
        # Create API Gateway with environment-specific naming
        self.drone_path_api = apigw.RestApi(
            self,
            "SpaceportDronePathApi",
            rest_api_name=f"spaceport-drone-path-api-{suffix}",
            description=f"Spaceport Drone Path API for {env_config['domain']}",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["*"]
            )
        )
        
        self.file_upload_api = apigw.RestApi(
            self,
            "SpaceportFileUploadApi",
            rest_api_name=f"spaceport-file-upload-api-{suffix}",
            description=f"Spaceport File Upload API for {env_config['domain']}",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["*"]
            )
        )
        
        # Create API Gateway resources and methods
        self._create_drone_path_endpoints()
        self._create_file_upload_endpoints()
        
        # ========== OUTPUTS ==========
        CfnOutput(
            self,
            "DronePathApiUrl",
            value=f"https://{self.drone_path_api.rest_api_id}.execute-api.{region}.amazonaws.com/prod",
            description=f"Drone Path API Gateway URL for {suffix}"
        )
        
        CfnOutput(
            self,
            "FileUploadApiUrl",
            value=f"https://{self.file_upload_api.rest_api_id}.execute-api.{region}.amazonaws.com/prod",
            description=f"File Upload API Gateway URL for {suffix}"
        )
        
        CfnOutput(
            self,
            "UploadBucketName",
            value=self.upload_bucket.bucket_name,
            description=f"Upload S3 bucket name for {suffix}"
        )
        
        CfnOutput(
            self,
            "EnvironmentName",
            value=suffix,
            description=f"Environment suffix: {suffix}"
        )

    def _create_drone_path_endpoints(self):
        """Create drone path API endpoints"""
        # Create the main API resource once
        api_resource = self.drone_path_api.root.add_resource("api")
        
        # Elevation endpoint
        elevation_resource = api_resource.add_resource("elevation")
        elevation_resource.add_method("POST", apigw.LambdaIntegration(self.drone_path_lambda))
        
        # Optimize spiral endpoint
        optimize_resource = api_resource.add_resource("optimize-spiral")
        optimize_resource.add_method("POST", apigw.LambdaIntegration(self.drone_path_lambda))
        
        # CSV endpoint
        csv_resource = api_resource.add_resource("csv")
        csv_resource.add_method("POST", apigw.LambdaIntegration(self.drone_path_lambda))
        
        # Battery CSV endpoint
        battery_csv_resource = csv_resource.add_resource("battery").add_resource("{id}")
        battery_csv_resource.add_method("GET", apigw.LambdaIntegration(self.drone_path_lambda))
        
        # Legacy endpoint
        legacy_resource = self.drone_path_api.root.add_resource("DronePathREST")
        legacy_resource.add_method("POST", apigw.LambdaIntegration(self.drone_path_lambda))

    def _create_file_upload_endpoints(self):
        """Create file upload API endpoints"""
        # Start multipart upload
        start_upload_resource = self.file_upload_api.root.add_resource("start-multipart-upload")
        start_upload_resource.add_method("POST", apigw.LambdaIntegration(self.file_upload_lambda))
        
        # Get presigned URL
        presigned_resource = self.file_upload_api.root.add_resource("get-presigned-url")
        presigned_resource.add_method("POST", apigw.LambdaIntegration(self.file_upload_lambda))
        
        # Complete upload
        complete_resource = self.file_upload_api.root.add_resource("complete-multipart-upload")
        complete_resource.add_method("POST", apigw.LambdaIntegration(self.file_upload_lambda))
        
        # Save submission
        save_resource = self.file_upload_api.root.add_resource("save-submission")
        save_resource.add_method("POST", apigw.LambdaIntegration(self.file_upload_lambda))

    def _bucket_exists(self, bucket_name: str) -> bool:
        """Check if an S3 bucket exists"""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except Exception:
            return False

    def _bucket_has_data(self, bucket_name: str) -> bool:
        """Check if S3 bucket contains any objects"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            return 'Contents' in response and len(response['Contents']) > 0
        except Exception as e:
            print(f"⚠️  Error checking bucket data for {bucket_name}: {e}")
            return False  # Conservative approach

    def _dynamodb_table_exists(self, table_name: str) -> bool:
        """Check if a DynamoDB table exists"""
        try:
            self.dynamodb_client.describe_table(TableName=table_name)
            return True
        except Exception:
            return False

    def _dynamodb_table_has_data(self, table_name: str) -> bool:
        """Check if DynamoDB table contains any data"""
        try:
            response = self.dynamodb_client.scan(
                TableName=table_name,
                Select='COUNT',
                Limit=1
            )
            return response['Count'] > 0
        except Exception as e:
            print(f"⚠️  Error checking table data for {table_name}: {e}")
            return False  # Conservative approach

    def _migrate_dynamodb_data(self, source_table: str, target_table: str) -> bool:
        """Migrate data from source DynamoDB table to target table"""
        try:
            print(f"🔄 Starting data migration: {source_table} → {target_table}")
            
            # Wait for target table to be active
            print(f"⏳ Waiting for target table to be active: {target_table}")
            waiter = self.dynamodb_client.get_waiter('table_exists')
            waiter.wait(
                TableName=target_table,
                WaiterConfig={'Delay': 5, 'MaxAttempts': 12}  # Wait up to 1 minute
            )
            print(f"✅ Target table is active: {target_table}")
            
            # Scan all items from source table
            response = self.dynamodb_client.scan(TableName=source_table)
            items = response.get('Items', [])
            
            if not items:
                print(f"ℹ️  No data to migrate from {source_table}")
                return True
            
            print(f"📊 Found {len(items)} items to migrate")
            
            # Write items to target table in batches
            batch_size = 25  # DynamoDB batch write limit
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                write_requests = [{'PutRequest': {'Item': item}} for item in batch]
                
                self.dynamodb_client.batch_write_item(
                    RequestItems={target_table: write_requests}
                )
                print(f"✅ Migrated batch {i//batch_size + 1}/{(len(items) + batch_size - 1)//batch_size}")
            
            print(f"✅ Data migration completed: {len(items)} items migrated")
            return True
            
        except Exception as e:
            print(f"❌ Data migration failed: {e}")
            return False

    def _migrate_s3_data(self, source_bucket: str, target_bucket: str) -> bool:
        """Migrate data from source S3 bucket to target bucket"""
        try:
            print(f"🔄 Starting S3 data migration: {source_bucket} → {target_bucket}")
            
            # List all objects in source bucket
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=source_bucket)
            
            migrated_count = 0
            for page in page_iterator:
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    key = obj['Key']
                    
                    # Copy object to target bucket
                    copy_source = {'Bucket': source_bucket, 'Key': key}
                    self.s3_client.copy_object(
                        CopySource=copy_source,
                        Bucket=target_bucket,
                        Key=key
                    )
                    migrated_count += 1
                    
                    if migrated_count % 10 == 0:
                        print(f"✅ Migrated {migrated_count} objects...")
            
            print(f"✅ S3 data migration completed: {migrated_count} objects migrated")
            return True
            
        except Exception as e:
            print(f"❌ S3 data migration failed: {e}")
            return False

    def _get_or_create_s3_bucket(self, construct_id: str, preferred_name: str, fallback_name: str) -> s3.IBucket:
        """Get existing S3 bucket or create new one with enhanced data-aware logic"""
        # Check if preferred name exists - always import if it exists
        if self._bucket_exists(preferred_name):
            print(f"✅ Importing existing S3 bucket: {preferred_name}")
            imported_bucket = s3.Bucket.from_bucket_name(self, construct_id, preferred_name)
            
            # After importing, check if it's empty and if fallback has data
            if not self._bucket_has_data(preferred_name):
                if self._bucket_exists(fallback_name) and self._bucket_has_data(fallback_name):
                    print(f"🔄 Imported bucket is empty, migrating data from fallback: {fallback_name} → {preferred_name}")
                    if self._migrate_s3_data(fallback_name, preferred_name):
                        print(f"✅ Successfully migrated data into {preferred_name}")
                    else:
                        print(f"⚠️  Data migration failed, but bucket {preferred_name} was imported")
                else:
                    print(f"ℹ️  Imported bucket is empty, no fallback data available")
            
            return imported_bucket
        
        # Preferred doesn't exist, check fallback
        if self._bucket_exists(fallback_name):
            if self._bucket_has_data(fallback_name):
                print(f"🔄 Fallback bucket has data, creating preferred and migrating: {fallback_name} → {preferred_name}")
                
                # Create the preferred bucket first
                new_bucket = s3.Bucket(
                    self, construct_id,
                    bucket_name=preferred_name,
                    removal_policy=RemovalPolicy.RETAIN,
                    auto_delete_objects=False,
                    versioned=True,
                    encryption=s3.BucketEncryption.S3_MANAGED,
                    block_public_access=s3.BlockPublicAccess.BLOCK_ALL
                )
                
                # Migrate data from fallback to preferred
                if self._migrate_s3_data(fallback_name, preferred_name):
                    print(f"✅ Successfully migrated data to {preferred_name}")
                    return new_bucket
                else:
                    print(f"⚠️  Data migration failed, but bucket {preferred_name} was created")
                    return new_bucket
            else:
                print(f"ℹ️  Fallback bucket exists but is empty: {fallback_name}")
                # Create preferred bucket (both are empty)
        
        # Create new bucket with preferred name
        print(f"🆕 Creating new S3 bucket: {preferred_name}")
        return s3.Bucket(
            self, construct_id,
            bucket_name=preferred_name,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

    def _get_or_create_dynamodb_table(self, construct_id: str, preferred_name: str, fallback_name: str, 
                                     partition_key_name: str, partition_key_type: dynamodb.AttributeType,
                                     sort_key_name: str = None, sort_key_type = None) -> dynamodb.ITable:
        """Get existing DynamoDB table or create new one with enhanced data-aware logic"""
        # Check if preferred name exists - always import if it exists
        if self._dynamodb_table_exists(preferred_name):
            print(f"✅ Importing existing DynamoDB table: {preferred_name}")
            imported_table = dynamodb.Table.from_table_name(self, construct_id, preferred_name)
            
            # After importing, check if it's empty and if fallback has data
            if not self._dynamodb_table_has_data(preferred_name):
                if self._dynamodb_table_exists(fallback_name) and self._dynamodb_table_has_data(fallback_name):
                    print(f"🔄 Imported table is empty, migrating data from fallback: {fallback_name} → {preferred_name}")
                    if self._migrate_dynamodb_data(fallback_name, preferred_name):
                        print(f"✅ Successfully migrated data into {preferred_name}")
                    else:
                        print(f"⚠️  Data migration failed, but table {preferred_name} was imported")
                else:
                    print(f"ℹ️  Imported table is empty, no fallback data available")
            
            return imported_table
        
        # Preferred doesn't exist, check fallback
        if self._dynamodb_table_exists(fallback_name):
            if self._dynamodb_table_has_data(fallback_name):
                print(f"🔄 Fallback table has data, creating preferred and migrating: {fallback_name} → {preferred_name}")
                
                # Create the preferred table first
                table_props = {
                    "table_name": preferred_name,
                    "partition_key": dynamodb.Attribute(
                        name=partition_key_name,
                        type=partition_key_type
                    ),
                    "removal_policy": RemovalPolicy.RETAIN,
                    "billing_mode": dynamodb.BillingMode.PAY_PER_REQUEST
                }
                
                if sort_key_name and sort_key_type:
                    table_props["sort_key"] = dynamodb.Attribute(
                        name=sort_key_name,
                        type=sort_key_type
                    )
                
                new_table = dynamodb.Table(self, construct_id, **table_props)
                
                # Migrate data from fallback to preferred
                if self._migrate_dynamodb_data(fallback_name, preferred_name):
                    print(f"✅ Successfully migrated data to {preferred_name}")
                    return new_table
                else:
                    print(f"⚠️  Data migration failed, but table {preferred_name} was created")
                    return new_table
            else:
                print(f"ℹ️  Fallback table exists but is empty: {fallback_name}")
                # Create preferred table (both are empty)
        
        # Create new table with preferred name
        print(f"🆕 Creating new DynamoDB table: {preferred_name}")
        table_props = {
            "table_name": preferred_name,
            "partition_key": dynamodb.Attribute(
                name=partition_key_name,
                type=partition_key_type
            ),
            "removal_policy": RemovalPolicy.RETAIN,
            "billing_mode": dynamodb.BillingMode.PAY_PER_REQUEST
        }
        
        if sort_key_name and sort_key_type:
            table_props["sort_key"] = dynamodb.Attribute(
                name=sort_key_name,
                type=sort_key_type
            )
        
        return dynamodb.Table(self, construct_id, **table_props)