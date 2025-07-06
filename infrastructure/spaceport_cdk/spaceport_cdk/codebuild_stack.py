from aws_cdk import (
    Stack,
    aws_codebuild as codebuild,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_s3 as s3,
    RemovalPolicy,
    CfnOutput,
    Duration,
)
from constructs import Construct

class CodeBuildStack(Stack):
    """
    CodeBuild stack for building container images with optimized caching
    Includes Docker layer caching, S3 artifact caching, and local caching
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
                    max_image_count=20,  # Increased for better caching
                    rule_priority=1,
                    description="Keep 20 most recent images for caching"
                )
            ]
        )

        # Enhanced S3 bucket for build artifacts and caching
        build_artifacts_bucket = s3.Bucket(
            self, "SOGSBuildArtifacts",
            bucket_name=f"spaceport-sogs-build-artifacts-{self.account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="CacheOptimization",
                    enabled=True,
                    # Keep recent artifacts for caching
                    expiration=Duration.days(30),
                    # Clean up old versions
                    noncurrent_version_expiration=Duration.days(7),
                    # Move to cheaper storage for long-term artifacts
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(7)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(30)
                        )
                    ]
                )
            ]
        )

        # Enhanced IAM role for CodeBuild with caching permissions
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
                                "ecr:CompleteLayerUpload",
                                "ecr:DescribeImages",
                                "ecr:ListImages"
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
                        # Enhanced S3 permissions for caching
                        iam.PolicyStatement(
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:GetBucketAcl",
                                "s3:GetBucketLocation",
                                "s3:ListBucket",
                                "s3:GetObjectVersion",
                                "s3:DeleteObject"
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

        # Optimized CodeBuild project for SOGS compression container
        sogs_build_project = codebuild.Project(
            self, "SOGSCompressionBuild",
            project_name="spaceport-sogs-compression-build",
            description="Build SOGS compression container with advanced caching and optimization",
            
            # Enhanced build environment
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.X2_LARGE,  # More resources for faster builds
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
                "IMAGE_TAG": codebuild.BuildEnvironmentVariable(value="latest"),
                "DOCKER_BUILDKIT": codebuild.BuildEnvironmentVariable(value="1"),
                "BUILDKIT_PROGRESS": codebuild.BuildEnvironmentVariable(value="plain")
            },
            
            # Enhanced artifacts with caching
            artifacts=codebuild.Artifacts.s3(
                bucket=build_artifacts_bucket,
                name="sogs-build-artifacts",
                include_build_id=True,
                path="artifacts"
            ),
            
            # Enable local and S3 caching
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.DOCKER_LAYER,
                codebuild.LocalCacheMode.SOURCE,
                codebuild.LocalCacheMode.CUSTOM
            ),
            
            # Additional S3 cache
            secondary_artifacts=[
                codebuild.Artifacts.s3(
                    bucket=build_artifacts_bucket,
                    name="build-cache",
                    include_build_id=False,
                    path="cache",
                    identifier="BuildCache"
                )
            ],
            
            # Role
            role=codebuild_role,
            
            # Extended timeout for complex builds
            timeout=Duration.minutes(90)
        )

        # Enhanced manual CodeBuild project with caching
        manual_build_project = codebuild.Project(
            self, "ManualContainerBuildProject",
            project_name="spaceport-manual-container-builds",
            description="Manually triggered CodeBuild project with optimized caching",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.X2_LARGE,  # More resources
                privileged=True
            ),
            source=codebuild.Source.git_hub(
                owner="your-github-owner", # CHANGE THIS
                repo="your-github-repo",   # CHANGE THIS
                branch_or_ref="main"
            ),
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml"),
            
            # Enhanced environment variables
            environment_variables={
                "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(value=self.region),
                "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=self.account),
                "DOCKER_BUILDKIT": codebuild.BuildEnvironmentVariable(value="1"),
                "BUILDKIT_PROGRESS": codebuild.BuildEnvironmentVariable(value="plain"),
                "CONTAINERS_TO_BUILD": codebuild.BuildEnvironmentVariable(value="all")
            },
            
            # Enable comprehensive caching
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.DOCKER_LAYER,
                codebuild.LocalCacheMode.SOURCE,
                codebuild.LocalCacheMode.CUSTOM
            ),
            
            # Enhanced artifacts
            artifacts=codebuild.Artifacts.s3(
                bucket=build_artifacts_bucket,
                name="manual-build-artifacts",
                include_build_id=True
            ),
            
            role=codebuild_role,
            timeout=Duration.minutes(120)  # Extended timeout
        )

        # Outputs
        CfnOutput(
            self, "SOGSECRRepository",
            value=sogs_ecr_repo.repository_uri,
            description="ECR Repository URI for SOGS compression container"
        )

        CfnOutput(
            self, "CodeBuildProjectName",
            value=sogs_build_project.project_name,
            description="CodeBuild project name for SOGS container"
        )

        CfnOutput(
            self, "ManualCodeBuildProjectName",
            value=manual_build_project.project_name,
            description="Manual CodeBuild project for all containers"
        )

        CfnOutput(
            self, "BuildArtifactsBucket",
            value=build_artifacts_bucket.bucket_name,
            description="S3 bucket for build artifacts and caching"
        )

        CfnOutput(
            self, "OptimizationFeatures",
            value="Docker Layer Caching, S3 Artifact Caching, Local Caching, Enhanced Compute",
            description="Optimization features enabled in this CodeBuild stack"
        )

        # Store references for other stacks
        self.sogs_ecr_repo = sogs_ecr_repo
        self.build_project = sogs_build_project
        self.manual_build_project = manual_build_project 