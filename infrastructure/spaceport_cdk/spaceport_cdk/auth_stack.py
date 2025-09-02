from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    # BundlingOptions,  # Not needed since we're importing existing Lambda functions
    CfnOutput,
    aws_cognito as cognito,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_logs as logs,
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

        # Environment-specific Cognito resources
        user_pool_v2 = cognito.UserPool(
            self,
            "SpaceportUserPoolV2",
            user_pool_name=f"Spaceport-Users-{suffix}",
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

        # Distinct group name to avoid collision with legacy pool
        cognito.CfnUserPoolGroup(
            self,
            "SpaceportBetaTestersGroupV2",
            user_pool_id=user_pool_v2.user_pool_id,
            group_name="beta-testers-v2",
            description="Approved beta testers allowed to sign in (v2)",
        )

        user_pool_client_v2 = user_pool_v2.add_client(
            "SpaceportUserPoolClientV2",
            user_pool_client_name="Spaceport-Web-Client-v2",
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True, admin_user_password=True),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                callback_urls=[
                    "http://localhost:3000/",
                    "https://spaceport.ai/",
                ],
                logout_urls=[
                    "http://localhost:3000/",
                    "https://spaceport.ai/",
                ],
            ),
            prevent_user_existence_errors=True,
        )

        CfnOutput(self, "CognitoUserPoolIdV2", value=user_pool_v2.user_pool_id)
        CfnOutput(self, "CognitoUserPoolClientIdV2", value=user_pool_client_v2.user_pool_client_id)

        # Import existing Lambda functions to avoid conflicts

        # Import existing invite Lambda function v2 to avoid conflicts
        invite_lambda_v2 = lambda_.Function.from_function_name(
            self,
            "Spaceport-InviteUserFunctionV2",
            "Spaceport-InviteUserFunctionV2"
        )

        # Note: Cannot modify IAM policies of imported Lambda functions
        # The required IAM permissions should be set manually in the Lambda console
        # or through a separate deployment process

        invite_api_v2 = apigw.RestApi(
            self,
            "Spaceport-InviteApiV2",
            rest_api_name="Spaceport-InviteApiV2",
            description="Invite approved users to Spaceport (v2)",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
        )

        invite_res_v2 = invite_api_v2.root.add_resource("invite")
        invite_res_v2.add_method("POST", apigw.LambdaIntegration(invite_lambda_v2, proxy=True))

        CfnOutput(self, "InviteApiUrlV2", value=f"{invite_api_v2.url}invite")

        # -------------------------------------
        # Alternate v3 pool to allow user-chosen handle at first sign-in
        # preferred_username is optional and mutable
        # -------------------------------------
        user_pool_v3 = cognito.UserPool(
            self,
            "SpaceportUserPoolV3",
            user_pool_name=f"Spaceport-Users-v3-{suffix}",
            self_sign_up_enabled=False,
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            sign_in_aliases=cognito.SignInAliases(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                preferred_username=cognito.StandardAttribute(required=False, mutable=True),
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

        cognito.CfnUserPoolGroup(
            self,
            "SpaceportBetaTestersGroupV3",
            user_pool_id=user_pool_v3.user_pool_id,
            group_name="beta-testers-v3",
            description="Approved beta testers allowed to sign in (v3)",
        )

        user_pool_client_v3 = user_pool_v3.add_client(
            "SpaceportUserPoolClientV3",
            user_pool_client_name="Spaceport-Web-Client-v3",
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True, admin_user_password=True),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                callback_urls=[
                    "http://localhost:3000/",
                    "https://spaceport.ai/",
                ],
                logout_urls=[
                    "http://localhost:3000/",
                    "https://spaceport.ai/",
                ],
            ),
            prevent_user_existence_errors=True,
        )

        CfnOutput(self, "CognitoUserPoolIdV3", value=user_pool_v3.user_pool_id)
        CfnOutput(self, "CognitoUserPoolClientIdV3", value=user_pool_client_v3.user_pool_client_id)

        # Import existing invite Lambda function v3 to avoid conflicts
        invite_lambda_v3 = lambda_.Function.from_function_name(
            self,
            "Spaceport-InviteUserFunctionV3",
            "Spaceport-InviteUserFunctionV3"
        )

        # Note: Cannot modify IAM policies of imported Lambda functions
        # The required IAM permissions should be set manually in the Lambda console
        # or through a separate deployment process

        invite_api_v3 = apigw.RestApi(
            self,
            "Spaceport-InviteApiV3",
            rest_api_name="Spaceport-InviteApiV3",
            description="Invite approved users to Spaceport (v3)",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
        )

        invite_res_v3 = invite_api_v3.root.add_resource("invite")
        invite_res_v3.add_method("POST", apigw.LambdaIntegration(invite_lambda_v3, proxy=True))

        CfnOutput(self, "InviteApiUrlV3", value=f"{invite_api_v3.url}invite")

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
            default_method_options=apigw.MethodOptions(
                authorization_type=apigw.AuthorizationType.COGNITO,
                authorizer=apigw.CognitoUserPoolsAuthorizer(
                    self,
                    "ProjectsAuthorizer",
                    cognito_user_pools=[user_pool_v2],
                ),
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
        proj_res = projects_api.root.add_resource("projects")
        proj_res.add_method("GET", apigw.LambdaIntegration(projects_lambda))
        proj_res.add_method("POST", apigw.LambdaIntegration(projects_lambda))
        proj_id = proj_res.add_resource("{id}")
        proj_id.add_method("GET", apigw.LambdaIntegration(projects_lambda))
        proj_id.add_method("PUT", apigw.LambdaIntegration(projects_lambda))
        proj_id.add_method("PATCH", apigw.LambdaIntegration(projects_lambda))
        proj_id.add_method("DELETE", apigw.LambdaIntegration(projects_lambda))

        CfnOutput(self, "ProjectsApiUrl", value=f"{projects_api.url}projects")

        # -------------------------------------
        # Subscription Management (integrated into AuthStack)
        # -------------------------------------
        
        # Dynamic users table - import if exists, create if not  
        users_table = self._get_or_create_dynamodb_table(
            construct_id="Spaceport-UsersTable",
            preferred_name=f"Spaceport-Users-{suffix}",
            fallback_name="Spaceport-Users",
            partition_key_name="id",
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
                "../lambda/subscription_manager"
            ),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "USERS_TABLE": users_table.table_name,
                "COGNITO_USER_POOL_ID": user_pool_v2.user_pool_id,
                "STRIPE_SECRET_KEY": os.environ.get("STRIPE_SECRET_KEY", ""),
                "STRIPE_WEBHOOK_SECRET": os.environ.get("STRIPE_WEBHOOK_SECRET", ""),
                "STRIPE_PRICE_SINGLE": os.environ.get("STRIPE_PRICE_SINGLE", ""),
                "STRIPE_PRICE_STARTER": os.environ.get("STRIPE_PRICE_STARTER", ""),
                "STRIPE_PRICE_GROWTH": os.environ.get("STRIPE_PRICE_GROWTH", ""),
                "REFERRAL_KICKBACK_PERCENTAGE": os.environ.get("REFERRAL_KICKBACK_PERCENTAGE", "10"),
                "EMPLOYEE_KICKBACK_PERCENTAGE": os.environ.get("EMPLOYEE_KICKBACK_PERCENTAGE", "30"),
                "COMPANY_KICKBACK_PERCENTAGE": os.environ.get("COMPANY_KICKBACK_PERCENTAGE", "70"),
                "REFERRAL_DURATION_MONTHS": os.environ.get("REFERRAL_DURATION_MONTHS", "6"),
                "EMPLOYEE_USER_ID": os.environ.get("EMPLOYEE_USER_ID", ""),
                "FRONTEND_URL": os.environ.get("FRONTEND_URL", "https://spaceport.ai"),
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
                resources=[user_pool_v2.user_pool_arn]
            )
        )

        # Add SES permissions for email notifications (optional)
        subscription_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                resources=["*"]
            )
        )

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
        create_checkout_resource.add_method(
            "POST",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self,
                "SubscriptionCreateAuthorizer",
                cognito_user_pools=[user_pool_v2],
            ),
        )

        # Webhook endpoint (no auth required for Stripe)
        webhook_resource = subscription_resource.add_resource("webhook")
        webhook_resource.add_method(
            "POST",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # Subscription status endpoint (requires auth)
        status_resource = subscription_resource.add_resource("subscription-status")
        status_resource.add_method(
            "GET",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self,
                "SubscriptionStatusAuthorizer",
                cognito_user_pools=[user_pool_v2],
            ),
        )

        # Cancel subscription endpoint (requires auth)
        cancel_resource = subscription_resource.add_resource("cancel-subscription")
        cancel_resource.add_method(
            "POST",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self,
                "SubscriptionCancelAuthorizer",
                cognito_user_pools=[user_pool_v2],
            ),
        )

        # Outputs
        CfnOutput(self, "SubscriptionApiUrl", value=subscription_api.url)
        CfnOutput(self, "SubscriptionLambdaArn", value=subscription_lambda.function_arn)
        
        # Debug: Ensure subscription resources are included in stack
        CfnOutput(self, "SubscriptionStackDebug", value="Subscription resources included in AuthStack")
        
        # Force resource inclusion by referencing them
        self.subscription_lambda = subscription_lambda
        self.subscription_api = subscription_api

        # -------------------------------------
        # Beta Access Admin Management
        # -------------------------------------
        
        # Dynamic permissions table for beta access admin
        permissions_table = self._get_or_create_dynamodb_table(
            construct_id="Spaceport-BetaAccessPermissionsTable",
            preferred_name=f"Spaceport-BetaAccessPermissions-{suffix}",
            fallback_name="Spaceport-BetaAccessPermissions",
            partition_key_name="user_id",
            partition_key_type=dynamodb.AttributeType.STRING
        )
        
        # Create beta access admin Lambda function
        beta_access_lambda = lambda_.Function(
            self,
            "BetaAccessAdminLambda",
            function_name=f"Spaceport-BetaAccessAdmin-{suffix}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                os.path.join(os.path.dirname(__file__), "..", "lambda", "beta_access_admin")
            ),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "COGNITO_USER_POOL_ID": user_pool_v2.user_pool_id,
                "PERMISSIONS_TABLE_NAME": permissions_table.table_name,
                "INVITE_API_KEY": os.environ.get("INVITE_API_KEY", ""),
            },
            log_retention=logs.RetentionDays.ONE_MONTH,
        )
        
        # Grant permissions
        permissions_table.grant_read_write_data(beta_access_lambda)
        
        # Add Cognito permissions for user management
        beta_access_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminAddUserToGroup",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:AdminUpdateUserAttributes",
                ],
                resources=[user_pool_v2.user_pool_arn]
            )
        )
        
        # Add SES permissions for sending invitation emails
        beta_access_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                resources=["*"]
            )
        )
        
        # Create beta access admin API Gateway
        beta_access_api = apigw.RestApi(
            self,
            "BetaAccessAdminApi",
            rest_api_name=f"Spaceport-BetaAccessAdmin-{suffix}",
            description="Beta access admin management API",
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
        
        # Add beta access admin endpoints
        admin_resource = beta_access_api.root.add_resource("admin")
        beta_resource = admin_resource.add_resource("beta-access")
        
        # Check permission endpoint (requires auth)
        check_permission_resource = beta_resource.add_resource("check-permission")
        check_permission_resource.add_method(
            "GET",
            apigw.LambdaIntegration(beta_access_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self,
                "BetaAccessCheckAuthorizer",
                cognito_user_pools=[user_pool_v2],
            ),
        )
        
        # Send invitation endpoint (requires auth)
        send_invitation_resource = beta_resource.add_resource("send-invitation")
        send_invitation_resource.add_method(
            "POST",
            apigw.LambdaIntegration(beta_access_lambda),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=apigw.CognitoUserPoolsAuthorizer(
                self,
                "BetaAccessSendAuthorizer",
                cognito_user_pools=[user_pool_v2],
            ),
        )
        
        # Outputs
        CfnOutput(self, "BetaAccessAdminApiUrl", value=beta_access_api.url)
        CfnOutput(self, "BetaAccessLambdaArn", value=beta_access_lambda.function_arn)
        
        # Force resource inclusion
        self.beta_access_lambda = beta_access_lambda
        self.beta_access_api = beta_access_api

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

    def _get_or_create_dynamodb_table(self, construct_id: str, preferred_name: str, fallback_name: str, 
                                     partition_key_name: str, partition_key_type: dynamodb.AttributeType) -> dynamodb.ITable:
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
                new_table = dynamodb.Table(
                    self, construct_id,
                    table_name=preferred_name,
                    partition_key=dynamodb.Attribute(
                        name=partition_key_name,
                        type=partition_key_type
                    ),
                    removal_policy=RemovalPolicy.RETAIN,
                    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
                )
                
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


# Force complete AuthStack redeployment with subscription resources
# This ensures all subscription resources (Lambda, API Gateway) are created
