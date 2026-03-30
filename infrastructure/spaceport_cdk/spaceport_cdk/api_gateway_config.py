def resolve_auth_api_endpoint_type(deployment_class: str) -> str | None:
    if deployment_class == "production":
        return None
    return "REGIONAL"
