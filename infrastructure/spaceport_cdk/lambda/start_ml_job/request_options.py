"""Request normalization helpers for the Start ML job Lambda."""

from __future__ import annotations

import re
from typing import Dict, Optional


DEFAULT_PIPELINE_STEP = "full"
DEFAULT_SFM_INSTANCE_TYPE = "ml.c6i.4xlarge"
DEFAULT_SFM_PROFILE_OVERRIDE = "auto"
VALID_PIPELINE_STEPS = {"full", "sfm", "3dgs", "compression"}
VALID_SFM_PROFILE_OVERRIDES = {"auto", "quality", "large_dataset"}
INSTANCE_TYPE_PATTERN = re.compile(r"^ml\.[a-z0-9][a-z0-9.-]*$", re.IGNORECASE)


def normalize_pipeline_step(raw_value: Optional[str]) -> str:
    """Normalize the requested starting pipeline step."""
    if raw_value is None:
        return DEFAULT_PIPELINE_STEP

    normalized = str(raw_value).strip().lower()
    if not normalized:
        return DEFAULT_PIPELINE_STEP
    if normalized not in VALID_PIPELINE_STEPS:
        raise ValueError(
            f"Unsupported pipelineStep: {raw_value!r}. "
            f"Expected one of {sorted(VALID_PIPELINE_STEPS)}."
        )
    return normalized


def normalize_sfm_options(raw_value: Optional[dict]) -> Dict[str, str]:
    """Normalize optional SfM runtime controls."""
    options = raw_value if isinstance(raw_value, dict) else {}

    raw_instance_type = options.get("instanceType", DEFAULT_SFM_INSTANCE_TYPE)
    instance_type = str(raw_instance_type).strip() or DEFAULT_SFM_INSTANCE_TYPE
    if not INSTANCE_TYPE_PATTERN.match(instance_type):
        raise ValueError(f"Invalid sfmOptions.instanceType: {raw_instance_type!r}")

    raw_profile_override = options.get("profileOverride", DEFAULT_SFM_PROFILE_OVERRIDE)
    profile_override = str(raw_profile_override).strip().lower() or DEFAULT_SFM_PROFILE_OVERRIDE
    if profile_override not in VALID_SFM_PROFILE_OVERRIDES:
        raise ValueError(
            f"Invalid sfmOptions.profileOverride: {raw_profile_override!r}. "
            f"Expected one of {sorted(VALID_SFM_PROFILE_OVERRIDES)}."
        )

    return {
        "instanceType": instance_type,
        "profileOverride": profile_override,
    }
