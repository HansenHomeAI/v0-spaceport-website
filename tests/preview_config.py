"""
Helpers for resolving API endpoints from a Cloudflare Pages preview deployment.

If BETA_READINESS_PREVIEW_URL (or PREVIEW_URL) is set, this module will fetch
the preview's API config and return endpoints aligned with that build's
NEXT_PUBLIC_* values.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

import requests


def _ensure_waitlist_endpoint(raw_url: Optional[str]) -> str:
    if not raw_url:
        return ""
    trimmed = raw_url.strip()
    if not trimmed:
        return ""

    try:
        from urllib.parse import urlparse, urlunparse
    except Exception:
        return trimmed

    parsed = urlparse(trimmed)
    segments = [segment for segment in parsed.path.split("/") if segment]
    if not any(segment.lower() == "waitlist" for segment in segments):
        segments.append("waitlist")
    new_path = "/" + "/".join(segments) if segments else "/waitlist"
    return urlunparse(parsed._replace(path=new_path))


def _fetch_preview_env() -> Optional[Dict[str, str]]:
    preview_url = os.getenv("BETA_READINESS_PREVIEW_URL") or os.getenv("PREVIEW_URL")
    if not preview_url:
        return None

    config_url = os.getenv("BETA_READINESS_API_CONFIG_URL") or f"{preview_url.rstrip('/')}/api/test-config"
    try:
        response = requests.get(config_url, timeout=10)
        response.raise_for_status()
        payload = response.json() or {}
    except Exception:
        return None

    if isinstance(payload, dict) and "env" in payload and isinstance(payload["env"], dict):
        return payload["env"]
    if isinstance(payload, dict):
        return payload
    return None


def resolve_api_endpoints(defaults: Dict[str, str]) -> Dict[str, str]:
    env = _fetch_preview_env()
    if not env:
        return defaults

    updated = dict(defaults)
    updated["projects"] = env.get("NEXT_PUBLIC_PROJECTS_API_URL") or updated.get("projects")
    updated["drone_path"] = env.get("NEXT_PUBLIC_DRONE_PATH_API_URL") or updated.get("drone_path")
    updated["file_upload"] = env.get("NEXT_PUBLIC_FILE_UPLOAD_API_URL") or updated.get("file_upload")
    updated["ml_pipeline"] = env.get("NEXT_PUBLIC_ML_PIPELINE_API_URL") or updated.get("ml_pipeline")
    waitlist_raw = env.get("NEXT_PUBLIC_WAITLIST_API_URL")
    if waitlist_raw:
        updated["waitlist"] = _ensure_waitlist_endpoint(waitlist_raw)

    return updated


def resolve_projects_api(default_value: str) -> str:
    env = _fetch_preview_env()
    if not env:
        return default_value
    return env.get("NEXT_PUBLIC_PROJECTS_API_URL") or default_value


def resolve_drone_api(default_value: str) -> str:
    env = _fetch_preview_env()
    if not env:
        return default_value
    return env.get("NEXT_PUBLIC_DRONE_PATH_API_URL") or default_value
