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


class MLPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ========== S3 BUCKETS ==========
        # Import existing S3 buckets to avoid conflicts
        ml_bucket = s3.Bucket.from_bucket_name(
            self, "SpaceportMLBucket",
            "spaceport-ml-processing"
        )

        # Import existing upload bucket
        upload_bucket = s3.Bucket.from_bucket_name(
            self, "ImportedUploadBucket",
            "spaceport-uploads"
        )

        # ========== ECR REPOSITORIES ==========
        # ECR repositories for ML containers
        sfm_repo = ecr.Repository(
            self, "SfMRepository",
            repository_name="spaceport/sfm",
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    max_image_count=10,
                    rule_priority=1,
                    description="Keep only 10 most recent images"
                )
            ]
        )

        gaussian_repo = ecr.Repository(
            self, "GaussianRepository", 
            repository_name="spaceport/3dgs",
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    max_image_count=10,
                    rule_priority=1,
                    description="Keep only 10 most recent images"
                )
            ]
        )

        compressor_repo = ecr.Repository(
            self, "CompressorRepository",
            repository_name="spaceport/compressor", 
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    max_image_count=10,
                    rule_priority=1,
                    description="Keep only 10 most recent images"
                )
            ]
        )

        # ========== IAM ROLES ==========
        # SageMaker execution role
        sagemaker_role = iam.Role(
            self, "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess")
            ]
        )

        # Step Functions execution role
        step_functions_role = iam.Role(
            self, "StepFunctionsExecutionRole",
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

        # Lambda execution role for API
        lambda_role = iam.Role(
            self, "MLLambdaExecutionRole",
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

        # Notification Lambda role
        notification_lambda_role = iam.Role(
            self, "NotificationLambdaRole",
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
        # Log groups for each component
        sfm_log_group = logs.LogGroup(
            self, "SfMLogGroup",
            log_group_name="/aws/sagemaker/processing-jobs/sfm",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        gaussian_log_group = logs.LogGroup(
            self, "GaussianLogGroup", 
            log_group_name="/aws/sagemaker/training-jobs/3dgs",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        compressor_log_group = logs.LogGroup(
            self, "CompressorLogGroup",
            log_group_name="/aws/sagemaker/processing-jobs/compressor", 
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        step_functions_log_group = logs.LogGroup(
            self, "StepFunctionsLogGroup",
            log_group_name="/aws/stepfunctions/ml-pipeline",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        # ========== LAMBDA FUNCTIONS ==========
        # Get the lambda directory path
        lambda_dir = os.path.join(os.path.dirname(__file__), "..", "lambda")

        # API Lambda for starting ML jobs
        start_job_lambda = lambda_.Function(
            self, "StartMLJobFunction",
            function_name="Spaceport-StartMLJob",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset(os.path.join(lambda_dir, "start_ml_job")),
            handler="lambda_function.lambda_handler",
            environment={
                "STATE_MACHINE_ARN": "",  # Will be set after Step Function creation
                "UPLOAD_BUCKET": upload_bucket.bucket_name,
                "ML_BUCKET": ml_bucket.bucket_name
            },
            role=lambda_role,
            timeout=Duration.seconds(30)
        )

        # Notification Lambda
        notification_lambda = lambda_.Function(
            self, "NotificationFunction",
            function_name="Spaceport-MLNotification",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset(os.path.join(lambda_dir, "ml_notification")),
            handler="lambda_function.lambda_handler",
            environment={
                "ML_BUCKET": ml_bucket.bucket_name
            },
            role=notification_lambda_role,
            timeout=Duration.seconds(30)
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
            state_machine_name="SpaceportMLPipeline",
            definition=definition,
            role=step_functions_role,
            logs=sfn.LogOptions(
                destination=step_functions_log_group,
                level=sfn.LogLevel.ALL,
                include_execution_data=True
            ),
            timeout=Duration.hours(8)
        )

        # Update Lambda environment with Step Function ARN
        start_job_lambda.add_environment("STATE_MACHINE_ARN", ml_pipeline.state_machine_arn)

        # Create Lambda function for stopping jobs
        stop_job_lambda = lambda_.Function(
            self, "StopJobFunction",
            function_name="Spaceport-StopJobFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset("../lambda/stop_job"),
            handler="stop_job.lambda_handler",
            role=lambda_role,
            timeout=Duration.seconds(30)
        )

        # ========== API GATEWAY ==========
        # Create API Gateway for ML pipeline
        ml_api = apigw.RestApi(
            self, "SpaceportMLApi",
            rest_api_name="Spaceport-ML-API",
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
        # Alarm for Step Function failures
        step_function_failure_alarm = cloudwatch.Alarm(
            self, "StepFunctionFailureAlarm",
            alarm_name="SpaceportMLPipeline-Failures",
            alarm_description="Alarm when ML pipeline fails",
            metric=ml_pipeline.metric_failed(),
            threshold=1,
            evaluation_periods=1,
            datapoints_to_alarm=1
        )

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