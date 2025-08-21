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
    BundlingOptions,
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
        
        # Get the lambda directory absolute path - fixed to point to correct location
        lambda_dir = os.path.join(os.path.dirname(__file__), "..", "lambda")
        
        # Create Lambda function for drone path generation with bundled dependencies
        drone_path_lambda = lambda_.Function(
            self, 
            "Spaceport-DronePathFunction",
            function_name="Spaceport-DronePathFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset(
                os.path.join(lambda_dir, "drone_path"),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ]
                )
            ),
            handler="lambda_function.lambda_handler",
            environment={
                "DYNAMODB_TABLE_NAME": drone_path_table.table_name,
                # Use the CloudFormation parameter value
                "GOOGLE_MAPS_API_KEY": api_key_param.value_as_string
            },
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512  # Increase from default 128MB to handle elevation API calls and terrain avoidance
        )
        
        # Create Lambda function for file upload
        file_upload_lambda = lambda_.Function(
            self, 
            "Spaceport-FileUploadFunction",
            function_name="Spaceport-FileUploadFunction",
            runtime=lambda_.Runtime.NODEJS_18_X,
            code=lambda_.Code.from_asset(os.path.join(lambda_dir, "file_upload")),
            handler="index.handler",
            environment={
                "BUCKET_NAME": upload_bucket.bucket_name,
                "METADATA_TABLE_NAME": file_metadata_table.table_name
            },
            role=lambda_role,
            timeout=Duration.seconds(30)
        )
        
        # Create Lambda function for CSV upload URL generation
        csv_upload_lambda = lambda_.Function(
            self, 
            "Spaceport-CsvUploadFunction",
            function_name="Spaceport-CsvUploadFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset(os.path.join(lambda_dir, "csv_upload_url")),
            handler="lambda_function.lambda_handler",
            environment={
                "ML_BUCKET": "spaceport-ml-processing"
            },
            role=lambda_role,
            timeout=Duration.seconds(30)
        )
        
        # Create Lambda function for waitlist submissions
        waitlist_lambda = lambda_.Function(
            self, 
            "Spaceport-WaitlistFunction",
            function_name="Spaceport-WaitlistFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset(
                os.path.join(lambda_dir, "waitlist"),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ]
                )
            ),
            handler="lambda_function.lambda_handler",
            environment={
                "WAITLIST_TABLE_NAME": waitlist_table.table_name
            },
            role=lambda_role,
            timeout=Duration.seconds(30)
        )
        
        # Create API Gateway for drone path generation
        drone_path_api = apigw.RestApi(
            self, 
            "Spaceport-DronePathApi",
            rest_api_name="Spaceport-DronePathApi",
            description="API for generating drone flight paths",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS
            )
        )
        
        drone_path_resource = drone_path_api.root.add_resource("DronePathREST")
        drone_path_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                drone_path_lambda,
                proxy=True,
                integration_responses=[
                    {
                        "statusCode": "200",
                        "responseParameters": {
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        }
                    },
                    {
                        "statusCode": "400",
                        "responseParameters": {
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        }
                    },
                    {
                        "statusCode": "500",
                        "responseParameters": {
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        },
                        "selectionPattern": ".*"
                    }
                ]
            ),
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                ),
                apigw.MethodResponse(
                    status_code="400",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                ),
                apigw.MethodResponse(
                    status_code="500",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ]
        )
        
        # Add enhanced drone path API endpoints with CORS
        api_resource = drone_path_api.root.add_resource("api")
        
        # /api/optimize-spiral endpoint
        optimize_spiral_resource = api_resource.add_resource("optimize-spiral")
        optimize_spiral_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                drone_path_lambda,
                proxy=True
            )
        )
        
        # /api/elevation endpoint  
        elevation_resource = api_resource.add_resource("elevation")
        elevation_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                drone_path_lambda,
                proxy=True
            )
        )
        
        # /api/csv endpoint
        csv_resource = api_resource.add_resource("csv")
        csv_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                drone_path_lambda,
                proxy=True
            )
        )
        
        # /api/csv/battery/{id} endpoint
        battery_resource = csv_resource.add_resource("battery")
        battery_id_resource = battery_resource.add_resource("{id}")
        battery_id_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                drone_path_lambda,
                proxy=True
            )
        )
        
        # Create API Gateway for file upload
        file_upload_api = apigw.RestApi(
            self, 
            "Spaceport-FileUploadApi",
            rest_api_name="Spaceport-FileUploadApi",
            description="API for file upload operations",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "X-Amz-Date",
                    "Authorization",
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                    "X-Amz-User-Agent"
                ],
                allow_credentials=True,
                max_age=Duration.seconds(300)
            )
        )
        
        # Add resources and methods for file upload API with proper CORS
        start_upload_resource = file_upload_api.root.add_resource("start-multipart-upload")
        start_upload_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                file_upload_lambda,
                proxy=True
            )
        )
        
        get_presigned_url_resource = file_upload_api.root.add_resource("get-presigned-url")
        get_presigned_url_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                file_upload_lambda,
                proxy=True
            )
        )
        
        complete_upload_resource = file_upload_api.root.add_resource("complete-multipart-upload")
        complete_upload_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                file_upload_lambda,
                proxy=True
            )
        )
        
        save_submission_resource = file_upload_api.root.add_resource("save-submission")
        save_submission_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                file_upload_lambda,
                proxy=True
            )
        )
        
        # Add CSV upload URL endpoint
        csv_upload_resource = file_upload_api.root.add_resource("get-csv-upload-url")
        csv_upload_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                csv_upload_lambda,
                proxy=True
            )
        )
        
        # Add waitlist endpoint
        waitlist_resource = file_upload_api.root.add_resource("waitlist")
        waitlist_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                waitlist_lambda,
                proxy=True
            )
        )
        
        # Output the API URLs
        CfnOutput(
            self, 
            "DronePathApiUrl",
            value=f"{drone_path_api.url}DronePathREST"
        )
        
        CfnOutput(
            self, 
            "FileUploadApiUrl",
            value=file_upload_api.url
        ) 

        # Authentication removed from this stack. It will be managed by a dedicated AuthStack.