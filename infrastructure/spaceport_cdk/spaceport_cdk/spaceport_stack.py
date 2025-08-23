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

class SpaceportStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a CloudFormation parameter for the API key
        api_key_param = CfnParameter(
            self, "GoogleMapsApiKey",
            type="String",
            description="Google Maps API Key",
            no_echo=True  # This will mask the value in CloudFormation
        )

        # Import existing S3 bucket to avoid conflicts
        upload_bucket = s3.Bucket.from_bucket_name(
            self,
            "Spaceport-UploadBucket",
            "spaceport-uploads"
        )
        
        # Import existing DynamoDB tables to avoid conflicts
        file_metadata_table = dynamodb.Table.from_table_name(
            self,
            "FileMetadataTable",
            "Spaceport-FileMetadata"
        )

        drone_path_table = dynamodb.Table.from_table_name(
            self,
            "DroneFlightPathsTable",
            "Spaceport-DroneFlightPaths"
        )
        
        # Import existing waitlist table
        waitlist_table = dynamodb.Table.from_table_name(
            self,
            "WaitlistTable",
            "Spaceport-Waitlist"
        )
        
        # Create Lambda execution role with permissions to S3 and DynamoDB
        lambda_role = iam.Role(
            self, 
            "Spaceport-LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Add permissions to the Lambda role
        lambda_role.add_to_policy(
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
                    f"arn:aws:s3:::{upload_bucket.bucket_name}",
                    f"arn:aws:s3:::{upload_bucket.bucket_name}/*"
                ]
            )
        )
        
        # Add permissions for ML bucket (CSV uploads)
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:DeleteObject"
                ],
                resources=[
                    "arn:aws:s3:::spaceport-ml-processing",
                    "arn:aws:s3:::spaceport-ml-processing/*"
                ]
            )
        )
        file_metadata_table.grant_read_write_data(lambda_role)
        drone_path_table.grant_read_write_data(lambda_role)
        waitlist_table.grant_read_write_data(lambda_role)
        
        # Add SES permissions for sending emails
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                resources=["*"]  # You may want to restrict this to specific email addresses
            )
        )
        
        # Lambda directory not needed since we're importing existing functions
        # lambda_dir = os.path.join(os.path.dirname(__file__), "..", "lambda")
        
        # Import existing Lambda function for drone path generation
        drone_path_lambda = lambda_.Function.from_function_name(
            self, 
            "Spaceport-DronePathFunction",
            "Spaceport-DronePathFunction"
        )
        
        # Import existing Lambda function for file upload
        file_upload_lambda = lambda_.Function.from_function_name(
            self, 
            "Spaceport-FileUploadFunction",
            "Spaceport-FileUploadFunction"
        )
        
        # Import existing Lambda function for CSV upload URL generation
        csv_upload_lambda = lambda_.Function.from_function_name(
            self, 
            "Spaceport-CsvUploadFunction",
            "Spaceport-CsvUploadFunction"
        )
        
        # Import existing Lambda function for waitlist submissions
        waitlist_lambda = lambda_.Function.from_function_name(
            self, 
            "Spaceport-WaitlistFunction",
            "Spaceport-WaitlistFunction"
        )
        
        # ========== API GATEWAY CONFIGURATION ==========
        # Import existing API Gateway for drone path generation
        drone_path_api = apigw.RestApi.from_rest_api_id(
            self,
            "Spaceport-DronePathApi",
            "0r3y4bx7lc"  # Use the existing production API Gateway ID
        )
        
        # Import existing API Gateway for file upload operations
        file_upload_api = apigw.RestApi.from_rest_api_id(
            self,
            "Spaceport-FileUploadApi",
            "rf3fnnejg2"  # Use the existing production API Gateway ID
        )
        
        # ========== OUTPUTS ==========
        CfnOutput(
            self,
            "DronePathApiUrl",
            value=f"https://0r3y4bx7lc.execute-api.us-west-2.amazonaws.com/prod",
            description="Drone Path API Gateway URL"
        )
        
        CfnOutput(
            self,
            "FileUploadApiUrl",
            value=f"https://rf3fnnejg2.execute-api.us-west-2.amazonaws.com/prod",
            description="File Upload API Gateway URL"
        )

        # Authentication removed from this stack. It will be managed by a dedicated AuthStack.