from aws_cdk import (
    core as cdk,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_ssm as ssm,
)
from constructs import Construct

class SpaceportStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create an S3 bucket for file uploads
        upload_bucket = s3.Bucket(
            self, 
            "Spaceport-UploadBucket",
            bucket_name="spaceport-uploads",
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET, s3.HttpMethods.POST],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    exposed_headers=["ETag"]
                )
            ],
            removal_policy=cdk.RemovalPolicy.RETAIN
        )
        
        # Create DynamoDB table for file metadata
        file_metadata_table = dynamodb.Table(
            self, 
            "Spaceport-FileMetadata",
            table_name="Spaceport-FileMetadata",
            partition_key=dynamodb.Attribute(
                name="id", 
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.RETAIN
        )
        
        # Create DynamoDB table for drone flight paths
        drone_path_table = dynamodb.Table(
            self, 
            "Spaceport-DroneFlightPaths",
            table_name="Spaceport-DroneFlightPaths",
            partition_key=dynamodb.Attribute(
                name="id", 
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.RETAIN
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
        upload_bucket.grant_read_write(lambda_role)
        file_metadata_table.grant_read_write_data(lambda_role)
        drone_path_table.grant_read_write_data(lambda_role)
        
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
        
        # Create Parameter Store parameter for Google Maps API key
        google_maps_api_key = ssm.StringParameter(
            self,
            "Spaceport-GoogleMapsApiKey",
            parameter_name="/Spaceport/GoogleMapsApiKey",
            string_value="AIzaSyDkdnE1weVG38PSUO5CWFneFjH16SPYZHU",
            description="Google Maps API key for elevation data",
            tier=ssm.ParameterTier.STANDARD
        )
        
        # Add permissions to the Lambda role to read the parameter
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[google_maps_api_key.parameter_arn]
            )
        )
        
        # Create Lambda function for drone path generation
        drone_path_lambda = lambda_.Function(
            self, 
            "Spaceport-DronePathFunction",
            function_name="Spaceport-DronePathFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset("lambda/drone_path"),
            handler="lambda_function.handler",
            environment={
                "DYNAMODB_TABLE_NAME": drone_path_table.table_name,
                "GOOGLE_MAPS_API_KEY_PARAM": google_maps_api_key.parameter_name
            },
            role=lambda_role,
            timeout=cdk.Duration.seconds(30)
        )
        
        # Create Lambda functions for multipart upload
        start_upload_lambda = lambda_.Function(
            self, 
            "Spaceport-StartUploadFunction",
            function_name="Spaceport-StartUploadFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset("lambda/file_upload"),
            handler="start_upload.handler",
            environment={
                "BUCKET_NAME": upload_bucket.bucket_name,
                "METADATA_TABLE_NAME": file_metadata_table.table_name
            },
            role=lambda_role,
            timeout=cdk.Duration.seconds(10)
        )
        
        get_presigned_url_lambda = lambda_.Function(
            self, 
            "Spaceport-GetPresignedUrlFunction",
            function_name="Spaceport-GetPresignedUrlFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset("lambda/file_upload"),
            handler="get_presigned_url.handler",
            environment={
                "BUCKET_NAME": upload_bucket.bucket_name
            },
            role=lambda_role,
            timeout=cdk.Duration.seconds(10)
        )
        
        complete_upload_lambda = lambda_.Function(
            self, 
            "Spaceport-CompleteUploadFunction",
            function_name="Spaceport-CompleteUploadFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset("lambda/file_upload"),
            handler="complete_upload.handler",
            environment={
                "BUCKET_NAME": upload_bucket.bucket_name
            },
            role=lambda_role,
            timeout=cdk.Duration.seconds(30)
        )
        
        save_submission_lambda = lambda_.Function(
            self, 
            "Spaceport-SaveSubmissionFunction",
            function_name="Spaceport-SaveSubmissionFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset("lambda/file_upload"),
            handler="save_submission.handler",
            environment={
                "METADATA_TABLE_NAME": file_metadata_table.table_name
            },
            role=lambda_role,
            timeout=cdk.Duration.seconds(10)
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
            apigw.LambdaIntegration(drone_path_lambda),
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ]
        )
        
        # Create API Gateway for file upload
        file_upload_api = apigw.RestApi(
            self, 
            "Spaceport-FileUploadApi",
            rest_api_name="Spaceport-FileUploadApi",
            description="API for file upload operations",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS
            )
        )
        
        # Add resources and methods for file upload API
        start_upload_resource = file_upload_api.root.add_resource("start-multipart-upload")
        start_upload_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(start_upload_lambda)
        )
        
        get_presigned_url_resource = file_upload_api.root.add_resource("get-presigned-url")
        get_presigned_url_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(get_presigned_url_lambda)
        )
        
        complete_upload_resource = file_upload_api.root.add_resource("complete-multipart-upload")
        complete_upload_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(complete_upload_lambda)
        )
        
        save_submission_resource = file_upload_api.root.add_resource("save-submission")
        save_submission_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(save_submission_lambda)
        )
        
        # Output the API URLs
        cdk.CfnOutput(
            self, 
            "DronePathApiUrl",
            value=f"{drone_path_api.url}DronePathREST"
        )
        
        cdk.CfnOutput(
            self, 
            "FileUploadApiUrl",
            value=file_upload_api.url
        ) 