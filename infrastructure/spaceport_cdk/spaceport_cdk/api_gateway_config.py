from typing import Optional


def resolve_auth_api_endpoint_type(deployment_class: str) -> Optional[str]:
    if deployment_class == "production":
        return None
    return "REGIONAL"
