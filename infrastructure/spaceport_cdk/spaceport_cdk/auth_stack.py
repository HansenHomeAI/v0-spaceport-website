from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    BundlingOptions,  # For installing Python dependencies
    DockerVolume,
    CfnOutput,
    aws_cognito as cognito,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_logs as logs,
    aws_kms as kms,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
)
from constructs import Construct
import os
import boto3


class AuthStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, env_config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Environment configuration
        self.env_config = env_config
        suffix = env_config['resourceSuffix']
        region = env_config['region']
        
        # Initialize AWS clients for resource checking
        self.dynamodb_client = boto3.client('dynamodb', region_name=region)
        self.cognito_client = boto3.client('cognito-idp', region_name=region)

        # ROBUST USER POOL LOGIC - Import existing or create new only when needed
        # Follows same pattern as DynamoDB: preferred → fallback → create new
        user_pool = self._get_or_create_user_pool(
            construct_id="SpaceportUserPool",
            preferred_name=f"Spaceport-Users-{suffix}",
            fallback_name="Spaceport-Users-v2",
            pool_type="standard"
        )
        
        # Get existing client for this pool
        user_pool_client = self._get_or_create_client(
            user_pool, 
            "SpaceportUserPoolClient",
            "Spaceport-Web-Client"
        )

        CfnOutput(self, "CognitoUserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "CognitoUserPoolClientId", value=user_pool_client.user_pool_client_id)

        # ========== INVITE USER LAMBDA ==========
        # Create IAM role for invite Lambda
        invite_lambda_role = iam.Role(
            self, "InviteUserLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "InviteUserPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "cognito-idp:AdminCreateUser",
                                "cognito-idp:AdminUpdateUserAttributes",
                                "cognito-idp:AdminSetUserPassword",
                                "cognito-idp:AdminAddUserToGroup",
                                "cognito-idp:AdminGetUser",
                            ],
                            resources=[user_pool.user_pool_arn]
                        )
                    ]
                )
            }
        )

        # Create invite Lambda function with environment-specific naming
        invite_lambda = lambda_.Function(
            self,
            "Spaceport-InviteUserFunction",
            function_name=f"Spaceport-InviteUserFunctionV2",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                os.path.join(os.path.dirname(__file__), "..", "lambda", "invite_user"),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && "
                        "cp -au . /asset-output"
                    ],
                ),
            ),
            role=invite_lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "COGNITO_USER_POOL_ID": user_pool.user_pool_id,
                "INVITE_GROUP": "beta-testers-v2",
                "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", ""),
                "INVITE_API_KEY": os.environ.get("INVITE_API_KEY", ""),
            },
        )

        # Create invite API Gateway
        invite_api = apigw.RestApi(
            self,
            "Spaceport-InviteApiV2",
            rest_api_name="Spaceport-InviteApiV2",
            description="Invite approved users to Spaceport (V2)",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
        )

        invite_res = invite_api.root.add_resource("invite")
        invite_res.add_method("POST", apigw.LambdaIntegration(invite_lambda, proxy=True))

        CfnOutput(self, "InviteApiUrlV2", value=f"{invite_api.url}invite")



        # -------------------------------------
        # Per-user Projects storage and REST API
        # -------------------------------------
        # Dynamic projects table - import if exists, create if not
        projects_table = self._get_or_create_dynamodb_table(
            construct_id="Spaceport-ProjectsTable",
            preferred_name=f"Spaceport-Projects-{suffix}",
            fallback_name="Spaceport-Projects",
            partition_key_name="id",
            partition_key_type=dynamodb.AttributeType.STRING
        )

        # Define Projects Lambda function with environment-specific naming
        projects_lambda = lambda_.Function(
            self,
            "Spaceport-ProjectsFunction",
            function_name=f"Spaceport-ProjectsFunction-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                os.path.join(os.path.dirname(__file__), "..", "lambda", "projects")
            ),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "PROJECTS_TABLE_NAME": projects_table.table_name,
            },
        )
        # Allow the Lambda to read/write from the Projects table
        projects_table.grant_read_write_data(projects_lambda)

        # Enable API Gateway access logs and INFO logging level
        access_log_group = logs.LogGroup(
            self,
            "ProjectsApiAccessLogs",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.RETAIN,
        )

        projects_api = apigw.RestApi(
            self,
            "Spaceport-ProjectsApi",
            rest_api_name=f"Spaceport-ProjectsApi-{suffix}",
            description="CRUD for user projects (requires Cognito JWT)",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "authorization",
                    "X-Amz-Date",
                    "X-Amz-Security-Token",
                    "X-Api-Key",
                ],
            ),
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
                access_log_destination=apigw.LogGroupLogDestination(access_log_group),
                access_log_format=apigw.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=True,
                ),
            ),
        )
        # Create Cognito authorizer for projects API
        projects_authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "ProjectsAuthorizer",
            cognito_user_pools=[user_pool],
        )
        
        proj_res = projects_api.root.add_resource("projects")
        proj_res.add_method(
            "GET", 
            apigw.LambdaIntegration(projects_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=projects_authorizer
        )
        proj_res.add_method(
            "POST", 
            apigw.LambdaIntegration(projects_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=projects_authorizer
        )
        proj_id = proj_res.add_resource("{id}")
        proj_id.add_method(
            "GET", 
            apigw.LambdaIntegration(projects_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=projects_authorizer
        )
        proj_id.add_method(
            "PUT", 
            apigw.LambdaIntegration(projects_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=projects_authorizer
        )
        proj_id.add_method(
            "PATCH", 
            apigw.LambdaIntegration(projects_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=projects_authorizer
        )
        proj_id.add_method(
            "DELETE", 
            apigw.LambdaIntegration(projects_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=projects_authorizer
        )

        # Add Gateway Responses to handle CORS for error responses
        projects_api.add_gateway_response(
            "DEFAULT_4XX",
            type=apigw.ResponseType.DEFAULT_4_XX,
            response_headers={
                "Access-Control-Allow-Origin": "'*'",
                "Access-Control-Allow-Headers": "'Content-Type,Authorization,authorization,X-Amz-Date,X-Amz-Security-Token,X-Api-Key'",
                "Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,PATCH,OPTIONS'"
            }
        )
        
        projects_api.add_gateway_response(
            "DEFAULT_5XX",
            type=apigw.ResponseType.DEFAULT_5_XX,
            response_headers={
                "Access-Control-Allow-Origin": "'*'",
                "Access-Control-Allow-Headers": "'Content-Type,Authorization,authorization,X-Amz-Date,X-Amz-Security-Token,X-Api-Key'",
                "Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,PATCH,OPTIONS'"
            }
        )

        CfnOutput(self, "ProjectsApiUrl", value=f"{projects_api.url}projects")

        # -------------------------------------
        # Subscription Management (integrated into AuthStack)
        # -------------------------------------
        
        # Dynamic users table - import if exists, create if not  
        # Updated schema: userSub (Cognito sub) as partition key + subscription fields
        users_table = self._get_or_create_dynamodb_table(
            construct_id="Spaceport-UsersTable",
            preferred_name=f"Spaceport-Users-{suffix}",
            fallback_name="Spaceport-Users",
            partition_key_name="userSub",
            partition_key_type=dynamodb.AttributeType.STRING
        )
        
        # Create subscription manager Lambda function
        subscription_lambda = lambda_.Function(
            self,
            "SubscriptionManagerLambda",  # Unique construct ID
            function_name=f"Spaceport-SubscriptionManager-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                "../lambda/subscription_manager",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                ),
            ),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "USERS_TABLE": users_table.table_name,
                "COGNITO_USER_POOL_ID": user_pool.user_pool_id,
                "STRIPE_SECRET_KEY": os.environ.get(f"STRIPE_SECRET_KEY_{'TEST' if suffix == 'staging' else suffix.upper()}", ""),
                "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", ""),
                "STRIPE_WEBHOOK_SECRET": os.environ.get(f"STRIPE_WEBHOOK_SECRET_{suffix.upper()}", ""),
                "STRIPE_PRICE_SINGLE": os.environ.get(f"STRIPE_PRICE_SINGLE_{suffix.upper()}", ""),
                "STRIPE_PRICE_STARTER": os.environ.get(f"STRIPE_PRICE_STARTER_{suffix.upper()}", ""),
                "STRIPE_PRICE_GROWTH": os.environ.get(f"STRIPE_PRICE_GROWTH_{suffix.upper()}", ""),
                "REFERRAL_KICKBACK_PERCENTAGE": os.environ.get("REFERRAL_KICKBACK_PERCENTAGE", "10"),
                "EMPLOYEE_KICKBACK_PERCENTAGE": os.environ.get("EMPLOYEE_KICKBACK_PERCENTAGE", "30"),
                "COMPANY_KICKBACK_PERCENTAGE": os.environ.get("COMPANY_KICKBACK_PERCENTAGE", "70"),
                "REFERRAL_DURATION_MONTHS": os.environ.get("REFERRAL_DURATION_MONTHS", "6"),
                "EMPLOYEE_USER_ID": os.environ.get("EMPLOYEE_USER_ID", ""),
                "FRONTEND_URL": os.environ.get("FRONTEND_URL", "https://spcprt.com"),
            },
            log_retention=logs.RetentionDays.ONE_MONTH,
        )
        users_table.grant_read_write_data(subscription_lambda)

        # Add Cognito permissions for updating user attributes
        subscription_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:AdminUpdateUserAttributes",
                    "cognito-idp:AdminGetUser",
                ],
                resources=[user_pool.user_pool_arn]
            )
        )

        # Note: SES permissions removed - now using Resend for all email functionality

        # Create subscription API Gateway
        subscription_api = apigw.RestApi(
            self,
            "SubscriptionApiGateway",  # Unique construct ID
            rest_api_name="Spaceport-SubscriptionApi",
            description="Subscription management API for Spaceport",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Amz-Security-Token",
                    "X-Api-Key",
                ],
            ),
        )

        # Add subscription endpoints
        subscription_resource = subscription_api.root.add_resource("subscription")

        # Create checkout session endpoint (requires auth)
        create_checkout_resource = subscription_resource.add_resource("create-checkout-session")
        create_checkout_method = create_checkout_resource.add_method(
            "POST",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self,
                "SubscriptionCreateAuthorizer",
                cognito_user_pools=[user_pool],
            ),
        )

        # Webhook endpoint (no auth required for Stripe)
        webhook_resource = subscription_resource.add_resource("webhook")
        webhook_method = webhook_resource.add_method(
            "POST",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # Subscription status endpoint (requires auth)
        status_resource = subscription_resource.add_resource("subscription-status")
        status_method = status_resource.add_method(
            "GET",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self,
                "SubscriptionStatusAuthorizer",
                cognito_user_pools=[user_pool],
            ),
        )

        # Cancel subscription endpoint (requires auth)
        cancel_resource = subscription_resource.add_resource("cancel-subscription")
        cancel_method = cancel_resource.add_method(
            "POST",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self,
                "SubscriptionCancelAuthorizer",
                cognito_user_pools=[user_pool],
            ),
        )

        # Explicit deployment to ensure prod stage picks up authorizer changes without
        # requiring manual API Gateway redeploys. CfnDeployment updates the existing
        # "prod" stage in-place, so it works with the legacy stage the stack already created.
        subscription_deployment = apigw.CfnDeployment(
            self,
            f"SubscriptionApiDeployment{suffix}",
            rest_api_id=subscription_api.rest_api_id,
            description=f"subscription-{suffix}-deployment",
            stage_name="prod"
        )
        subscription_deployment.node.add_dependency(subscription_lambda)
        for method in (create_checkout_method, webhook_method, status_method, cancel_method):
            default_child = method.node.default_child
            if default_child is not None:
                subscription_deployment.node.add_dependency(default_child)

        # Outputs
        subscription_api_url = (
            f"https://{subscription_api.rest_api_id}.execute-api.{self.region}.amazonaws.com/prod/"
        )
        CfnOutput(self, "SubscriptionApiUrl", value=subscription_api_url)
        CfnOutput(self, "SubscriptionLambdaArn", value=subscription_lambda.function_arn)

        # Debug: Ensure subscription resources are included in stack
        CfnOutput(self, "SubscriptionStackDebug", value="Subscription resources included in AuthStack")
        
        # Force resource inclusion by referencing them
        self.subscription_lambda = subscription_lambda
        self.subscription_api = subscription_api

        # ========== BETA ACCESS ADMIN SYSTEM ==========
        # Create DynamoDB table for beta access permissions
        beta_access_permissions_table = self._get_or_create_dynamodb_table(
            construct_id="Spaceport-BetaAccessPermissionsTable",
            preferred_name=f"Spaceport-BetaAccessPermissions-{suffix}",
            fallback_name="Spaceport-BetaAccessPermissions",
            partition_key_name="user_id",
            partition_key_type=dynamodb.AttributeType.STRING
        )

        # Create IAM role for beta access admin Lambda
        beta_access_lambda_role = iam.Role(
            self, "BetaAccessAdminLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "BetaAccessAdminPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "cognito-idp:AdminCreateUser",
                                "cognito-idp:AdminAddUserToGroup",
                                "cognito-idp:AdminGetUser",
                                "cognito-idp:ListUsers",
                                "cognito-idp:ListGroups",
                                "cognito-idp:AdminUpdateUserAttributes",
                                "cognito-idp:AdminSetUserPassword"
                            ],
                            resources=[user_pool.user_pool_arn]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:DeleteItem",
                                "dynamodb:Query",
                                "dynamodb:Scan"
                            ],
                            resources=[beta_access_permissions_table.table_arn]
                        ),
                        # Note: SES permissions removed - now using Resend for all email functionality
                    ]
                )
            }
        )

        # Create beta access admin Lambda function
        shared_lambda_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lambda", "shared"))

        beta_access_lambda = lambda_.Function(
            self, "Spaceport-BetaAccessAdminFunction",
            function_name=f"Spaceport-BetaAccessAdminFunction-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                os.path.join(os.path.dirname(__file__), "..", "lambda", "beta_access_admin"),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
                    volumes=[
                        DockerVolume(
                            host_path=shared_lambda_dir,
                            container_path="/shared-src",
                        ),
                    ],
                    command=[
                        "bash", "-c",
                        "set -euo pipefail; pip install -r requirements.txt -t /asset-output; cp -au . /asset-output; mkdir -p /asset-output/shared; cp -au /shared-src/. /asset-output/shared/"
                    ],
                ),
            ),
            role=beta_access_lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "COGNITO_USER_POOL_ID": user_pool.user_pool_id,
                "PERMISSIONS_TABLE_NAME": beta_access_permissions_table.table_name,
                "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", ""),
            },
        )

        # Create API Gateway for beta access admin
        beta_access_api = apigw.RestApi(
            self, "Spaceport-BetaAccessAdminApi",
            rest_api_name=f"Spaceport-BetaAccessAdminApi-{suffix}",
            description="Beta access admin API for employee invitation management",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "authorization",
                    "X-Amz-Date",
                    "X-Amz-Security-Token",
                ],
            ),
        )

        # Add beta access admin endpoints
        admin_resource = beta_access_api.root.add_resource("admin")
        beta_access_resource = admin_resource.add_resource("beta-access")
        
        # Check permission endpoint
        check_permission_resource = beta_access_resource.add_resource("check-permission")
        check_permission_resource.add_method(
            "GET",
            apigw.LambdaIntegration(beta_access_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self,
                "BetaAccessCheckPermissionAuthorizer",
                cognito_user_pools=[user_pool],
            ),
        )

        for response_type, label in (
            (apigw.ResponseType.DEFAULT_4_XX, "Default4XX"),
            (apigw.ResponseType.DEFAULT_5_XX, "Default5XX"),
        ):
            beta_access_api.add_gateway_response(
                f"BetaAccess{label}",
                type=response_type,
                response_headers={
                    "Access-Control-Allow-Origin": "'*'",
                    "Access-Control-Allow-Headers": "'Content-Type,Authorization,authorization,X-Amz-Date,X-Amz-Security-Token,X-Api-Key'",
                    "Access-Control-Allow-Methods": "'GET,POST,OPTIONS'",
                },
            )

        # Send invitation endpoint
        send_invitation_resource = beta_access_resource.add_resource("send-invitation")
        send_invitation_resource.add_method(
            "POST",
            apigw.LambdaIntegration(beta_access_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self,
                "BetaAccessSendInvitationAuthorizer",
                cognito_user_pools=[user_pool],
            ),
        )

        # Outputs
        CfnOutput(self, "BetaAccessAdminApiUrl", value=beta_access_api.url)
        CfnOutput(self, "BetaAccessAdminLambdaArn", value=beta_access_lambda.function_arn)
        CfnOutput(self, "BetaAccessPermissionsTableName", value=beta_access_permissions_table.table_name)
        
        # Force resource inclusion by referencing them
        self.beta_access_lambda = beta_access_lambda
        self.beta_access_api = beta_access_api
        self.beta_access_permissions_table = beta_access_permissions_table

        # ========== MODEL DELIVERY ADMIN ==========
        model_delivery_table_arn = getattr(projects_table, "table_arn", "*")

        model_delivery_lambda_role = iam.Role(
            self, "ModelDeliveryAdminLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "ModelDeliveryAdminPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "cognito-idp:AdminGetUser",
                                "cognito-idp:ListUsers"
                            ],
                            resources=[user_pool.user_pool_arn]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:Query",
                                "dynamodb:Scan"
                            ],
                            resources=[
                                beta_access_permissions_table.table_arn,
                                model_delivery_table_arn,
                            ]
                        ),
                    ]
                )
            }
        )

        model_delivery_lambda = lambda_.Function(
            self, "Spaceport-ModelDeliveryAdminFunction",
            function_name=f"Spaceport-ModelDeliveryAdminFunction-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                os.path.join(os.path.dirname(__file__), "..", "lambda", "model_delivery_admin"),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                ),
            ),
            role=model_delivery_lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "COGNITO_USER_POOL_ID": user_pool.user_pool_id,
                "PROJECTS_TABLE_NAME": projects_table.table_name,
                "PERMISSIONS_TABLE_NAME": beta_access_permissions_table.table_name,
                "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", ""),
            },
        )

        # Grant table access
        beta_access_permissions_table.grant_read_write_data(model_delivery_lambda)
        projects_table.grant_read_write_data(model_delivery_lambda)

        model_delivery_api = apigw.RestApi(
            self, "Spaceport-ModelDeliveryAdminApi",
            rest_api_name=f"Spaceport-ModelDeliveryAdminApi-{suffix}",
            description="Model delivery admin API for sending model links to clients",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "authorization",
                    "X-Amz-Date",
                    "X-Amz-Security-Token",
                ],
            ),
        )

        model_delivery_authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "ModelDeliveryAuthorizer",
            cognito_user_pools=[user_pool],
        )

        model_delivery_resource = model_delivery_api.root.add_resource("admin").add_resource("model-delivery")

        model_delivery_resource.add_resource("check-permission").add_method(
            "GET",
            apigw.LambdaIntegration(model_delivery_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=model_delivery_authorizer,
        )

        model_delivery_resource.add_resource("resolve-client").add_method(
            "POST",
            apigw.LambdaIntegration(model_delivery_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=model_delivery_authorizer,
        )

        model_delivery_resource.add_resource("send").add_method(
            "POST",
            apigw.LambdaIntegration(model_delivery_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=model_delivery_authorizer,
        )

        for response_type, label in (
            (apigw.ResponseType.DEFAULT_4_XX, "Default4XX"),
            (apigw.ResponseType.DEFAULT_5_XX, "Default5XX"),
        ):
            model_delivery_api.add_gateway_response(
                f"ModelDelivery{label}",
                type=response_type,
                response_headers={
                    "Access-Control-Allow-Origin": "'*'",
                    "Access-Control-Allow-Headers": "'Content-Type,Authorization,authorization,X-Amz-Date,X-Amz-Security-Token,X-Api-Key'",
                    "Access-Control-Allow-Methods": "'GET,POST,OPTIONS'",
                },
            )

        CfnOutput(self, "ModelDeliveryAdminApiUrl", value=model_delivery_api.url)

        self.model_delivery_lambda = model_delivery_lambda
        self.model_delivery_api = model_delivery_api

        # ========== LITCHI AUTOMATION ==========
        litchi_credentials_table = self._get_or_create_dynamodb_table(
            construct_id="Spaceport-LitchiCredentialsTable",
            preferred_name=f"Spaceport-LitchiCredentials-{suffix}",
            fallback_name="Spaceport-LitchiCredentials",
            partition_key_name="userId",
            partition_key_type=dynamodb.AttributeType.STRING,
        )

        litchi_kms_key = kms.Key(
            self,
            "Spaceport-LitchiCredentialsKey",
            description="KMS key for encrypting Litchi session cookies",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,
        )
        kms.Alias(
            self,
            "Spaceport-LitchiCredentialsKeyAlias",
            alias_name=f"alias/spaceport-litchi-credentials-{suffix}",
            target_key=litchi_kms_key,
        )

        litchi_worker_role = iam.Role(
            self,
            "LitchiWorkerLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
        )
        litchi_credentials_table.grant_read_write_data(litchi_worker_role)
        litchi_kms_key.grant_encrypt_decrypt(litchi_worker_role)

        litchi_worker_lambda = lambda_.DockerImageFunction(
            self,
            "Spaceport-LitchiWorkerFunction",
            function_name=f"Spaceport-LitchiWorkerContainerFunction-{suffix}",
            code=lambda_.DockerImageCode.from_image_asset(
                os.path.join(os.path.dirname(__file__), "..", "lambda", "litchi_worker"),
            ),
            role=litchi_worker_role,
            timeout=Duration.minutes(5),
            memory_size=2048,
            environment={
                "LITCHI_CREDENTIALS_TABLE": litchi_credentials_table.table_name,
                "LITCHI_KMS_KEY_ID": litchi_kms_key.key_id,
                "LITCHI_WORKER_DRY_RUN": "0",
            },
        )

        litchi_stepfunctions_log_group = logs.LogGroup(
            self,
            "LitchiStepFunctionsLogGroup",
            log_group_name=f"/aws/stepfunctions/litchi-{suffix}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        litchi_state_machine_role = iam.Role(
            self,
            "LitchiStateMachineRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )
        litchi_worker_lambda.grant_invoke(litchi_state_machine_role)

        worker_task = sfn_tasks.LambdaInvoke(
            self,
            "LitchiUploadWorker",
            lambda_function=litchi_worker_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "mode": "upload",
                    "userId.$": "$.userId",
                    "mission.$": "$.mission",
                    "missionIndex.$": "$.missionIndex",
                    "missionTotal.$": "$.missionTotal",
                }
            ),
            payload_response_only=True,
            result_path="$.worker",
        )
        worker_task.add_retry(
            errors=["RateLimitedError"],
            interval=Duration.seconds(60),
            max_attempts=3,
            backoff_rate=2.0,
        )

        jitter_wait = sfn.Wait(
            self,
            "LitchiJitterWait",
            time=sfn.WaitTime.seconds_path("$.worker.waitSeconds"),
        )

        litchi_map = sfn.Map(
            self,
            "LitchiMissionMap",
            items_path="$.missions",
            parameters={
                "userId.$": "$.userId",
                "mission.$": "$$.Map.Item.Value",
                "missionIndex.$": "$$.Map.Item.Index",
                "missionTotal.$": "$.totalMissions",
            },
        )
        litchi_map.iterator(worker_task.next(jitter_wait))

        litchi_state_machine = sfn.StateMachine(
            self,
            "LitchiUploadStateMachine",
            state_machine_name=f"Spaceport-LitchiUpload-{suffix}",
            definition=litchi_map,
            role=litchi_state_machine_role,
            logs=sfn.LogOptions(
                destination=litchi_stepfunctions_log_group,
                level=sfn.LogLevel.ALL,
                include_execution_data=True,
            ),
            timeout=Duration.hours(1),
        )

        litchi_api_role = iam.Role(
            self,
            "LitchiApiLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
        )
        litchi_credentials_table.grant_read_data(litchi_api_role)

        litchi_api_lambda = lambda_.Function(
            self,
            "Spaceport-LitchiApiFunction",
            function_name=f"Spaceport-LitchiApiFunction-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                os.path.join(os.path.dirname(__file__), "..", "lambda", "litchi_api"),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output",
                    ],
                ),
            ),
            role=litchi_api_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "LITCHI_CREDENTIALS_TABLE": litchi_credentials_table.table_name,
                "LITCHI_WORKER_FUNCTION": litchi_worker_lambda.function_name,
                "LITCHI_STATE_MACHINE_ARN": litchi_state_machine.state_machine_arn,
            },
        )

        litchi_worker_lambda.grant_invoke(litchi_api_lambda)
        litchi_state_machine.grant_start_execution(litchi_api_lambda)

        litchi_api = apigw.RestApi(
            self,
            "Spaceport-LitchiApi",
            rest_api_name=f"Spaceport-LitchiApi-{suffix}",
            description="Litchi automation API for Spaceport users",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "authorization",
                    "X-Amz-Date",
                    "X-Amz-Security-Token",
                ],
            ),
        )

        litchi_authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "LitchiAuthorizer",
            cognito_user_pools=[user_pool],
        )

        litchi_resource = litchi_api.root.add_resource("litchi")
        litchi_resource.add_resource("status").add_method(
            "GET",
            apigw.LambdaIntegration(litchi_api_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=litchi_authorizer,
        )
        litchi_resource.add_resource("connect").add_method(
            "POST",
            apigw.LambdaIntegration(litchi_api_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=litchi_authorizer,
        )
        litchi_resource.add_resource("test-connection").add_method(
            "POST",
            apigw.LambdaIntegration(litchi_api_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=litchi_authorizer,
        )
        litchi_resource.add_resource("upload").add_method(
            "POST",
            apigw.LambdaIntegration(litchi_api_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=litchi_authorizer,
        )

        for response_type, label in (
            (apigw.ResponseType.DEFAULT_4_XX, "Default4XX"),
            (apigw.ResponseType.DEFAULT_5_XX, "Default5XX"),
        ):
            litchi_api.add_gateway_response(
                f"Litchi{label}",
                type=response_type,
                response_headers={
                    "Access-Control-Allow-Origin": "'*'",
                    "Access-Control-Allow-Headers": "'Content-Type,Authorization,authorization,X-Amz-Date,X-Amz-Security-Token,X-Api-Key'",
                    "Access-Control-Allow-Methods": "'GET,POST,OPTIONS'",
                },
            )

        CfnOutput(self, "LitchiApiUrl", value=litchi_api.url)

        self.litchi_api = litchi_api
        self.litchi_api_lambda = litchi_api_lambda
        self.litchi_worker_lambda = litchi_worker_lambda
        self.litchi_state_machine = litchi_state_machine

        # ========== PASSWORD RESET SYSTEM ==========
        # Create DynamoDB table for password reset codes
        password_reset_codes_table = self._get_or_create_dynamodb_table(
            construct_id="Spaceport-PasswordResetCodesTable",
            preferred_name=f"Spaceport-PasswordResetCodes-{suffix}",
            fallback_name="Spaceport-PasswordResetCodes",
            partition_key_name="email",
            partition_key_type=dynamodb.AttributeType.STRING
        )

        # Create IAM role for password reset Lambda
        password_reset_lambda_role = iam.Role(
            self, "PasswordResetLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "PasswordResetPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "cognito-idp:AdminGetUser",
                                "cognito-idp:AdminSetUserPassword"
                            ],
                            resources=[user_pool.user_pool_arn]
                        )
                    ]
                )
            }
        )

        # Create password reset Lambda function
        password_reset_lambda = lambda_.Function(
            self, "Spaceport-PasswordResetFunction",
            function_name=f"Spaceport-PasswordResetFunction-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                os.path.join(os.path.dirname(__file__), "..", "lambda", "password_reset"),
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                ),
            ),
            role=password_reset_lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "COGNITO_USER_POOL_ID": user_pool.user_pool_id,
                "COGNITO_USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id,
                "RESET_CODES_TABLE": password_reset_codes_table.table_name,
                "RESEND_API_KEY": os.environ.get("RESEND_API_KEY", ""),
            },
        )

        # Create API Gateway for password reset
        password_reset_api = apigw.RestApi(
            self, "Spaceport-PasswordResetApi",
            rest_api_name=f"Spaceport-PasswordResetApi-{suffix}",
            description="Password reset API for Spaceport users",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "authorization",
                    "X-Amz-Date",
                    "X-Amz-Security-Token",
                ],
            ),
        )

        # Add password reset endpoint
        password_reset_resource = password_reset_api.root.add_resource("password-reset")
        password_reset_resource.add_method(
            "POST",
            apigw.LambdaIntegration(password_reset_lambda),
            authorization_type=apigw.AuthorizationType.NONE,  # No auth required for password reset
        )

        # Grant DynamoDB permissions to the Lambda function
        password_reset_codes_table.grant_read_write_data(password_reset_lambda)

        # Outputs
        CfnOutput(self, "PasswordResetApiUrl", value=password_reset_api.url)
        CfnOutput(self, "PasswordResetLambdaArn", value=password_reset_lambda.function_arn)
        
        # Force resource inclusion by referencing them
        self.password_reset_lambda = password_reset_lambda
        self.password_reset_api = password_reset_api
        self.password_reset_codes_table = password_reset_codes_table

    def _dynamodb_table_exists(self, table_name: str) -> bool:
        """Check if a DynamoDB table exists"""
        try:
            self.dynamodb_client.describe_table(TableName=table_name)
            return True
        except Exception:
            return False

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

    def _cognito_user_pool_exists(self, user_pool_name: str) -> bool:
        """Check if a Cognito User Pool exists"""
        try:
            # List all user pools and check if one with the given name exists
            response = self.cognito_client.list_user_pools(MaxResults=60)
            for pool in response.get('UserPools', []):
                if pool['Name'] == user_pool_name:
                    return True
            return False
        except Exception as e:
            print(f"Error checking if user pool exists: {e}")
            return False

    def _get_user_pool_id_by_name(self, user_pool_name: str) -> str:
        """Get user pool ID by name"""
        try:
            response = self.cognito_client.list_user_pools(MaxResults=60)
            for pool in response.get('UserPools', []):
                if pool['Name'] == user_pool_name:
                    return pool['Id']
            return None
        except Exception as e:
            print(f"Error getting user pool ID: {e}")
            return None

    def _get_or_create_user_pool(self, construct_id: str, preferred_name: str, fallback_name: str, pool_type: str) -> cognito.UserPool:
        """
        Import existing Cognito User Pool or create a new one if it doesn't exist.
        """
        # First try preferred name (with environment suffix)
        if self._cognito_user_pool_exists(preferred_name):
            print(f"Importing existing Cognito User Pool: {preferred_name}")
            pool_id = self._get_user_pool_id_by_name(preferred_name)
            if pool_id:
                return cognito.UserPool.from_user_pool_id(self, construct_id, pool_id)
        
        # Then try fallback name (without suffix)
        if self._cognito_user_pool_exists(fallback_name):
            print(f"Importing existing Cognito User Pool: {fallback_name}")
            pool_id = self._get_user_pool_id_by_name(fallback_name)
            if pool_id:
                return cognito.UserPool.from_user_pool_id(self, construct_id, pool_id)
        
        # Create new user pool with preferred name
        print(f"Creating new Cognito User Pool: {preferred_name}")
        return cognito.UserPool(
            self,
            construct_id,
            user_pool_name=preferred_name,
            self_sign_up_enabled=False,  # invite-only
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            sign_in_aliases=cognito.SignInAliases(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                preferred_username=cognito.StandardAttribute(required=True, mutable=False),
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
                temp_password_validity=Duration.days(7),
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.RETAIN,
        )

    def _get_or_create_client(self, user_pool: cognito.UserPool, construct_id: str, client_name: str) -> cognito.UserPoolClient:
        """
        Create or update CloudFormation-managed User Pool Client.
        CloudFormation will update existing clients instead of creating duplicates.
        """
        # Always create a CloudFormation-managed resource
        # CloudFormation will update existing clients instead of creating duplicates
        client = cognito.UserPoolClient(
            self, construct_id,
            user_pool=user_pool,
            user_pool_client_name=client_name,
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True, admin_user_password=True),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                callback_urls=[
                    "http://localhost:3000/",
                    "https://spcprt.com/",
                ],
                logout_urls=[
                    "http://localhost:3000/",
                    "https://spcprt.com/",
                ],
            ),
            prevent_user_existence_errors=True,
        )
        print(f"✅ CloudFormation-managed client: {client_name}")
        return client


# Force complete AuthStack redeployment with subscription resources
# This ensures all subscription resources (Lambda, API Gateway) are created
