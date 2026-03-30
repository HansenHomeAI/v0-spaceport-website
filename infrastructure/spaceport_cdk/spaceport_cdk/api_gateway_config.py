from typing import Optional


def resolve_auth_api_endpoint_type(deployment_class: str) -> Optional[str]:
    if deployment_class == "production":
        return None
    return "REGIONAL"


def should_serialize_auth_api_updates(deployment_class: str) -> bool:
    return resolve_auth_api_endpoint_type(deployment_class) == "REGIONAL"
