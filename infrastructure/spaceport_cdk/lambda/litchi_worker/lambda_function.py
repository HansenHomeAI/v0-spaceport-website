import asyncio
import base64
import json
import logging
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3

try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except Exception:  # pragma: no cover - optional dependency at runtime
    PlaywrightTimeoutError = Exception
    async_playwright = None

try:
    from playwright_stealth import stealth_async
except Exception:  # pragma: no cover - optional dependency at runtime
    stealth_async = None


logger = logging.getLogger()
logger.setLevel(logging.INFO)


LOGIN_URL = os.environ.get("LITCHI_LOGIN_URL", "https://flylitchi.com")
MISSIONS_URL = os.environ.get("LITCHI_MISSIONS_URL", "https://flylitchi.com/hub")

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]


class RateLimitedError(Exception):
    """Raised when Litchi responds with rate limiting behavior."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jitter_seconds(low: int = 12, high: int = 25) -> float:
    return random.uniform(low, high)


def _human_delay(base_min: float = 0.04, base_max: float = 0.18) -> float:
    return random.uniform(base_min, base_max)


def _kms_client():
    return boto3.client("kms")


def _dynamodb_table():
    table_name = os.environ.get("LITCHI_CREDENTIALS_TABLE")
    if not table_name:
        raise RuntimeError("LITCHI_CREDENTIALS_TABLE is not configured")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


def _encrypt_text(plaintext: str, key_id: str) -> str:
    client = _kms_client()
    response = client.encrypt(KeyId=key_id, Plaintext=plaintext.encode("utf-8"))
    return base64.b64encode(response["CiphertextBlob"]).decode("utf-8")


def _decrypt_text(ciphertext: str) -> str:
    client = _kms_client()
    blob = base64.b64decode(ciphertext.encode("utf-8"))
    response = client.decrypt(CiphertextBlob=blob)
    return response["Plaintext"].decode("utf-8")


def _load_record(table, user_id: str) -> Dict[str, Any]:
    return table.get_item(Key={"userId": user_id}).get("Item", {})


def _save_record(table, record: Dict[str, Any]) -> None:
    table.put_item(Item=record)


def _append_log(record: Dict[str, Any], message: str) -> None:
    logs = list(record.get("logs", []))
    logs.append(f"[{_now_iso()}] {message}")
    record["logs"] = logs[-50:]


def _update_status(
    table,
    user_id: str,
    status: Optional[str] = None,
    message: Optional[str] = None,
    progress: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    record = _load_record(table, user_id)
    record.setdefault("userId", user_id)
    if status:
        record["status"] = status
    if message:
        record["message"] = message
        _append_log(record, message)
    if progress is not None:
        record["progress"] = progress
    record["updatedAt"] = _now_iso()
    _save_record(table, record)
    return record


async def _human_click(locator, *, timeout_ms: int = 30000, force_fallback: bool = False) -> None:
    await asyncio.sleep(_human_delay())
    box = await locator.bounding_box()
    click_kwargs = {"delay": int(_human_delay(0.08, 0.25) * 1000), "timeout": timeout_ms}
    if box:
        x = box["x"] + random.uniform(0.2, 0.8) * box["width"]
        y = box["y"] + random.uniform(0.2, 0.8) * box["height"]
        click_kwargs["position"] = {"x": x, "y": y}
    try:
        await locator.click(**click_kwargs)
    except PlaywrightTimeoutError:
        if not force_fallback:
            raise
        click_kwargs["force"] = True
        await locator.click(**click_kwargs)


async def _human_type(locator, text: str) -> None:
    await locator.click()
    await asyncio.sleep(_human_delay())
    await locator.fill("")
    await locator.type(text, delay=int(_human_delay(0.06, 0.14) * 1000))


async def _apply_stealth(page) -> None:
    if stealth_async:
        await stealth_async(page)


async def _launch_context():
    if async_playwright is None:
        raise RuntimeError("playwright is not installed in the runtime")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--no-zygote",
            "--single-process",
            "--disable-gpu",
        ],
    )
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": 1440, "height": 900},
        locale="en-US",
    )
    return playwright, browser, context


async def _close_context(playwright, browser) -> None:
    await browser.close()
    await playwright.stop()


def _serialize_cookies(cookies: List[Dict[str, Any]], key_id: str) -> str:
    payload = json.dumps(cookies)
    return _encrypt_text(payload, key_id)


def _deserialize_cookies(ciphertext: str) -> List[Dict[str, Any]]:
    payload = _decrypt_text(ciphertext)
    return json.loads(payload)


def _require_kms_key() -> str:
    key_id = os.environ.get("LITCHI_KMS_KEY_ID")
    if not key_id:
        raise RuntimeError("LITCHI_KMS_KEY_ID is not configured")
    return key_id


def _session_record(table, user_id: str) -> Dict[str, Any]:
    record = _load_record(table, user_id)
    if not record:
        record = {"userId": user_id, "status": "not_connected", "createdAt": _now_iso()}
        _save_record(table, record)
    return record


def _load_cookies(table, user_id: str) -> Optional[List[Dict[str, Any]]]:
    record = _session_record(table, user_id)
    encrypted = record.get("cookies")
    if not encrypted:
        return None
    return _deserialize_cookies(encrypted)


def _save_cookies(table, user_id: str, cookies: List[Dict[str, Any]], status: str = "active") -> None:
    record = _session_record(table, user_id)
    key_id = _require_kms_key()
    record["cookies"] = _serialize_cookies(cookies, key_id)
    record["status"] = status
    record["lastUsed"] = _now_iso()
    record["updatedAt"] = _now_iso()
    _append_log(record, "Session cookies refreshed")
    _save_record(table, record)


def _mark_expired(table, user_id: str, message: str) -> None:
    _update_status(table, user_id, status="expired", message=message)


def _mark_error(table, user_id: str, message: str) -> None:
    _update_status(table, user_id, status="error", message=message)


def _detect_rate_limit(content: str) -> bool:
    if not content:
        return False
    lowered = content.lower()
    return "too many requests" in lowered or "rate limit" in lowered or "429" in lowered


async def _run_login_flow(payload: Dict[str, Any]) -> Dict[str, Any]:
    table = _dynamodb_table()
    user_id = payload.get("userId")
    username = payload.get("username")
    password = payload.get("password")
    two_factor_code = payload.get("twoFactorCode")

    if not user_id or not username or not password:
        _mark_error(table, user_id or "unknown", "Missing login credentials")
        return {"status": "error", "message": "Missing login credentials"}

    _update_status(table, user_id, status="connecting", message="Starting Litchi login")

    playwright, browser, context = await _launch_context()
    try:
        page = await context.new_page()
        await _apply_stealth(page)
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        await asyncio.sleep(_human_delay(0.6, 1.2))

        login_link = page.get_by_role("link", name="Log In")
        if await login_link.count() == 0:
            login_link = page.get_by_role("link", name="Log in")
        if await login_link.count() == 0:
            login_link = page.get_by_text("Log In")
        if await login_link.count() > 0:
            try:
                await page.evaluate(
                    "document.documentElement.style.pointerEvents='auto';"
                    "document.body.style.pointerEvents='auto';"
                )
                await _human_click(login_link.first, timeout_ms=8000, force_fallback=True)
            except PlaywrightTimeoutError as exc:
                logger.warning("Login link click failed, falling back to script click: %s", exc)
                await login_link.first.evaluate("el => el.click()")
            await page.wait_for_timeout(int(_human_delay(0.5, 1.1) * 1000))

        login_dialog = page.get_by_role("dialog")
        if await login_dialog.count() > 0:
            await login_dialog.first.wait_for(state="visible", timeout=10000)

        login_form = page.locator("form#login-form")
        if await login_form.count() == 0:
            login_form = page.locator("form").filter(
                has=page.locator("input[type='email']")
            ).filter(
                has=page.locator("input[type='password']")
            )
        login_scope = login_dialog.first if await login_dialog.count() > 0 else page
        if await login_form.count() > 0:
            if not await login_form.first.is_visible():
                await page.evaluate(
                    """
                    () => {
                      const form = document.querySelector('form#login-form');
                      if (!form) return;
                      const modal = form.closest('.modal');
                      if (modal) {
                        modal.classList.add('show', 'in');
                        modal.style.display = 'block';
                      }
                      form.style.display = 'block';
                      form.style.visibility = 'visible';
                      document.body.classList.add('modal-open');
                    }
                    """
                )
            await login_form.first.wait_for(state="visible", timeout=8000)
            login_scope = login_form.first

        email_input = login_scope.locator("input[type='email']")
        if await email_input.count() == 0:
            email_input = login_scope.get_by_label("Email")
        if await email_input.count() > 1:
            email_input = email_input.first
        await _human_type(email_input, username)

        password_input = login_scope.locator("input[type='password']")
        if await password_input.count() == 0:
            password_input = login_scope.get_by_label("Password")
        if await password_input.count() > 1:
            password_input = password_input.first
        await _human_type(password_input, password)

        login_button = login_scope.get_by_role("button", name="Log in")
        if await login_button.count() == 0:
            login_button = login_scope.get_by_role("button", name="Sign in")
        if await login_button.count() == 0:
            login_button = login_scope.locator("button[type='submit'], button#signin")
        if await login_button.count() > 1:
            login_button = login_button.first
        try:
            await _human_click(login_button, timeout_ms=8000, force_fallback=True)
        except PlaywrightTimeoutError as exc:
            logger.warning("Login button click failed, falling back to script click: %s", exc)
            await login_button.evaluate("el => el.click()")

        await page.wait_for_timeout(int(_human_delay(0.8, 1.6) * 1000))

        disabled_banner = page.get_by_text("temporarily disabled", exact=False)
        if await disabled_banner.count() > 0:
            message = (await disabled_banner.first.text_content()) or "Sign in temporarily disabled"
            _mark_error(table, user_id, message.strip())
            return {"status": "error", "message": message.strip()}

        two_factor_input = page.locator("input[name*='code']")
        if await two_factor_input.count() > 0:
            if not two_factor_code:
                _update_status(table, user_id, status="pending_2fa", message="Two-factor code required")
                return {"status": "pending_2fa", "message": "Two-factor code required"}
            await _human_type(two_factor_input.first, str(two_factor_code))
            verify_button = page.get_by_role("button", name="Verify")
            if await verify_button.count() > 0:
                await _human_click(verify_button, timeout_ms=8000, force_fallback=True)
            await page.wait_for_timeout(int(_human_delay(0.8, 1.6) * 1000))

        await page.goto(MISSIONS_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(int(_human_delay(0.6, 1.2) * 1000))

        cookies = await context.cookies()
        _save_cookies(table, user_id, cookies, status="active")
        _update_status(table, user_id, status="active", message="Litchi session connected")
        return {"status": "active", "message": "Connected"}
    except Exception as exc:
        logger.exception("Login failed")
        _mark_error(table, user_id, f"Login failed: {exc}")
        return {"status": "error", "message": "Login failed"}
    finally:
        await _close_context(playwright, browser)


async def _run_test_flow(payload: Dict[str, Any]) -> Dict[str, Any]:
    table = _dynamodb_table()
    user_id = payload.get("userId")
    if not user_id:
        return {"status": "error", "message": "Missing userId"}

    _update_status(table, user_id, status="testing", message="Testing Litchi session")

    cookies = _load_cookies(table, user_id)
    if not cookies:
        _mark_expired(table, user_id, "No session cookies found")
        return {"status": "expired", "message": "No session cookies"}

    playwright, browser, context = await _launch_context()
    try:
        await context.add_cookies(cookies)
        page = await context.new_page()
        await _apply_stealth(page)
        await page.goto(MISSIONS_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(int(_human_delay(0.6, 1.2) * 1000))

        if _detect_rate_limit(await page.content()):
            raise RateLimitedError("Rate limit detected")

        _update_status(table, user_id, status="active", message="Connection healthy")
        return {"status": "healthy", "message": "Connection healthy"}
    except RateLimitedError as exc:
        _update_status(table, user_id, status="rate_limited", message=str(exc))
        raise
    except Exception as exc:
        logger.exception("Test connection failed")
        _mark_expired(table, user_id, f"Session check failed: {exc}")
        return {"status": "expired", "message": "Session expired"}
    finally:
        await _close_context(playwright, browser)


async def _run_healthcheck_flow() -> Dict[str, Any]:
    playwright, browser, context = await _launch_context()
    try:
        page = await context.new_page()
        await _apply_stealth(page)
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(int(_human_delay(0.4, 0.9) * 1000))
        return {"status": "ok", "message": "Browser launched"}
    except Exception as exc:
        logger.exception("Healthcheck failed")
        return {"status": "error", "message": f"Healthcheck failed: {exc}"}
    finally:
        await _close_context(playwright, browser)


async def _run_upload_flow(payload: Dict[str, Any]) -> Dict[str, Any]:
    table = _dynamodb_table()
    user_id = payload.get("userId")
    mission = payload.get("mission") or {}
    mission_name = mission.get("name") or "Spaceport Mission"
    csv_content = mission.get("csv")
    mission_index = payload.get("missionIndex")
    mission_total = payload.get("missionTotal")

    if not user_id:
        return {"status": "error", "message": "Missing userId"}

    progress = None
    if isinstance(mission_index, int) and mission_total:
        current = mission_index + 1
        progress = {
            "current": current,
            "total": mission_total,
            "label": f"Uploading {current}/{mission_total}",
        }

    _update_status(table, user_id, status="uploading", message=f"Uploading {mission_name}", progress=progress)

    cookies = _load_cookies(table, user_id)
    if not cookies:
        _mark_expired(table, user_id, "Session cookies missing")
        return {"status": "expired", "message": "Session cookies missing"}

    if os.environ.get("LITCHI_WORKER_DRY_RUN") == "1":
        _update_status(table, user_id, status="active", message=f"Uploaded {mission_name} (dry run)")
        return {"status": "ok", "message": "Dry run upload complete", "waitSeconds": _jitter_seconds()}

    playwright, browser, context = await _launch_context()
    try:
        await context.add_cookies(cookies)
        page = await context.new_page()
        await _apply_stealth(page)
        await page.goto(MISSIONS_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(int(_human_delay(0.6, 1.2) * 1000))

        if _detect_rate_limit(await page.content()):
            raise RateLimitedError("Rate limit detected")

        create_button = page.get_by_role("button", name="New Mission")
        if await create_button.count() == 0:
            create_button = page.get_by_text("New Mission")
        if await create_button.count() > 0:
            await _human_click(create_button)

        name_input = page.locator("input[name='missionName']")
        if await name_input.count() > 0:
            await _human_type(name_input, mission_name)

        if csv_content:
            upload_input = page.locator("input[type='file']")
            if await upload_input.count() > 0:
                await upload_input.set_input_files(
                    {
                        "name": f"{mission_name}.csv",
                        "mimeType": "text/csv",
                        "buffer": csv_content.encode("utf-8"),
                    }
                )

        save_button = page.get_by_role("button", name="Save")
        if await save_button.count() > 0:
            await _human_click(save_button)

        await page.wait_for_timeout(int(_human_delay(0.8, 1.6) * 1000))
        _update_status(table, user_id, status="active", message=f"Uploaded {mission_name}")
        return {"status": "ok", "message": f"Uploaded {mission_name}", "waitSeconds": _jitter_seconds()}
    except RateLimitedError as exc:
        _update_status(table, user_id, status="rate_limited", message=str(exc))
        raise
    except Exception as exc:
        logger.exception("Upload failed")
        _mark_error(table, user_id, f"Upload failed: {exc}")
        return {"status": "error", "message": "Upload failed"}
    finally:
        await _close_context(playwright, browser)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    mode = event.get("mode") or "upload"

    if mode == "login":
        return asyncio.run(_run_login_flow(event))

    if mode == "test":
        return asyncio.run(_run_test_flow(event))

    if mode == "healthcheck":
        return asyncio.run(_run_healthcheck_flow())

    if mode == "upload":
        return asyncio.run(_run_upload_flow(event))

    return {"status": "error", "message": "Unsupported mode"}
