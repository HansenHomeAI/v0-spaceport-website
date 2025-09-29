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
    BundlingOptions,  # For installing Python dependencies
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

        # Public model delivery bucket exposed via Cloudflare routing
        self.model_delivery_bucket = self._get_or_create_public_s3_bucket(
            construct_id="SpaceportModelDeliveryBucket",
            preferred_name=f"spaceport-model-delivery-{suffix}",
            fallback_name="spaceport-model-delivery"
        )
        print(f"📦 Model delivery bucket ready: {self.model_delivery_bucket.bucket_name}")
        
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
        
        # Note: SES permissions removed - now using Resend for all email functionality
        
        # Create Lambda functions with environment-specific naming
        self.drone_path_lambda = lambda_.Function(
            self, 
            "SpaceportDronePathFunction",
            function_name=f"Spaceport-DronePathFunction-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                "lambda/drone_path",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                ),
            ),
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
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                "lambda/file_upload",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                ),
            ),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "UPLOAD_BUCKET": self.upload_bucket.bucket_name,
                "FILE_METADATA_TABLE": self.file_metadata_table.table_name,
                "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", "")
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
            code=lambda_.Code.from_asset(
                "lambda/waitlist",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                ),
            ),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "WAITLIST_TABLE_NAME": self.waitlist_table.table_name,
                "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", ""),
            }
        )

        feedback_allowed_origin = env_config.get("feedbackAllowedOrigin", "*")
        self.feedback_lambda = lambda_.Function(
            self,
            "SpaceportFeedbackFunction",
            function_name=f"Spaceport-FeedbackFunction-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                "lambda/feedback",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output",
                    ],
                ),
            ),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", ""),
                "FEEDBACK_RECIPIENTS": os.environ.get(
                    "FEEDBACK_RECIPIENTS",
                    "gabriel@spcprt.com,ethan@spcprt.com,hello@spcprt.com",
                ),
                "FEEDBACK_FROM_ADDRESS": os.environ.get(
                    "FEEDBACK_FROM_ADDRESS",
                    "Spaceport AI <hello@spcprt.com>",
                ),
                "ALLOWED_ORIGINS": feedback_allowed_origin,
            },
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
        
        # Create Waitlist API Gateway
        self.waitlist_api = apigw.RestApi(
            self,
            "SpaceportWaitlistApi",
            rest_api_name=f"spaceport-waitlist-api-{suffix}",
            description=f"Spaceport Waitlist API for {env_config['domain']}",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["*"]
            )
        )

        self.feedback_api = apigw.RestApi(
            self,
            "SpaceportFeedbackApi",
            rest_api_name=f"spaceport-feedback-api-{suffix}",
            description=f"Spaceport Feedback API for {env_config['domain']}",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["*"]
            )
        )
        
        # Create API Gateway resources and methods
        self._create_drone_path_endpoints()
        self._create_file_upload_endpoints()
        self._create_waitlist_endpoints()
        self._create_feedback_endpoints()
        
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
            "WaitlistApiUrl",
            value=f"https://{self.waitlist_api.rest_api_id}.execute-api.{region}.amazonaws.com/prod",
            description=f"Waitlist API Gateway URL for {suffix}"
        )

        CfnOutput(
            self,
            "FeedbackApiUrl",
            value=f"https://{self.feedback_api.rest_api_id}.execute-api.{region}.amazonaws.com/prod",
            description=f"Feedback API Gateway URL for {suffix}"
        )
        
        CfnOutput(
            self,
            "UploadBucketName",
            value=self.upload_bucket.bucket_name,
            description=f"Upload S3 bucket name for {suffix}"
        )

        CfnOutput(
            self,
            "ModelDeliveryBucketName",
            value=self.model_delivery_bucket.bucket_name,
            description=f"Model delivery bucket for {suffix}"
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
        battery_csv_resource.add_method("POST", apigw.LambdaIntegration(self.drone_path_lambda))
        
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

    def _create_waitlist_endpoints(self):
        """Create waitlist API endpoints"""
        # Add waitlist endpoint
        waitlist_resource = self.waitlist_api.root.add_resource("waitlist")
        waitlist_resource.add_method(
            "POST",
            apigw.LambdaIntegration(
                self.waitlist_lambda,
                proxy=True
            )
        )

    def _create_feedback_endpoints(self):
        """Create feedback API endpoints"""
        feedback_resource = self.feedback_api.root.add_resource("feedback")
        feedback_resource.add_method(
            "POST",
            apigw.LambdaIntegration(self.feedback_lambda)
        )

    def _bucket_exists(self, bucket_name: str) -> bool:
        """Check if an S3 bucket exists"""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except Exception:
            return False

    def _dynamodb_table_exists(self, table_name: str) -> bool:
        """Check if a DynamoDB table exists"""
        try:
            self.dynamodb_client.describe_table(TableName=table_name)
            return True
        except Exception:
            return False

    def _get_or_create_s3_bucket(self, construct_id: str, preferred_name: str, fallback_name: str) -> s3.IBucket:
        """Get existing S3 bucket or create new one"""
        # First try preferred name (with environment suffix)
        if self._bucket_exists(preferred_name):
            print(f"Importing existing S3 bucket: {preferred_name}")
            return s3.Bucket.from_bucket_name(self, construct_id, preferred_name)
        
        # Then try fallback name (without suffix)
        if self._bucket_exists(fallback_name):
            print(f"Importing existing S3 bucket: {fallback_name}")
            return s3.Bucket.from_bucket_name(self, construct_id, fallback_name)
        
        # Create new bucket with preferred name
        print(f"Creating new S3 bucket: {preferred_name}")
        return s3.Bucket(
            self, construct_id,
            bucket_name=preferred_name,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

    def _get_or_create_public_s3_bucket(self, construct_id: str, preferred_name: str, fallback_name: str) -> s3.IBucket:
        """Create or import an S3 bucket with public read for model delivery."""
        candidates = [preferred_name, fallback_name]
        bucket: s3.IBucket
        bucket_name: str

        for candidate in candidates:
            if self._bucket_exists(candidate):
                print(f"Importing existing public S3 bucket: {candidate}")
                bucket = s3.Bucket.from_bucket_name(self, construct_id, candidate)
                bucket_name = candidate
                break
        else:
            print(f"Creating new public S3 bucket: {preferred_name}")
            bucket = s3.Bucket(
                self,
                construct_id,
                bucket_name=preferred_name,
                encryption=s3.BucketEncryption.S3_MANAGED,
                removal_policy=RemovalPolicy.RETAIN,
                auto_delete_objects=False,
                public_read_access=False,
                block_public_access=s3.BlockPublicAccess(
                    block_public_acls=False,
                    ignore_public_acls=False,
                    block_public_policy=False,
                    restrict_public_buckets=False,
                ),
                object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            )
            bucket_name = preferred_name

        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.AnyPrincipal()],
                actions=["s3:GetObject"],
                resources=[bucket.arn_for_objects("*")],
            )
        )

        return bucket

    def _get_or_create_dynamodb_table(self, construct_id: str, preferred_name: str, fallback_name: str, 
                                     partition_key_name: str, partition_key_type: dynamodb.AttributeType) -> dynamodb.ITable:
        """Get existing DynamoDB table or create new one"""
        # First try preferred name (with environment suffix)
        if self._dynamodb_table_exists(preferred_name):
            print(f"Importing existing DynamoDB table: {preferred_name}")
            return dynamodb.Table.from_table_name(self, construct_id, preferred_name)
        
        # Then try fallback name (without suffix)
        if self._dynamodb_table_exists(fallback_name):
            print(f"Importing existing DynamoDB table: {fallback_name}")
            return dynamodb.Table.from_table_name(self, construct_id, fallback_name)
        
        # Create new table with preferred name
        print(f"Creating new DynamoDB table: {preferred_name}")
        return dynamodb.Table(
            self, construct_id,
            table_name=preferred_name,
            partition_key=dynamodb.Attribute(
                name=partition_key_name,
                type=partition_key_type
            ),
            removal_policy=RemovalPolicy.RETAIN,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )
