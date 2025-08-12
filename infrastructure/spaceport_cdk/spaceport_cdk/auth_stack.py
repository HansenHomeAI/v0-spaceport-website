from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_cognito as cognito,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
    aws_iam as iam,
)
from constructs import Construct
import os


class AuthStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Dedicated v2 Cognito resources – no overlap with legacy pool
        user_pool_v2 = cognito.UserPool(
            self,
            "SpaceportUserPoolV2",
            user_pool_name="Spaceport-Users-v2",
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

        # Invite Lambda & API scoped to v2 only
        lambda_dir = os.path.join(os.path.dirname(__file__), "..", "lambda")

        invite_lambda_v2 = lambda_.Function(
            self,
            "Spaceport-InviteUserFunctionV2",
            function_name="Spaceport-InviteUserFunctionV2",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset(os.path.join(lambda_dir, "invite_user")),
            handler="lambda_function.lambda_handler",
            environment={
                "COGNITO_USER_POOL_ID": user_pool_v2.user_pool_id,
                # Ensure users are added to the v2 group name
                "INVITE_GROUP": "beta-testers-v2",
            },
            timeout=Duration.seconds(30),
        )

        invite_lambda_v2.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminAddUserToGroup",
                ],
                resources=[
                    f"arn:aws:cognito-idp:{Stack.of(self).region}:{Stack.of(self).account}:userpool/*"
                ],
            )
        )

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


