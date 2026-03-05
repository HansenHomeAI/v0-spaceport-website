from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Dict


PRODUCTION_BRANCH = "main"
SHARED_STAGING_BRANCH = "development"
SHARED_STAGING_AUTH_STACK = "SpaceportAuthStagingStack"
PRODUCTION_AUTH_STACK = "SpaceportAuthProductionStack"
BRANCH_ID_LENGTH = 10


@dataclass(frozen=True)
class DeploymentContext:
    deployment_class: str
    branch_name: str
    branch_id: str
    resource_suffix: str
    stack_label: str
    spaceport_stack_name: str
    ml_stack_name: str
    auth_stack_name: str
    cdk_environment_name: str
    environment_name: str
    reuse_shared_auth: bool
    reuse_shared_ecr: bool
    allow_fallback_imports: bool
    deploy_auth_stack: bool

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _compute_branch_id(branch_name: str) -> str:
    digest = hashlib.sha1(branch_name.encode("utf-8")).hexdigest()
    return digest[:BRANCH_ID_LENGTH]


def resolve_deployment_context(branch_name: str) -> DeploymentContext:
    if not branch_name:
        raise ValueError("branch_name is required")

    if branch_name == PRODUCTION_BRANCH:
        return DeploymentContext(
            deployment_class="production",
            branch_name=branch_name,
            branch_id="",
            resource_suffix="prod",
            stack_label="Production",
            spaceport_stack_name="SpaceportProductionStack",
            ml_stack_name="SpaceportMLPipelineProductionStack",
            auth_stack_name=PRODUCTION_AUTH_STACK,
            cdk_environment_name="production",
            environment_name="production",
            reuse_shared_auth=False,
            reuse_shared_ecr=False,
            allow_fallback_imports=True,
            deploy_auth_stack=True,
        )

    if branch_name == SHARED_STAGING_BRANCH:
        return DeploymentContext(
            deployment_class="shared-staging",
            branch_name=branch_name,
            branch_id="",
            resource_suffix="staging",
            stack_label="Staging",
            spaceport_stack_name="SpaceportStagingStack",
            ml_stack_name="SpaceportMLPipelineStagingStack",
            auth_stack_name=SHARED_STAGING_AUTH_STACK,
            cdk_environment_name="staging",
            environment_name="staging",
            reuse_shared_auth=False,
            reuse_shared_ecr=False,
            allow_fallback_imports=True,
            deploy_auth_stack=True,
        )

    branch_id = _compute_branch_id(branch_name)
    stack_label = f"Preview{branch_id.upper()}"
    return DeploymentContext(
        deployment_class="branch-preview",
        branch_name=branch_name,
        branch_id=branch_id,
        resource_suffix=f"br-{branch_id}",
        stack_label=stack_label,
        spaceport_stack_name=f"Spaceport{stack_label}Stack",
        ml_stack_name=f"SpaceportML{stack_label}Stack",
        auth_stack_name=SHARED_STAGING_AUTH_STACK,
        cdk_environment_name="staging",
        environment_name="branch-preview",
        reuse_shared_auth=True,
        reuse_shared_ecr=True,
        allow_fallback_imports=False,
        deploy_auth_stack=False,
    )


def build_env_config(base_env_config: Dict[str, object], context: DeploymentContext) -> Dict[str, object]:
    env_config = dict(base_env_config)
    env_config.update(
        {
            "deploymentClass": context.deployment_class,
            "environmentName": context.environment_name,
            "resourceSuffix": context.resource_suffix,
            "sharedAuthStackName": context.auth_stack_name,
            "reuseSharedEcr": context.reuse_shared_ecr,
            "allowFallbackImports": context.allow_fallback_imports,
            "branchName": context.branch_name,
            "branchId": context.branch_id,
            "spaceportStackName": context.spaceport_stack_name,
            "mlStackName": context.ml_stack_name,
            "deployAuthStack": context.deploy_auth_stack,
        }
    )
    return env_config
