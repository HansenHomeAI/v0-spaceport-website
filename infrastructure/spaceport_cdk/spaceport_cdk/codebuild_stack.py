from aws_cdk import (
    Stack,
    aws_codebuild as codebuild,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_s3 as s3,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct

class CodeBuildStack(Stack):
    """
    CodeBuild stack for building SOGS compression container on AWS infrastructure
    This enables building CUDA containers without requiring local CUDA support
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECR Repository for SOGS compression container
        sogs_ecr_repo = ecr.Repository(
            self, "SOGSCompressionRepository",
            repository_name="spaceport-ml-sogs-compressor",
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    max_image_count=10,
                    rule_priority=1,
                    description="Keep only 10 most recent images"
                )
            ]
        )

        # S3 bucket for build artifacts (if needed)
        build_artifacts_bucket = s3.Bucket(
            self, "SOGSBuildArtifacts",
            bucket_name=f"spaceport-sogs-build-artifacts-{self.account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # IAM role for CodeBuild
        codebuild_role = iam.Role(
            self, "SOGSCodeBuildRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            inline_policies={
                "SOGSBuildPolicy": iam.PolicyDocument(
                    statements=[
                        # ECR permissions
                        iam.PolicyStatement(
                            actions=[
                                "ecr:BatchCheckLayerAvailability",
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchGetImage",
                                "ecr:GetAuthorizationToken",
                                "ecr:PutImage",
                                "ecr:InitiateLayerUpload",
                                "ecr:UploadLayerPart",
                                "ecr:CompleteLayerUpload"
                            ],
                            resources=[
                                sogs_ecr_repo.repository_arn,
                                f"arn:aws:ecr:{self.region}:{self.account}:repository/*"
                            ]
                        ),
                        # ECR auth token
                        iam.PolicyStatement(
                            actions=["ecr:GetAuthorizationToken"],
                            resources=["*"]
                        ),
                        # CloudWatch Logs
                        iam.PolicyStatement(
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/codebuild/*"
                            ]
                        ),
                        # S3 for artifacts
                        iam.PolicyStatement(
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:GetBucketAcl",
                                "s3:GetBucketLocation"
                            ],
                            resources=[
                                build_artifacts_bucket.bucket_arn,
                                f"{build_artifacts_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                )
            }
        )

        # CodeBuild project for SOGS compression container
        sogs_build_project = codebuild.Project(
            self, "SOGSCompressionBuild",
            project_name="spaceport-sogs-compression-build",
            description="Build SOGS compression container with CUDA support on AWS infrastructure",
            
            # Use a build environment with GPU support for CUDA builds
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,  # Latest with Docker support
                compute_type=codebuild.ComputeType.LARGE,  # More resources for container builds
                privileged=True  # Required for Docker builds
            ),
            
            # Source from GitHub (you'll need to connect your repo)
            source=codebuild.Source.git_hub(
                owner="yourusername",  # Replace with your GitHub username
                repo="Spaceport-Website",  # Your repo name
                webhook=True,  # Enable webhooks for automatic builds
                webhook_filters=[
                    codebuild.FilterGroup.in_event_of(
                        codebuild.EventAction.PUSH
                    ).and_branch_is("main")  # Build on pushes to main
                ]
            ),
            
            # Build specification
            build_spec=codebuild.BuildSpec.from_source_filename("infrastructure/containers/compressor/buildspec.yml"),
            
            # Environment variables
            environment_variables={
                "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(value=self.region),
                "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=self.account),
                "IMAGE_REPO_NAME": codebuild.BuildEnvironmentVariable(value="spaceport-ml-sogs-compressor"),
                "IMAGE_TAG": codebuild.BuildEnvironmentVariable(value="latest")
            },
            
            # Artifacts
            artifacts=codebuild.Artifacts.s3(
                bucket=build_artifacts_bucket,
                name="sogs-build-artifacts",
                include_build_id=True
            ),
            
            # Role
            role=codebuild_role,
            
            # Timeout
            timeout_in_minutes=60  # 1 hour for container builds
        )

        # Manual build project (for testing without webhooks)
        manual_build_project = codebuild.Project(
            self, "SOGSManualBuild",
            project_name="spaceport-sogs-manual-build",
            description="Manual build for SOGS compression container",
            
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.LARGE,
                privileged=True
            ),
            
            # Source from local files (for manual builds)
            source=codebuild.Source.code_commit(
                repository=None  # Will be configured manually
            ),
            
            build_spec=codebuild.BuildSpec.from_source_filename("infrastructure/containers/compressor/buildspec.yml"),
            
            environment_variables={
                "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(value=self.region),
                "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=self.account),
                "IMAGE_REPO_NAME": codebuild.BuildEnvironmentVariable(value="spaceport-ml-sogs-compressor"),
                "IMAGE_TAG": codebuild.BuildEnvironmentVariable(value="latest")
            },
            
            artifacts=codebuild.Artifacts.s3(
                bucket=build_artifacts_bucket,
                name="sogs-manual-build-artifacts",
                include_build_id=True
            ),
            
            role=codebuild_role,
            timeout_in_minutes=60
        )

        # Outputs
        CfnOutput(
            self, "SOGSECRRepository",
            value=sogs_ecr_repo.repository_uri,
            description="ECR Repository URI for SOGS compression container"
        )

        CfnOutput(
            self, "SOGSBuildProject",
            value=sogs_build_project.project_name,
            description="CodeBuild project name for SOGS container"
        )

        CfnOutput(
            self, "SOGSManualBuildProject",
            value=manual_build_project.project_name,
            description="Manual CodeBuild project for SOGS container"
        )

        CfnOutput(
            self, "BuildArtifactsBucket",
            value=build_artifacts_bucket.bucket_name,
            description="S3 bucket for build artifacts"
        )

        # Store references for other stacks
        self.sogs_ecr_repo = sogs_ecr_repo
        self.build_project = sogs_build_project
        self.manual_build_project = manual_build_project 