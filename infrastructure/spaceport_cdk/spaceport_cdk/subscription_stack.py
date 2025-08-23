from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_logs as logs,
    Duration,
    CfnOutput,
    RemovalPolicy,
)
from constructs import Construct
import os


class SubscriptionStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDB table for subscriptions
        subscriptions_table = dynamodb.Table(
            self,
            "Spaceport-SubscriptionsTable",
            table_name="Spaceport-Subscriptions",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
        )

        # Add GSI for referral tracking
        subscriptions_table.add_global_secondary_index(
            index_name="ReferralIndex",
            partition_key=dynamodb.Attribute(
                name="referredBy",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Add GSI for subscription status
        subscriptions_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="updatedAt",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Create Lambda execution role
        subscription_lambda_role = iam.Role(
            self,
            "Subscription-LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add DynamoDB permissions
        subscriptions_table.grant_read_write_data(subscription_lambda_role)

        # Add Cognito permissions
        subscription_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:AdminUpdateUserAttributes",
                    "cognito-idp:AdminGetUser",
                ],
                resources=["*"]  # You may want to restrict this to specific user pools
            )
        )

        # Add SES permissions for email notifications
        subscription_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                resources=["*"]
            )
        )

        # Create subscription manager Lambda function
        subscription_lambda = lambda_.Function(
            self,
            "Spaceport-SubscriptionManager",
            function_name="Spaceport-SubscriptionManager",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/subscription_manager"),
            role=subscription_lambda_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "SUBSCRIPTIONS_TABLE": subscriptions_table.table_name,
                "USERS_TABLE": "Spaceport-Users",  # Reference to existing users table
                "COGNITO_USER_POOL_ID": os.environ.get("COGNITO_USER_POOL_ID", ""),
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

        # Create API Gateway for subscription endpoints
        subscription_api = apigw.RestApi(
            self,
            "Spaceport-SubscriptionApi",
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
        
        # Create checkout session endpoint
        create_checkout_resource = subscription_resource.add_resource("create-checkout-session")
        create_checkout_resource.add_method(
            "POST",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.NONE,  # We'll handle auth in Lambda
        )

        # Webhook endpoint (no auth required for Stripe)
        webhook_resource = subscription_resource.add_resource("webhook")
        webhook_resource.add_method(
            "POST",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # Subscription status endpoint
        status_resource = subscription_resource.add_resource("subscription-status")
        status_resource.add_method(
            "GET",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.NONE,  # We'll handle auth in Lambda
        )

        # Cancel subscription endpoint
        cancel_resource = subscription_resource.add_resource("cancel-subscription")
        cancel_resource.add_method(
            "POST",
            apigw.LambdaIntegration(subscription_lambda),
            authorization_type=apigw.AuthorizationType.NONE,  # We'll handle auth in Lambda
        )

        # Outputs
        CfnOutput(self, "SubscriptionApiUrl", value=subscription_api.url)
        CfnOutput(self, "SubscriptionsTableName", value=subscriptions_table.table_name)
        CfnOutput(self, "SubscriptionLambdaArn", value=subscription_lambda.function_arn)

        # Add CloudWatch alarms for monitoring
        # TODO: Add CloudWatch alarms for error rates, duration, etc.
