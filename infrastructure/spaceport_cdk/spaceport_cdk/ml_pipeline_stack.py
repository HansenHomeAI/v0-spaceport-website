from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_s3 as s3,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    aws_sagemaker as sagemaker,
    aws_ecr as ecr,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    RemovalPolicy,
    Duration,
    CfnOutput,
    aws_ec2 as ec2,
)
from constructs import Construct
import os
import json
import boto3


class MLPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, env_config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Environment configuration
        self.env_config = env_config
        suffix = env_config['resourceSuffix']
        region = env_config['region']
        
        # Initialize AWS clients for resource checking
        self.s3_client = boto3.client('s3', region_name=region)
        self.ecr_client = boto3.client('ecr', region_name=region)
        self.cloudwatch_client = boto3.client('cloudwatch', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        
        # Track resources for validation
        self._created_resources = []
        self._imported_resources = []
        
        # Run robustness validations
        self._validate_environment_config()
        self._validate_resource_naming_conventions()

        # ========== S3 BUCKETS ==========
        # ML bucket - this stack owns this bucket
        ml_bucket = self._get_or_create_s3_bucket(
            construct_id="SpaceportMLBucket",
            preferred_name=f"spaceport-ml-processing-{suffix}",
            fallback_name="spaceport-ml-processing"
        )
        print(f"🆕 ML Pipeline stack owns ML bucket: {ml_bucket.bucket_name}")

        # Import upload bucket from main Spaceport stack - DO NOT CREATE
        # This bucket is owned by the main Spaceport stack, we just reference it
        upload_bucket = s3.Bucket.from_bucket_name(
            self, "ImportedUploadBucket",
            f"spaceport-uploads-{suffix}"
        )
        print(f"✅ Importing upload bucket from main stack: spaceport-uploads-{suffix}")
        self._imported_resources.append({"type": "S3::Bucket", "name": f"spaceport-uploads-{suffix}", "action": "imported_from_main_stack"})

        # ========== ECR REPOSITORIES ==========
        # Dynamic ECR repositories - import if exist, create if not
        sfm_repo = self._get_or_create_ecr_repo(
            construct_id="SfMRepository",
            preferred_name=f"spaceport/sfm-{suffix}",
            fallback_name="spaceport/sfm"
        )

        gaussian_repo = self._get_or_create_ecr_repo(
            construct_id="GaussianRepository",
            preferred_name=f"spaceport/3dgs-{suffix}",
            fallback_name="spaceport/3dgs"
        )

        compressor_repo = self._get_or_create_ecr_repo(
            construct_id="CompressorRepository",
            preferred_name=f"spaceport/compressor-{suffix}",
            fallback_name="spaceport/compressor"
        )

        # ========== IAM ROLES ==========
        # SageMaker execution role with environment-specific naming
        sagemaker_role = iam.Role(
            self, "SageMakerExecutionRole",
            role_name=f"Spaceport-SageMaker-Role-{suffix}",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess")
            ]
        )

        # Step Functions execution role with environment-specific naming
        step_functions_role = iam.Role(
            self, "StepFunctionsExecutionRole",
            role_name=f"Spaceport-StepFunctions-Role-{suffix}",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            inline_policies={
                "SageMakerPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "sagemaker:CreateProcessingJob",
                                "sagemaker:CreateTrainingJob",
                                "sagemaker:DescribeProcessingJob",
                                "sagemaker:DescribeTrainingJob",
                                "sagemaker:StopProcessingJob",
                                "sagemaker:StopTrainingJob"
                            ],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            actions=["iam:PassRole"],
                            resources=[sagemaker_role.role_arn]
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "lambda:InvokeFunction"
                            ],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                                "logs:DescribeLogGroups",
                                "logs:DescribeLogStreams"
                            ],
                            resources=["*"]
                        )
                    ]
                )
            }
        )

        # Lambda execution role for API with environment-specific naming
        lambda_role = iam.Role(
            self, "MLLambdaExecutionRole",
            role_name=f"Spaceport-ML-Lambda-Role-{suffix}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "StepFunctionsPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["states:StartExecution"],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "s3:GetObject",
                                "s3:HeadObject",
                                "s3:PutObject"
                            ],
                            resources=[
                                f"{upload_bucket.bucket_arn}/*",
                                f"{ml_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                )
            }
        )

        # Notification Lambda role with environment-specific naming
        notification_lambda_role = iam.Role(
            self, "NotificationLambdaRole",
            role_name=f"Spaceport-Notification-Lambda-Role-{suffix}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "SESPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "ses:SendEmail",
                                "ses:SendRawEmail"
                            ],
                            resources=["*"]
                        )
                    ]
                )
            }
        )

        # ========== CLOUDWATCH LOG GROUPS ==========
        # Log groups for each component with environment-specific naming
        sfm_log_group = logs.LogGroup(
            self, "SfMLogGroup",
            log_group_name=f"/aws/sagemaker/processing-jobs/sfm-{suffix}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        gaussian_log_group = logs.LogGroup(
            self, "GaussianLogGroup", 
            log_group_name=f"/aws/sagemaker/training-jobs/3dgs-{suffix}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        compressor_log_group = logs.LogGroup(
            self, "CompressorLogGroup",
            log_group_name=f"/aws/sagemaker/processing-jobs/compressor-{suffix}", 
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        step_functions_log_group = logs.LogGroup(
            self, "StepFunctionsLogGroup",
            log_group_name=f"/aws/stepfunctions/ml-pipeline-{suffix}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        # ========== LAMBDA FUNCTIONS ==========
        # Create Lambda functions with environment-specific naming

        # Create Lambda for starting ML jobs (will update environment after Step Function creation)
        start_job_lambda = lambda_.Function(
            self, "StartMLJobFunction",
            function_name=f"Spaceport-StartMLJob-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/start_ml_job"),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "ML_BUCKET": ml_bucket.bucket_name,
            }
        )

        # Create Notification Lambda
        notification_lambda = lambda_.Function(
            self, "NotificationFunction",
            function_name=f"Spaceport-MLNotification-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("lambda/ml_notification"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "ML_BUCKET": ml_bucket.bucket_name,
                "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", ""),
            }
        )

        # ========== STEP FUNCTIONS DEFINITION ==========
        # Define the Step Functions workflow
        
        # SfM Processing Job - Using CallAwsService since SageMakerCreateProcessingJob doesn't exist in CDK v2
        sfm_job = sfn_tasks.CallAwsService(
            self, "SfMProcessingJob",
            service="sagemaker",
            action="createProcessingJob",
            parameters={
                "ProcessingJobName": sfn.JsonPath.format("{}-sfm", sfn.JsonPath.string_at("$.jobName")),
                "AppSpecification": {
                    "ImageUri": sfn.JsonPath.string_at("$.sfmImageUri"),
                    "ContainerEntrypoint": ["/opt/ml/code/run_sfm.sh"]
                },
                "ProcessingResources": {
                    "ClusterConfig": {
                        "InstanceCount": 1,
                        "InstanceType": "ml.c6i.2xlarge",
                        "VolumeSizeInGB": 100
                    }
                },
                "ProcessingInputs.$": "$.sfmProcessingInputs",
                "ProcessingOutputConfig": {
                    "Outputs": [{
                        "OutputName": "colmap-output",
                        "AppManaged": False,
                        "S3Output": {
                            "S3Uri": sfn.JsonPath.string_at("$.colmapOutputS3Uri"),
                            "LocalPath": "/opt/ml/processing/output",
                            "S3UploadMode": "EndOfJob"
                        }
                    }]
                },
                "RoleArn": sagemaker_role.role_arn
            },
            iam_resources=[
                f"arn:aws:sagemaker:{self.region}:{self.account}:processing-job/*"
            ],
            result_path="$.sfmResult"
        )

        # Wait for SfM processing job to complete
        wait_for_sfm = sfn_tasks.CallAwsService(
            self, "WaitForSfMCompletion",
            service="sagemaker",
            action="describeProcessingJob",
            parameters={
                "ProcessingJobName": sfn.JsonPath.format("{}-sfm", sfn.JsonPath.string_at("$.jobName"))
            },
            iam_resources=[
                f"arn:aws:sagemaker:{self.region}:{self.account}:processing-job/*"
            ],
            result_path="$.sfmStatus"
        )

        # Check if SfM job is complete
        sfm_choice = sfn.Choice(self, "IsSfMComplete")
        
        # Wait state for polling
        sfm_wait = sfn.Wait(
            self, "WaitForSfM",
            time=sfn.WaitTime.duration(Duration.seconds(60))  # Wait 60 seconds between polls
        )

        # NerfStudio 3DGS Training Job - Vincent Woo's Sutro Tower Methodology
        gaussian_job = sfn_tasks.CallAwsService(
            self, "GaussianTrainingJob",
            service="sagemaker",
            action="createTrainingJob",
            parameters={
                "TrainingJobName": sfn.JsonPath.format("{}-3dgs", sfn.JsonPath.string_at("$.jobName")),
                "AlgorithmSpecification": {
                    "TrainingImage": sfn.JsonPath.string_at("$.gaussianImageUri"),
                    "TrainingInputMode": "File"
                },
                "InputDataConfig": [{
                    "ChannelName": "training",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            "S3Uri": sfn.JsonPath.string_at("$.colmapOutputS3Uri"),
                            "S3DataDistributionType": "FullyReplicated"
                        }
                    }
                }],
                "OutputDataConfig": {
                    "S3OutputPath": sfn.JsonPath.string_at("$.gaussianOutputS3Uri")
                },
                "ResourceConfig": {
                    "InstanceCount": 1,
                    "InstanceType": "ml.g5.xlarge",  # A10G GPU - supports gsplat labeled_partition
                    "VolumeSizeInGB": 100
                },
                "StoppingCondition": {
                    "MaxRuntimeInSeconds": 7200  # 2 hours for real training
                },
                "RoleArn": sagemaker_role.role_arn,
                "Environment": {
                    # Vincent Woo's NerfStudio Methodology - Core Parameters
                    # Note: All values must be strings for SageMaker environment variables
                    "MAX_ITERATIONS": sfn.JsonPath.format("{}", sfn.JsonPath.string_at("$.MAX_ITERATIONS")),
                    "TARGET_PSNR": sfn.JsonPath.format("{}", sfn.JsonPath.string_at("$.TARGET_PSNR")),
                    "LOG_INTERVAL": sfn.JsonPath.format("{}", sfn.JsonPath.string_at("$.LOG_INTERVAL")),
                    
                    # Vincent Woo's Key Features
                    "MODEL_VARIANT": sfn.JsonPath.format("{}", sfn.JsonPath.string_at("$.MODEL_VARIANT")),  # splatfacto vs splatfacto-big
                    "SH_DEGREE": sfn.JsonPath.format("{}", sfn.JsonPath.string_at("$.SH_DEGREE")),          # Industry standard: 3
                    "BILATERAL_PROCESSING": sfn.JsonPath.format("{}", sfn.JsonPath.string_at("$.BILATERAL_PROCESSING")),  # Vincent's innovation
                    
                    # NerfStudio Framework Configuration
                    "FRAMEWORK": "nerfstudio",
                    "METHODOLOGY": "vincent_woo_sutro_tower",
                    "LICENSE": "apache_2_0",
                    
                    # Quality and Performance Settings
                    "OUTPUT_FORMAT": "ply",
                    "SOGS_COMPATIBLE": "true",
                    "COMMERCIAL_LICENSE": "true"
                }
            },
            iam_resources=[
                f"arn:aws:sagemaker:{self.region}:{self.account}:training-job/*"
            ],
            result_path="$.gaussianResult"
        )

        # Wait for Gaussian training job to complete
        wait_for_gaussian = sfn_tasks.CallAwsService(
            self, "WaitForGaussianCompletion",
            service="sagemaker",
            action="describeTrainingJob",
            parameters={
                "TrainingJobName": sfn.JsonPath.format("{}-3dgs", sfn.JsonPath.string_at("$.jobName"))
            },
            iam_resources=[
                f"arn:aws:sagemaker:{self.region}:{self.account}:training-job/*"
            ],
            result_path="$.gaussianStatus"
        )

        # Check if Gaussian job is complete
        gaussian_choice = sfn.Choice(self, "IsGaussianComplete")
        
        # Wait state for polling
        gaussian_wait = sfn.Wait(
            self, "WaitForGaussian",
            time=sfn.WaitTime.duration(Duration.seconds(120))  # Wait 2 minutes between polls for longer training jobs
        )

        # Compression Job - Using CallAwsService since SageMakerCreateProcessingJob doesn't exist in CDK v2
        compression_job = sfn_tasks.CallAwsService(
            self, "CompressionJob",
            service="sagemaker",
            action="createProcessingJob",
            parameters={
                "ProcessingJobName": sfn.JsonPath.format("{}-compression", sfn.JsonPath.string_at("$.jobName")),
                "AppSpecification": {
                    "ImageUri": sfn.JsonPath.string_at("$.compressorImageUri"),
                    "ContainerEntrypoint": ["python3", "compress.py"]
                },
                "ProcessingResources": {
                    "ClusterConfig": {
                        "InstanceCount": 1,
                        "InstanceType": "ml.g4dn.xlarge",  # T4 GPU - compatible with SOGS compression
                        "VolumeSizeInGB": 50
                    }
                },
                "ProcessingInputs": [{
                    "InputName": "gaussian-model",
                    "AppManaged": False,
                    "S3Input": {
                        "S3Uri": sfn.JsonPath.string_at("$.gaussianOutputS3Uri"),
                        "LocalPath": "/opt/ml/processing/input",
                        "S3DataType": "S3Prefix",
                        "S3InputMode": "File"
                    }
                }],
                "ProcessingOutputConfig": {
                    "Outputs": [{
                        "OutputName": "compressed-model",
                        "AppManaged": False,
                        "S3Output": {
                            "S3Uri": sfn.JsonPath.string_at("$.compressedOutputS3Uri"),
                            "LocalPath": "/opt/ml/processing/output",
                            "S3UploadMode": "EndOfJob"
                        }
                    }]
                },
                "RoleArn": sagemaker_role.role_arn
            },
            iam_resources=[
                f"arn:aws:sagemaker:{self.region}:{self.account}:processing-job/*"
            ],
            result_path="$.compressionResult"
        )

        # Wait for Compression job to complete
        wait_for_compression = sfn_tasks.CallAwsService(
            self, "WaitForCompressionCompletion",
            service="sagemaker",
            action="describeProcessingJob",
            parameters={
                "ProcessingJobName": sfn.JsonPath.format("{}-compression", sfn.JsonPath.string_at("$.jobName"))
            },
            iam_resources=[
                f"arn:aws:sagemaker:{self.region}:{self.account}:processing-job/*"
            ],
            result_path="$.compressionStatus"
        )

        # Check if Compression job is complete
        compression_choice = sfn.Choice(self, "IsCompressionComplete")
        
        # Wait state for polling
        compression_wait = sfn.Wait(
            self, "WaitForCompression",
            time=sfn.WaitTime.duration(Duration.seconds(60))  # Wait 60 seconds between polls
        )

        # Notification step
        notify_user = sfn_tasks.LambdaInvoke(
            self, "NotifyUser",
            lambda_function=notification_lambda,
            payload=sfn.TaskInput.from_object({
                "jobId": sfn.JsonPath.string_at("$.jobId"),
                "email": sfn.JsonPath.string_at("$.email"),
                "s3Url": sfn.JsonPath.string_at("$.s3Url"),
                "compressedOutputS3Uri": sfn.JsonPath.string_at("$.compressedOutputS3Uri"),
                "status": "completed"
            }),
            result_path="$.notificationResult"
        )

        # Error notification - handle different error structures
        notify_error = sfn_tasks.LambdaInvoke(
            self, "NotifyError",
            lambda_function=notification_lambda,
            payload=sfn.TaskInput.from_object({
                "jobId": sfn.JsonPath.string_at("$.jobId"),
                "email": sfn.JsonPath.string_at("$.email"),
                "s3Url": sfn.JsonPath.string_at("$.s3Url"),
                "status": "failed",
                # Pass the entire state so Lambda can extract the right error
                "state": sfn.JsonPath.entire_payload
            })
        )

        # Add error handling to each job
        sfm_job_with_catch = sfm_job.add_catch(
            notify_error,
            errors=["States.ALL"],
            result_path="$.error"
        )

        wait_for_sfm_with_catch = wait_for_sfm.add_catch(
            notify_error,
            errors=["States.ALL"],
            result_path="$.error"
        )

        gaussian_job_with_catch = gaussian_job.add_catch(
            notify_error,
            errors=["States.ALL"],
            result_path="$.error"
        )

        wait_for_gaussian_with_catch = wait_for_gaussian.add_catch(
            notify_error,
            errors=["States.ALL"],
            result_path="$.error"
        )

        compression_job_with_catch = compression_job.add_catch(
            notify_error,
            errors=["States.ALL"],
            result_path="$.error"
        )

        wait_for_compression_with_catch = wait_for_compression.add_catch(
            notify_error,
            errors=["States.ALL"],
            result_path="$.error"
        )

        # Build the workflow with proper job completion waiting
        # SfM workflow: Start job -> Wait and poll until complete
        sfm_polling_loop = sfm_choice.when(
            sfn.Condition.string_equals("$.sfmStatus.ProcessingJobStatus", "Completed"),
            gaussian_job_with_catch
        ).when(
            sfn.Condition.string_equals("$.sfmStatus.ProcessingJobStatus", "Failed"),
            notify_error
        ).otherwise(
            sfm_wait.next(wait_for_sfm_with_catch)
        )

        # Gaussian workflow: Start job -> Wait and poll until complete  
        gaussian_polling_loop = gaussian_choice.when(
            sfn.Condition.string_equals("$.gaussianStatus.TrainingJobStatus", "Completed"),
            compression_job_with_catch
        ).when(
            sfn.Condition.string_equals("$.gaussianStatus.TrainingJobStatus", "Failed"),
            notify_error
        ).otherwise(
            gaussian_wait.next(wait_for_gaussian_with_catch)
        )

        # Compression workflow: Start job -> Wait and poll until complete
        compression_polling_loop = compression_choice.when(
            sfn.Condition.string_equals("$.compressionStatus.ProcessingJobStatus", "Completed"),
            notify_user
        ).when(
            sfn.Condition.string_equals("$.compressionStatus.ProcessingJobStatus", "Failed"),
            notify_error
        ).otherwise(
            compression_wait.next(wait_for_compression_with_catch)
        )

        # Connect the polling loops to the choices
        wait_for_sfm_with_catch.next(sfm_polling_loop)
        wait_for_gaussian_with_catch.next(gaussian_polling_loop)
        wait_for_compression_with_catch.next(compression_polling_loop)

        # Create pipeline step selector choice
        pipeline_step_choice = sfn.Choice(self, "PipelineStepChoice")
        
        # Define workflows for each starting point
        sfm_workflow = sfm_job_with_catch.next(wait_for_sfm_with_catch)
        gaussian_workflow = gaussian_job_with_catch.next(wait_for_gaussian_with_catch)
        compression_workflow = compression_job_with_catch.next(wait_for_compression_with_catch)
        
        # Pipeline step conditional logic
        definition = pipeline_step_choice.when(
            sfn.Condition.string_equals("$.pipelineStep", "sfm"),
            sfm_workflow
        ).when(
            sfn.Condition.string_equals("$.pipelineStep", "3dgs"),
            gaussian_workflow
        ).when(
            sfn.Condition.string_equals("$.pipelineStep", "compression"),
            compression_workflow
        ).otherwise(
            sfm_workflow  # Default to full pipeline
        )

        # Create the Step Function
        ml_pipeline = sfn.StateMachine(
            self, "MLPipelineStateMachine",
            state_machine_name=f"SpaceportMLPipeline-{suffix}",
            definition=definition,
            role=step_functions_role,
            logs=sfn.LogOptions(
                destination=step_functions_log_group,
                level=sfn.LogLevel.ALL,
                include_execution_data=True
            ),
            timeout=Duration.hours(8)
        )

        # Update start job lambda with Step Function ARN
        start_job_lambda.add_environment("STEP_FUNCTION_ARN", ml_pipeline.state_machine_arn)

        # Create Lambda function for stopping jobs
        stop_job_lambda = lambda_.Function(
            self, "StopJobFunction",
            function_name=f"Spaceport-StopJobFunction-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="stop_job.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/stop_job"),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "STEP_FUNCTION_ARN": ml_pipeline.state_machine_arn,
            }
        )

        # ========== API GATEWAY ==========
        # Create API Gateway for ML pipeline
        ml_api = apigw.RestApi(
            self, "SpaceportMLApi",
            rest_api_name=f"Spaceport-ML-API-{suffix}",
            description="API for ML processing pipeline",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"]
            )
        )

        # Add /start-job endpoint
        start_job_resource = ml_api.root.add_resource("start-job")
        start_job_resource.add_method(
            "POST",
            apigw.LambdaIntegration(
                start_job_lambda,
                proxy=True
            )
        )

        # Add /stop-job endpoint
        stop_job_resource = ml_api.root.add_resource("stop-job")
        stop_job_resource.add_method(
            "POST",
            apigw.LambdaIntegration(
                stop_job_lambda,
                proxy=True
            )
        )

        # ========== CLOUDWATCH ALARMS ==========
        # Alarm for Step Function failures with environment-specific naming
        step_function_failure_alarm = cloudwatch.Alarm(
            self, "StepFunctionFailureAlarm",
            alarm_name=f"SpaceportMLPipeline-Failures-{suffix}",
            alarm_description=f"Alarm when ML pipeline fails for {suffix} environment",
            metric=ml_pipeline.metric_failed(),
            threshold=1,
            evaluation_periods=1,
            datapoints_to_alarm=1
        )

        # ========== PREFLIGHT DEPLOYMENT CHECKS ==========
        # Run comprehensive validation before deployment
        self._run_preflight_deployment_check()

        # ========== OUTPUTS ==========
        CfnOutput(
            self, "MLApiUrl",
            value=ml_api.url,
            description="ML Pipeline API Gateway URL"
        )

        CfnOutput(
            self, "MLBucketName", 
            value=ml_bucket.bucket_name,
            description="ML Processing S3 Bucket"
        )

        CfnOutput(
            self, "StepFunctionArn",
            value=ml_pipeline.state_machine_arn,
            description="ML Pipeline Step Function ARN"
        )

        CfnOutput(
            self, "SfMRepositoryUri",
            value=sfm_repo.repository_uri,
            description="SfM ECR Repository URI"
        )

        CfnOutput(
            self, "GaussianRepositoryUri", 
            value=gaussian_repo.repository_uri,
            description="3DGS ECR Repository URI"
        )

        CfnOutput(
            self, "CompressorRepositoryUri",
            value=compressor_repo.repository_uri,
            description="Compressor ECR Repository URI"
        )

    def _bucket_exists(self, bucket_name: str) -> bool:
        """Check if an S3 bucket exists"""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except Exception:
            return False

    def _ecr_repo_exists(self, repo_name: str) -> bool:
        """Check if an ECR repository exists"""
        try:
            self.ecr_client.describe_repositories(repositoryNames=[repo_name])
            return True
        except Exception:
            return False

    def _get_or_create_s3_bucket(self, construct_id: str, preferred_name: str, fallback_name: str) -> s3.IBucket:
        """Get existing S3 bucket or create new one with robustness validation"""
        
        # Robustness: Validate names before proceeding
        self._validate_s3_bucket_name(preferred_name, "preferred")
        self._validate_s3_bucket_name(fallback_name, "fallback")
        
        # Robustness: Check for potential conflicts
        self._check_s3_naming_conflicts(preferred_name, fallback_name)
        
        # First try preferred name (with environment suffix)
        if self._bucket_exists(preferred_name):
            print(f"✅ Importing existing S3 bucket: {preferred_name}")
            bucket = s3.Bucket.from_bucket_name(self, construct_id, preferred_name)
            self._imported_resources.append({"type": "S3::Bucket", "name": preferred_name, "action": "imported"})
            return bucket
        
        # Then try fallback name (without suffix)
        if self._bucket_exists(fallback_name):
            print(f"✅ Importing existing S3 bucket (fallback): {fallback_name}")
            # Robustness: Validate fallback is accessible
            if not self._validate_bucket_accessibility(fallback_name):
                print(f"⚠️  Warning: Fallback bucket {fallback_name} may have access issues")
            bucket = s3.Bucket.from_bucket_name(self, construct_id, fallback_name)
            self._imported_resources.append({"type": "S3::Bucket", "name": fallback_name, "action": "imported_fallback"})
            return bucket
        
        # Create new bucket with preferred name
        print(f"🆕 Creating new S3 bucket: {preferred_name}")
        bucket = s3.Bucket(
            self, construct_id,
            bucket_name=preferred_name,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )
        self._created_resources.append({"type": "S3::Bucket", "name": preferred_name, "action": "created"})
        return bucket

    def _get_or_create_ecr_repo(self, construct_id: str, preferred_name: str, fallback_name: str) -> ecr.IRepository:
        """Get existing ECR repository or create new one"""
        # First try preferred name (with environment suffix)
        if self._ecr_repo_exists(preferred_name):
            print(f"Importing existing ECR repository: {preferred_name}")
            return ecr.Repository.from_repository_name(self, construct_id, preferred_name)
        
        # Then try fallback name (without suffix)
        if self._ecr_repo_exists(fallback_name):
            print(f"Importing existing ECR repository: {fallback_name}")
            return ecr.Repository.from_repository_name(self, construct_id, fallback_name)
        
        # Create new repository with preferred name
        print(f"Creating new ECR repository: {preferred_name}")
        return ecr.Repository(
            self, construct_id,
            repository_name=preferred_name,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    max_image_count=10,
                    tag_status=ecr.TagStatus.ANY
                )
            ]
        )

    # ========== ROBUSTNESS VALIDATION METHODS ==========
    
    def _validate_environment_config(self):
        """Validate environment configuration is complete and correct"""
        required_keys = ['resourceSuffix', 'region', 'domain']
        for key in required_keys:
            if key not in self.env_config:
                raise ValueError(f"Missing required environment config key: {key}")
        
        # Validate suffix format
        suffix = self.env_config['resourceSuffix']
        if not suffix or not suffix.replace('-', '').replace('_', '').isalnum():
            raise ValueError(f"Invalid resource suffix: {suffix}")
        
        print(f"✅ Environment config validated for: {suffix}")
    
    def _validate_resource_naming_conventions(self):
        """Validate all resource names follow proper conventions"""
        suffix = self.env_config['resourceSuffix']
        
        # Define expected resource names
        expected_names = {
            'iam_roles': [
                f"Spaceport-SageMaker-Role-{suffix}",
                f"Spaceport-StepFunctions-Role-{suffix}",
                f"Spaceport-ML-Lambda-Role-{suffix}",
                f"Spaceport-Notification-Lambda-Role-{suffix}"
            ],
            'lambda_functions': [
                f"Spaceport-StartMLJob-{suffix}",
                f"Spaceport-MLNotification-{suffix}",
                f"Spaceport-StopJobFunction-{suffix}"
            ],
            'cloudwatch_alarms': [
                f"SpaceportMLPipeline-Failures-{suffix}"
            ]
        }
        
        # Validate naming patterns
        for resource_type, names in expected_names.items():
            for name in names:
                if not self._is_valid_resource_name(name, suffix):
                    raise ValueError(f"Invalid {resource_type} name: {name}")
        
        print(f"✅ Resource naming conventions validated for: {suffix}")
    
    def _is_valid_resource_name(self, name: str, suffix: str) -> bool:
        """Check if resource name follows conventions"""
        # Must contain the suffix
        if not name.endswith(f"-{suffix}"):
            return False
        
        # Must start with Spaceport
        if not name.startswith("Spaceport"):
            return False
        
        # No invalid characters
        if any(char in name for char in [' ', '_', '.']):
            return False
        
        return True
    
    def _validate_s3_bucket_name(self, bucket_name: str, name_type: str):
        """Validate S3 bucket name follows AWS requirements"""
        if not bucket_name:
            raise ValueError(f"Empty bucket name for {name_type}")
        
        # AWS S3 bucket naming rules
        if len(bucket_name) < 3 or len(bucket_name) > 63:
            raise ValueError(f"Bucket name {bucket_name} must be between 3 and 63 characters")
        
        if not bucket_name.replace('-', '').replace('.', '').isalnum():
            raise ValueError(f"Bucket name {bucket_name} contains invalid characters")
        
        if bucket_name.startswith('-') or bucket_name.endswith('-'):
            raise ValueError(f"Bucket name {bucket_name} cannot start or end with hyphen")
    
    def _check_s3_naming_conflicts(self, preferred_name: str, fallback_name: str):
        """Check for potential S3 bucket naming conflicts"""
        # Check if names are too similar
        if preferred_name == fallback_name:
            print(f"⚠️  Warning: Preferred and fallback bucket names are identical: {preferred_name}")
        
        # Check for reserved names
        reserved_patterns = ['aws-', 'amazon-', 'cloudfront-']
        for pattern in reserved_patterns:
            if preferred_name.startswith(pattern) or fallback_name.startswith(pattern):
                print(f"⚠️  Warning: Bucket name uses reserved pattern: {pattern}")
    
    def _validate_bucket_accessibility(self, bucket_name: str) -> bool:
        """Validate that bucket is accessible for import"""
        try:
            # Check if we can read bucket metadata
            self.s3_client.head_bucket(Bucket=bucket_name)
            
            # Check if we can list objects (basic permission test)
            self.s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            
            return True
        except Exception as e:
            print(f"⚠️  Bucket accessibility issue for {bucket_name}: {str(e)}")
            return False
    
    def _run_preflight_deployment_check(self):
        """Run comprehensive preflight checks before deployment"""
        print("🚀 Running preflight deployment checks...")
        
        # Check 1: Validate resource mix makes sense
        self._validate_resource_mix()
        
        # Check 2: Check for naming conflicts with existing resources
        self._check_existing_resource_conflicts()
        
        # Check 3: Validate all imported resources are accessible
        self._validate_imported_resources()
        
        # Check 4: Validate environment-specific requirements
        self._validate_environment_requirements()
        
        print("✅ All preflight checks passed - deployment ready!")
    
    def _validate_resource_mix(self):
        """Validate the mix of imported vs created resources makes sense"""
        imported_count = len(self._imported_resources)
        created_count = len(self._created_resources)
        
        print(f"📊 Resource mix: {imported_count} imported, {created_count} created")
        
        # Environment-specific validations
        suffix = self.env_config['resourceSuffix']
        
        if suffix == 'staging':
            if imported_count == 0:
                print("⚠️  Warning: No imported resources in staging - all resources will be new")
            if created_count > imported_count * 2:
                print("⚠️  Warning: Creating many new resources in staging environment")
        
        elif suffix == 'prod':
            if created_count > imported_count:
                print("⚠️  Warning: Creating more resources than importing in production")
    
    def _check_existing_resource_conflicts(self):
        """Check for conflicts with existing AWS resources"""
        print("🔍 Checking for existing resource conflicts...")
        
        # Check each resource we plan to create
        for resource in self._created_resources:
            resource_name = resource['name']
            resource_type = resource['type']
            
            if self._has_aws_resource_conflict(resource_type, resource_name):
                raise ValueError(f"Resource conflict detected: {resource_type} {resource_name} already exists")
    
    def _has_aws_resource_conflict(self, resource_type: str, resource_name: str) -> bool:
        """Check if resource name conflicts with existing AWS resources"""
        try:
            if resource_type == "S3::Bucket":
                self.s3_client.head_bucket(Bucket=resource_name)
                return True
            elif resource_type == "ECR::Repository":
                self.ecr_client.describe_repositories(repositoryNames=[resource_name])
                return True
            elif resource_type == "CloudWatch::Alarm":
                response = self.cloudwatch_client.describe_alarms(AlarmNames=[resource_name])
                return len(response['MetricAlarms']) > 0
            elif resource_type == "IAM::Role":
                self.iam_client.get_role(RoleName=resource_name)
                return True
        except Exception:
            return False
        
        return False
    
    def _validate_imported_resources(self):
        """Validate all imported resources are properly accessible"""
        print("🔍 Validating imported resources...")
        
        for resource in self._imported_resources:
            resource_name = resource['name']
            resource_type = resource['type']
            
            if not self._is_resource_accessible_for_import(resource_type, resource_name):
                print(f"⚠️  Warning: Imported resource may not be accessible: {resource_type} {resource_name}")
    
    def _is_resource_accessible_for_import(self, resource_type: str, resource_name: str) -> bool:
        """Check if resource is accessible for CloudFormation import"""
        try:
            if resource_type == "S3::Bucket":
                return self._validate_bucket_accessibility(resource_name)
            elif resource_type == "ECR::Repository":
                self.ecr_client.describe_repositories(repositoryNames=[resource_name])
                return True
            # Add more resource type validations as needed
            return True
        except Exception:
            return False
    
    def _validate_environment_requirements(self):
        """Validate environment-specific requirements are met"""
        suffix = self.env_config['resourceSuffix']
        
        if suffix == 'staging':
            # Staging should have fallback resources available
            if not any(r['action'] == 'imported_fallback' for r in self._imported_resources):
                print("ℹ️  Info: No fallback resources used in staging environment")
        
        elif suffix == 'prod':
            # Production should prefer environment-specific resources
            fallback_count = len([r for r in self._imported_resources if r['action'] == 'imported_fallback'])
            if fallback_count > 0:
                print(f"⚠️  Warning: Production using {fallback_count} fallback resources")
        
        print(f"✅ Environment requirements validated for: {suffix}") 