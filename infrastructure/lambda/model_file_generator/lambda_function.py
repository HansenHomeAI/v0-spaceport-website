import json
import logging
from pathlib import Path
from typing import Any, Dict
import re

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "templates" / "viewer_template.html"
DEFAULT_CONFIG_PATH = BASE_DIR / "default_config.json"


def load_default_config() -> Dict[str, Any]:
    with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_template(template_name: str = 'viewer_template.html') -> str:
    template_path = BASE_DIR / 'templates' / template_name
    if not template_path.exists():
        raise FileNotFoundError(f'Template {template_name} not found at {template_path}')
    with template_path.open('r', encoding='utf-8') as f:
        return f.read()


def deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def update_template_with_config(template: str, config: Dict[str, Any]) -> str:
    pretty_json = json.dumps(config, indent=2)
    # Replace config script block
    pattern = re.compile(
        r'(\<script id="viewer-config" type="application/json"\>\n)(.*?)(\n\s*\</script\>)',
        re.DOTALL,
    )

    def replacement(match: re.Match) -> str:
        indent = "    "
        json_block = "\n".join(f"{indent}{line}" for line in pretty_json.splitlines())
        return f"{match.group(1)}{json_block}{match.group(3)}"

    updated_html, count = pattern.subn(replacement, template, count=1)
    if count == 0:
        raise ValueError("viewer-config script tag not found in template")

    # Update the document <title> tag to match config page title if present
    page_title = config.get("page", {}).get("title")
    if page_title:
        updated_html = re.sub(
            r"<title>.*?</title>", f"<title>{page_title}</title>", updated_html, count=1
        )
    return updated_html


def apply_source_link(config: Dict[str, Any], source_link: str) -> None:
    if not source_link:
        return
    viewer = config.setdefault("viewer", {})
    splats = viewer.setdefault("splats", {})
    primary = splats.setdefault("splat1", {})
    primary["source"] = source_link


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    try:
        LOGGER.info("Received event: %s", json.dumps(event or {}))
        event = event or {}

        source_link = event.get("source_link") or event.get("sourceLink")
        overrides = (
            event.get("fine_tune_config")
            or event.get("fineTuneConfig")
            or event.get("config_overrides")
            or event.get("configOverrides")
            or event.get("config")
            or {}
        )

        if overrides and not isinstance(overrides, dict):
            raise ValueError("fine_tune_config/config_overrides must be an object")

        config = load_default_config()
        apply_source_link(config, source_link)
        if overrides:
            LOGGER.info("Merging overrides into default config")
            config = deep_merge(config, overrides)

        template_name = event.get('template_name') or event.get('templateName') or 'viewer_template.html'
        template = load_template(template_name)
        rendered_html = update_template_with_config(template, config)

        response_body = {
            "html": rendered_html,
            "config": config,
        }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response_body),
        }
    except Exception as exc:  # pragma: no cover - ensure errors propagate cleanly
        LOGGER.exception("Model file generation failed")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(exc)}),
        }
