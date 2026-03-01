#!/usr/bin/env python3
"""Unit tests for ML job ECR image resolution."""

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT / "infrastructure" / "spaceport_cdk"))
sys.path.append(str(REPO_ROOT / "infrastructure" / "spaceport_cdk" / "lambda" / "start_ml_job"))

from spaceport_cdk.branch_utils import get_ecr_branch_suffix  # type: ignore
from lambda_function import _resolve_ecr_uri  # type: ignore


class FakeRepoNotFound(Exception):
    def __init__(self):
        self.response = {"Error": {"Code": "RepositoryNotFoundException"}}


class FakeImageNotFound(Exception):
    def __init__(self):
        self.response = {"Error": {"Code": "ImageNotFoundException"}}


class FakeEcrClient:
    def __init__(self, existing_repos, existing_tags=None):
        self.existing_repos = set(existing_repos)
        self.existing_tags = set(existing_tags or set())

    def describe_repositories(self, repositoryNames):
        repo_name = repositoryNames[0]
        if repo_name not in self.existing_repos:
            raise FakeRepoNotFound()
        return {"repositories": [{"repositoryName": repo_name}]}

    def describe_images(self, repositoryName, imageIds):
        image_tag = imageIds[0]["imageTag"]
        if (repositoryName, image_tag) not in self.existing_tags:
            raise FakeImageNotFound()
        return {"imageDetails": [{"imageTags": [image_tag]}]}


def test_ml_development_uses_empty_ecr_tag():
    assert get_ecr_branch_suffix("ml-development") == ""


def test_agent_branch_uses_sanitized_ecr_tag():
    assert get_ecr_branch_suffix("agent-48276194-ndvs-push-baseline-gate") == "agent48276194ndvspushbaselinegate"


def test_long_lived_branch_prefers_shared_branch_tag_when_available():
    client = FakeEcrClient(
        {"spaceport/sfm-agent123", "spaceport/sfm"},
        {("spaceport/sfm", "agent123")},
    )
    uri = _resolve_ecr_uri(
        client,
        "123456789012",
        "us-west-2",
        "spaceport/sfm-agent123",
        "spaceport/sfm",
        "agent123",
    )
    assert uri == "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent123"


def test_branch_specific_repo_uses_latest_when_shared_branch_tag_missing():
    client = FakeEcrClient({"spaceport/sfm-agent123", "spaceport/sfm"})
    uri = _resolve_ecr_uri(
        client,
        "123456789012",
        "us-west-2",
        "spaceport/sfm-agent123",
        "spaceport/sfm",
        "agent123",
    )
    assert uri == "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm-agent123:latest"


def test_missing_branch_repo_falls_back_to_shared_branch_tag():
    client = FakeEcrClient(set())
    uri = _resolve_ecr_uri(
        client,
        "123456789012",
        "us-west-2",
        "spaceport/sfm-agent123",
        "spaceport/sfm",
        "agent123",
    )
    assert uri == "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent123"


def test_shared_repo_uses_latest_for_shared_branch():
    client = FakeEcrClient({"spaceport/sfm"})
    uri = _resolve_ecr_uri(
        client,
        "123456789012",
        "us-west-2",
        "spaceport/sfm",
        "spaceport/sfm",
        "",
    )
    assert uri == "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:latest"


def test_ml_development_ignores_stale_branch_repo_and_uses_shared_latest():
    client = FakeEcrClient({"spaceport/sfm-mldevelopment", "spaceport/sfm"})
    uri = _resolve_ecr_uri(
        client,
        "123456789012",
        "us-west-2",
        "spaceport/sfm-mldevelopment",
        "spaceport/sfm",
        "",
    )
    assert uri == "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:latest"
