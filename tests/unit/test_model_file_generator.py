import importlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def lambda_module():
    module_path = Path('infrastructure/spaceport_cdk/lambda/model_file_generator/lambda_function.py')
    spec = importlib.util.spec_from_file_location('model_file_generator_lambda', module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Unable to load lambda module for tests')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lambda_handler_applies_overrides(lambda_module):
    event = {
        "source_link": "https://example.com/asset.splat",
        "fine_tune_config": {
            "page": {"title": "Unit Test Model"},
            "viewer": {
                "hotspots": [
                    {"text": "Test", "position": {"x": 1, "y": 2, "z": 3}, "scale": 0.5}
                ]
            },
        },
    }
    response = lambda_module.lambda_handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["config"]["viewer"]["splats"]["splat1"]["source"] == "https://example.com/asset.splat"
    assert body["config"]["page"]["title"] == "Unit Test Model"
    assert "<title>Unit Test Model</title>" in body["html"]
    assert "https://example.com/asset.splat" in body["html"]


def test_cli_local_generates_file(tmp_path: Path):
    config_file = tmp_path / "config.json"
    overrides = {
        "page": {"title": "CLI Model"},
        "viewer": {
            "splats": {
                "splat2": {"source": "https://example.com/secondary.splat"}
            }
        }
    }
    config_file.write_text(json.dumps(overrides), encoding="utf-8")

    output_file = tmp_path / "output.html"
    command = [
        sys.executable,
        str(Path("scripts") / "model_viewer_generator.py"),
        "--source-link",
        "https://example.com/primary.splat",
        "--config",
        str(config_file),
        "--output",
        str(output_file),
        "--mode",
        "local",
    ]
    subprocess.run(command, check=True)

    html = output_file.read_text(encoding="utf-8")
    assert "CLI Model" in html
    assert "https://example.com/primary.splat" in html
