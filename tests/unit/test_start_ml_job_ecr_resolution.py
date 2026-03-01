import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT / "infrastructure" / "spaceport_cdk"))

from spaceport_cdk.branch_utils import get_ecr_branch_suffix, get_resource_suffix, sanitize_branch_name


def _load_lambda_module():
    module_path = (
        REPO_ROOT
        / "infrastructure"
        / "spaceport_cdk"
        / "lambda"
        / "start_ml_job"
        / "lambda_function.py"
    )
    spec = importlib.util.spec_from_file_location("start_ml_job_lambda", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


lambda_module = _load_lambda_module()


def test_agent_branch_uses_shared_repo_branch_tag():
    uri = lambda_module._resolve_ecr_uri(
        "123456789012",
        "us-west-2",
        "spaceport/sfm",
        "agent90547182phase5densifyinterval",
    )
    assert (
        uri
        == "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent90547182phase5densifyinterval"
    )


def test_main_uses_shared_latest():
    uri = lambda_module._resolve_ecr_uri(
        "123456789012",
        "us-west-2",
        "spaceport/sfm",
        "",
    )
    assert uri == "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:latest"


def test_ml_development_uses_shared_latest():
    uri = lambda_module._resolve_ecr_uri(
        "123456789012",
        "us-west-2",
        "spaceport/sfm",
        "",
    )
    assert uri == "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:latest"


def test_branch_tag_derivation_for_ml_development_is_empty():
    assert get_ecr_branch_suffix("ml-development") == ""


def test_branch_tag_derivation_for_agent_branch_is_sanitized():
    assert get_ecr_branch_suffix("agent-90547182-phase5-densify-interval") == "agent90547182phase5densifyintervalbfc2a7"


def test_sanitize_branch_name_preserves_uniqueness_for_punctuation_variants():
    assert sanitize_branch_name("agent-a-b") != sanitize_branch_name("agentab")


def test_resource_suffix_stays_bucket_safe():
    suffix = get_resource_suffix("agent-90547182-phase5-densify-interval")
    assert len(suffix) <= 40
