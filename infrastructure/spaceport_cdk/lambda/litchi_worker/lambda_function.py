import asyncio
import base64
import json
import logging
import os
import random
from urllib.parse import urlparse
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


LOGIN_URL = os.environ.get("LITCHI_LOGIN_URL", "https://flylitchi.com/hub")
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


def _jitter_seconds(low: int = 12, high: int = 25) -> int:
    return random.randint(low, high)


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
    except Exception:
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


async def _launch_context(storage_state: Optional[Dict[str, Any]] = None):
    if async_playwright is None:
        raise RuntimeError("playwright is not installed in the runtime")

    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    os.environ.setdefault("GALLIUM_DRIVER", "llvmpipe")

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
            "--use-gl=swiftshader",
            "--ignore-gpu-blocklist",
        ],
    )
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport=None,
        locale="en-US",
        storage_state=storage_state,
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


def _serialize_local_storage(storage: Dict[str, str], key_id: str) -> str:
    payload = json.dumps(storage)
    return _encrypt_text(payload, key_id)


def _deserialize_local_storage(ciphertext: str) -> Dict[str, str]:
    payload = _decrypt_text(ciphertext)
    return json.loads(payload)


def _serialize_session_storage(storage: Dict[str, str], key_id: str) -> str:
    payload = json.dumps(storage)
    return _encrypt_text(payload, key_id)


def _deserialize_session_storage(ciphertext: str) -> Dict[str, str]:
    payload = _decrypt_text(ciphertext)
    return json.loads(payload)


def _serialize_credentials(credentials: Dict[str, str], key_id: str) -> str:
    payload = json.dumps(credentials)
    return _encrypt_text(payload, key_id)


def _deserialize_credentials(ciphertext: str) -> Dict[str, str]:
    payload = _decrypt_text(ciphertext)
    return json.loads(payload)


def _serialize_storage_state(state: Dict[str, Any], key_id: str) -> str:
    payload = json.dumps(state)
    return _encrypt_text(payload, key_id)


def _deserialize_storage_state(ciphertext: str) -> Dict[str, Any]:
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


def _load_local_storage(table, user_id: str) -> Optional[Dict[str, str]]:
    record = _session_record(table, user_id)
    encrypted = record.get("localStorage")
    if not encrypted:
        return None
    return _deserialize_local_storage(encrypted)


def _load_session_storage(table, user_id: str) -> Optional[Dict[str, str]]:
    record = _session_record(table, user_id)
    encrypted = record.get("sessionStorage")
    if not encrypted:
        return None
    return _deserialize_session_storage(encrypted)


def _load_credentials(table, user_id: str) -> Optional[Dict[str, str]]:
    record = _session_record(table, user_id)
    encrypted = record.get("credentials")
    if not encrypted:
        return None
    return _deserialize_credentials(encrypted)


def _load_storage_state(table, user_id: str) -> Optional[Dict[str, Any]]:
    record = _session_record(table, user_id)
    encrypted = record.get("storageState")
    if not encrypted:
        return None
    return _deserialize_storage_state(encrypted)


def _save_credentials(table, user_id: str, username: str, password: str) -> None:
    record = _session_record(table, user_id)
    key_id = _require_kms_key()
    record["credentials"] = _serialize_credentials(
        {"username": username, "password": password},
        key_id,
    )
    record["updatedAt"] = _now_iso()
    _save_record(table, record)


def _save_storage_state(table, user_id: str, state: Dict[str, Any]) -> None:
    record = _session_record(table, user_id)
    key_id = _require_kms_key()
    record["storageState"] = _serialize_storage_state(state, key_id)
    record["updatedAt"] = _now_iso()
    _save_record(table, record)


def _save_cookies(
    table,
    user_id: str,
    cookies: List[Dict[str, Any]],
    status: str = "active",
    local_storage: Optional[Dict[str, str]] = None,
    session_storage: Optional[Dict[str, str]] = None,
) -> None:
    record = _session_record(table, user_id)
    key_id = _require_kms_key()
    record["cookies"] = _serialize_cookies(cookies, key_id)
    if local_storage is not None:
        record["localStorage"] = _serialize_local_storage(local_storage, key_id)
    if session_storage is not None:
        record["sessionStorage"] = _serialize_session_storage(session_storage, key_id)
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
    return "too many requests" in lowered or "rate limit" in lowered or "rate limited" in lowered


async def _login_in_page(
    page,
    username: str,
    password: str,
    two_factor_code: Optional[str] = None,
    force_form: bool = False,
) -> str:
    if not force_form:
        try:
            parse_login = await page.evaluate(
                """
                async ({ username, password }) => {
                  if (!window.Parse || !window.Parse.User || !window.Parse.User.logIn) {
                    return { ok: false, reason: 'parse_unavailable' };
                  }
                  try {
                    const user = await window.Parse.User.logIn(username, password);
                    return { ok: true, user: Boolean(user) };
                  } catch (err) {
                    return { ok: false, error: String(err) };
                  }
                }
                """,
                {"username": username, "password": password},
            )
            if parse_login and isinstance(parse_login, dict):
                if parse_login.get("ok"):
                    return "success"
                logger.info("Parse login attempt did not succeed: %s", parse_login)
        except Exception as exc:
            logger.warning("Parse login attempt failed: %s", exc)

    login_link = page.get_by_role("link", name="Log In")
    if await login_link.count() == 0:
        login_link = page.get_by_role("link", name="Log in")
    if await login_link.count() == 0:
        login_link = page.get_by_text("Log In")
    if await login_link.count() > 0 and await login_link.first.is_visible():
        try:
            await _human_click(login_link.first, timeout_ms=8000, force_fallback=True)
        except PlaywrightTimeoutError:
            await login_link.first.evaluate("el => el.click()")
        await page.wait_for_timeout(int(_human_delay(0.4, 0.8) * 1000))

    login_dialog = page.get_by_role("dialog")
    if await login_dialog.count() > 0:
        await login_dialog.first.wait_for(state="visible", timeout=10000)
    login_modal = page.locator("#login-modal")
    if await login_modal.count() > 0 and await login_modal.first.is_visible():
        login_dialog = login_modal

    login_form = page.locator("form#login-form")
    try:
        await page.wait_for_selector("form#login-form", state="attached", timeout=10000)
    except PlaywrightTimeoutError:
        pass
    if await login_form.count() == 0:
        login_form = page.locator("form").filter(
            has=page.locator("input[type='email']")
        ).filter(
            has=page.locator("input[type='password']")
        )

    login_scope = page
    if await login_dialog.count() > 0:
        dialog_inputs = login_dialog.first.locator("input[type='email']")
        if await dialog_inputs.count() > 0:
            login_scope = login_dialog.first
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

    email_input = login_scope.locator("input[type='email']:visible")
    if await email_input.count() == 0:
        email_input = login_scope.locator("input[type='email']")
    if await email_input.count() == 0:
        email_input = login_scope.locator("input[name*='email'], input[id*='email']")
    if await email_input.count() == 0:
        email_input = login_scope.locator("input[name*='user'], input[id*='user']")
    if await email_input.count() == 0:
        email_input = login_scope.locator("input[type='text']:visible")
    if await email_input.count() == 0:
        email_input = login_scope.locator("input[type='text']")
    if await email_input.count() == 0:
        email_input = login_scope.get_by_label("Email")
    if await email_input.count() > 1:
        email_input = email_input.first
    if await email_input.count() == 0:
        return "error"
    await _human_type(email_input, username)

    password_input = login_scope.locator("input[type='password']:visible")
    if await password_input.count() == 0:
        password_input = login_scope.locator("input[type='password']")
    if await password_input.count() == 0:
        password_input = login_scope.get_by_label("Password")
    if await password_input.count() > 1:
        password_input = password_input.first
    if await password_input.count() == 0:
        return "error"
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
    except PlaywrightTimeoutError:
        await login_button.evaluate("el => el.click()")

    await page.wait_for_timeout(int(_human_delay(0.6, 1.2) * 1000))

    two_factor_input = page.locator("input[name*='code']")
    for _ in range(20):
        if await two_factor_input.count() > 0 and await two_factor_input.first.is_visible():
            if not two_factor_code:
                return "pending_2fa"
            await _human_type(two_factor_input.first, str(two_factor_code))
            verify_button = page.get_by_role("button", name="Verify")
            if await verify_button.count() > 0:
                await _human_click(verify_button, timeout_ms=8000, force_fallback=True)
            await page.wait_for_timeout(int(_human_delay(0.8, 1.6) * 1000))
            return "success"

        for snippet in ("invalid", "incorrect", "wrong password", "failed"):
            login_error_text = page.get_by_text(snippet, exact=False)
            if await login_error_text.count() > 0 and await login_error_text.first.is_visible():
                return "invalid"

        parse_user = await page.evaluate(
            """
            () => Boolean(window.Parse && window.Parse.User && window.Parse.User.current && window.Parse.User.current())
            """
        )
        if parse_user:
            return "success"

        became_user = False
        try:
            became_user = await page.evaluate(
                """
                async () => {
                  if (!window.Parse || !window.Parse.User || !window.Parse.User.become) return false;
                  const key = Object.keys(localStorage).find((item) => item.includes('/currentUser'));
                  if (!key) return false;
                  try {
                    const raw = localStorage.getItem(key);
                    if (!raw) return false;
                    const value = JSON.parse(raw);
                    if (!value || !value.sessionToken) return false;
                    await window.Parse.User.become(value.sessionToken);
                    return true;
                  } catch (err) {
                    return false;
                  }
                }
                """
            )
        except Exception:
            became_user = False
        if became_user:
            logger.info("Attempted Parse.User.become from localStorage session token.")

        current_user = await page.evaluate(
            """
            () => {
              const key = Object.keys(localStorage).find((item) => item.includes('/currentUser'));
              if (!key) return null;
              return localStorage.getItem(key);
            }
            """
        )
        if current_user:
            return "success"

        await page.wait_for_timeout(1000)

    return "error"


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
        login_responses: List[str] = []
        page.on(
            "response",
            lambda response: login_responses.append(
                f"{response.status} {response.url}"
            )
            if any(
                key in response.url.lower()
                for key in ("login", "parse", "session", "users")
            ) and len(login_responses) < 10
            else None,
        )
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
        try:
            await page.wait_for_selector("form#login-form", state="attached", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        if await login_form.count() == 0:
            login_form = page.locator("form").filter(
                has=page.locator("input[type='email']")
            ).filter(
                has=page.locator("input[type='password']")
            )

        if await login_form.count() == 0:
            login_button = page.get_by_role("button", name="Log In")
            if await login_button.count() == 0:
                login_button = page.get_by_role("button", name="Login")
            if await login_button.count() == 0:
                login_button = page.get_by_role("button", name="Sign In")
            if await login_button.count() > 0:
                try:
                    await _human_click(login_button.first, timeout_ms=8000, force_fallback=True)
                except PlaywrightTimeoutError:
                    await login_button.first.evaluate("el => el.click()")
                await page.wait_for_timeout(1500)

            try:
                await page.wait_for_selector("form#login-form", state="attached", timeout=10000)
            except PlaywrightTimeoutError:
                pass

            login_form = page.locator("form#login-form")
            if await login_form.count() == 0:
                login_form = page.locator("form").filter(
                    has=page.locator("input[type='email']")
                ).filter(
                    has=page.locator("input[type='password']")
                )

        if await login_form.count() == 0 and LOGIN_URL != MISSIONS_URL:
            await page.goto(MISSIONS_URL, wait_until="domcontentloaded")
            login_dialog = page.get_by_role("dialog")
            if await login_dialog.count() > 0:
                await login_dialog.first.wait_for(state="visible", timeout=10000)
            try:
                await page.wait_for_selector("form#login-form", state="attached", timeout=10000)
            except PlaywrightTimeoutError:
                pass
            login_form = page.locator("form#login-form")
            if await login_form.count() == 0:
                login_form = page.locator("form").filter(
                    has=page.locator("input[type='email']")
                ).filter(
                    has=page.locator("input[type='password']")
                )
        login_scope = page
        if await login_dialog.count() > 0:
            dialog_inputs = login_dialog.first.locator("input[type='email']")
            if await dialog_inputs.count() > 0:
                login_scope = login_dialog.first
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
        logger.info(
            "Litchi login elements form_count=%s form_visible=%s email_count=%s password_count=%s",
            await login_form.count(),
            await login_form.first.is_visible() if await login_form.count() > 0 else False,
            await login_scope.locator("input[type='email']").count(),
            await login_scope.locator("input[type='password']").count(),
        )

        email_input = login_scope.locator("input[type='email']:visible")
        if await email_input.count() == 0:
            email_input = login_scope.locator("input[type='email']")
        if await email_input.count() == 0:
            email_input = login_scope.get_by_label("Email")
        if await email_input.count() > 1:
            email_input = email_input.first
        if await email_input.count() == 0:
            _mark_error(table, user_id, "Login form not available")
            return {"status": "error", "message": "Login form not available"}
        await _human_type(email_input, username)

        password_input = login_scope.locator("input[type='password']:visible")
        if await password_input.count() == 0:
            password_input = login_scope.locator("input[type='password']")
        if await password_input.count() == 0:
            password_input = login_scope.get_by_label("Password")
        if await password_input.count() > 1:
            password_input = password_input.first
        if await password_input.count() == 0:
            _mark_error(table, user_id, "Login form not available")
            return {"status": "error", "message": "Login form not available"}
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
        try:
            await password_input.press("Enter")
        except PlaywrightTimeoutError:
            pass

        await page.wait_for_timeout(int(_human_delay(0.8, 1.6) * 1000))

        two_factor_input = page.locator("input[name*='code']")
        current_user = None
        parse_user = False

        for _ in range(20):
            if await two_factor_input.count() > 0 and await two_factor_input.first.is_visible():
                break

            for snippet in ("invalid", "incorrect", "wrong password", "failed"):
                login_error_text = page.get_by_text(snippet, exact=False)
                if await login_error_text.count() > 0 and await login_error_text.first.is_visible():
                    _mark_error(table, user_id, "Invalid Litchi credentials")
                    return {"status": "error", "message": "Invalid Litchi credentials"}

            disabled_banner = page.get_by_text("temporarily disabled", exact=False)
            if await disabled_banner.count() > 0 and await disabled_banner.first.is_visible():
                message = (await disabled_banner.first.text_content()) or "Sign in temporarily disabled"
                _mark_error(table, user_id, message.strip())
                return {"status": "error", "message": message.strip()}

            parse_user = await page.evaluate(
                """
                () => Boolean(window.Parse && window.Parse.User && window.Parse.User.current && window.Parse.User.current())
                """
            )
            if parse_user:
                current_user = {"parse": True}
                break

            current_user = await page.evaluate(
                """
                () => {
                  const key = Object.keys(localStorage).find((item) => item.includes('/currentUser'));
                  if (!key) return null;
                  const value = localStorage.getItem(key);
                  return value ? { key, value } : null;
                }
                """
            )
            if current_user:
                break

            await page.wait_for_timeout(1000)

        if await two_factor_input.count() > 0 and await two_factor_input.first.is_visible():
            if not two_factor_code:
                _update_status(table, user_id, status="pending_2fa", message="Two-factor code required")
                return {"status": "pending_2fa", "message": "Two-factor code required"}
            await _human_type(two_factor_input.first, str(two_factor_code))
            verify_button = page.get_by_role("button", name="Verify")
            if await verify_button.count() > 0:
                await _human_click(verify_button, timeout_ms=8000, force_fallback=True)
            await page.wait_for_timeout(int(_human_delay(0.8, 1.6) * 1000))

        await page.goto(MISSIONS_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(int(_human_delay(2.0, 3.0) * 1000))

        current_user = None
        parse_user = await page.evaluate(
            """
            () => Boolean(window.Parse && window.Parse.User && window.Parse.User.current && window.Parse.User.current())
            """
        )
        if parse_user:
            current_user = {"parse": True}
        else:
            for _ in range(15):
                current_user = await page.evaluate(
                    """
                    () => {
                      const key = Object.keys(localStorage).find((item) => item.includes('/currentUser'));
                      if (!key) return null;
                      const value = localStorage.getItem(key);
                      return value ? { key, value } : null;
                    }
                    """
                )
                if current_user:
                    break
                await page.wait_for_timeout(1000)

        if not current_user:
            current_url = page.url
            page_title = await page.title()
            if "login" in current_url:
                _mark_error(table, user_id, "Login failed. Check your email and password.")
                return {"status": "error", "message": "Login failed"}

            login_form_after = page.locator("form#login-form")
            if await login_form_after.count() == 0:
                login_form_after = page.locator("form").filter(
                    has=page.locator("input[type='email']")
                ).filter(
                    has=page.locator("input[type='password']")
                )
            login_form_visible = await login_form_after.count() > 0 and await login_form_after.first.is_visible()

            login_link = page.get_by_role("link", name="Log In")
            login_link_visible = await login_link.count() > 0 and await login_link.first.is_visible()

            login_button = page.get_by_role("button", name="Log In")
            if await login_button.count() == 0:
                login_button = page.get_by_role("button", name="Login")
            login_button_visible = await login_button.count() > 0 and await login_button.first.is_visible()

            two_factor_visible = await page.locator("input[name*='code']").count() > 0
            captcha_visible = await page.locator(
                "iframe[src*='captcha'], iframe[src*='recaptcha'], iframe[src*='turnstile'], iframe[src*='challenges.cloudflare.com'], .cf-turnstile"
            ).count() > 0
            if login_responses:
                logger.info("Litchi login network activity: %s", " | ".join(login_responses))

            logger.info(
                "Litchi login diagnostics url=%s title=%s parse_user=%s local_storage=%s login_form=%s login_link=%s login_button=%s two_factor=%s captcha=%s",
                current_url,
                page_title,
                parse_user,
                bool(current_user),
                login_form_visible,
                login_link_visible,
                login_button_visible,
                two_factor_visible,
                captcha_visible,
            )

            if login_form_visible:
                _mark_error(table, user_id, "Login failed. Check your email and password.")
                return {"status": "error", "message": "Login failed"}

            if login_link_visible:
                _mark_error(table, user_id, "Login failed. Check your email and password.")
                return {"status": "error", "message": "Login failed"}

            if login_button_visible:
                _mark_error(table, user_id, "Login failed. Check your email and password.")
                return {"status": "error", "message": "Login failed"}

        _save_credentials(table, user_id, username, password)

        local_storage = await page.evaluate(
            """
            () => {
              const entries = {};
              for (const key of Object.keys(localStorage)) {
                const value = localStorage.getItem(key);
                if (value) entries[key] = value;
              }
              return entries;
            }
            """
        )
        session_storage = await page.evaluate(
            """
            () => {
              const entries = {};
              for (const key of Object.keys(sessionStorage)) {
                const value = sessionStorage.getItem(key);
                if (value) entries[key] = value;
              }
              return entries;
            }
            """
        )
        logger.info(
            "Captured local/session storage keys: local=%s session=%s",
            list(local_storage.keys()),
            list(session_storage.keys()),
        )
        try:
            storage_state = await context.storage_state()
            _save_storage_state(table, user_id, storage_state)
        except Exception as exc:
            logger.warning("Failed to capture storage state: %s", exc)
        cookies = await context.cookies()
        _save_cookies(
            table,
            user_id,
            cookies,
            status="active",
            local_storage=local_storage,
            session_storage=session_storage,
        )
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
    storage_state = _load_storage_state(table, user_id)
    if not cookies:
        _mark_expired(table, user_id, "No session cookies found")
        return {"status": "expired", "message": "No session cookies"}

    playwright, browser, context = await _launch_context(storage_state=storage_state)
    try:
        if not storage_state:
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
    relogin_attempted = bool(payload.get("reloginAttempted"))

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
    local_storage = _load_local_storage(table, user_id)
    session_storage = _load_session_storage(table, user_id)
    storage_state = _load_storage_state(table, user_id)
    if not cookies:
        _mark_expired(table, user_id, "Session cookies missing")
        return {"status": "expired", "message": "Session cookies missing"}

    if os.environ.get("LITCHI_WORKER_DRY_RUN") == "1":
        completed_progress = None
        if isinstance(mission_index, int) and mission_total:
            current = mission_index + 1
            completed_progress = {
                "current": current,
                "total": mission_total,
                "label": f"Uploaded {current}/{mission_total}",
            }
        _update_status(
            table,
            user_id,
            status="active",
            message=f"Uploaded {mission_name} (dry run)",
            progress=completed_progress,
        )
        return {"status": "ok", "message": "Dry run upload complete", "waitSeconds": _jitter_seconds()}

    playwright, browser, context = await _launch_context(storage_state=storage_state)
    try:
        if not storage_state:
            await context.add_cookies(cookies)
        if local_storage:
            logger.info("Restoring local storage keys: %s", list(local_storage.keys()))
        if session_storage:
            logger.info("Restoring session storage keys: %s", list(session_storage.keys()))
        if local_storage or session_storage:
            await context.add_init_script(
                f"""
                () => {{
                  const localEntries = {json.dumps(local_storage or {})};
                  for (const [key, value] of Object.entries(localEntries)) {{
                    localStorage.setItem(key, value);
                  }}
                  const sessionEntries = {json.dumps(session_storage or {})};
                  for (const [key, value] of Object.entries(sessionEntries)) {{
                    sessionStorage.setItem(key, value);
                  }}
                  window.__litchiLocalStorageApplied = Object.keys(localEntries).length;
                  window.__litchiSessionStorageApplied = Object.keys(sessionEntries).length;
                }}
                """
            )
        page = await context.new_page()
        await _apply_stealth(page)
        save_requests: List[str] = []
        save_responses: List[str] = []
        save_statuses: List[int] = []
        def _capture_save_request(request):
            if request.method in {"POST", "PUT", "PATCH"}:
                url = request.url.lower()
                if "google-analytics" in url or "g/collect" in url:
                    return
                save_requests.append(f"{request.method} {request.url}")

        def _capture_save_response(response):
            if response.request.method in {"POST", "PUT", "PATCH"}:
                url = response.url.lower()
                if "google-analytics" in url or "g/collect" in url:
                    return
                if "parse.litchiapi.com" in url or "mission" in url:
                    save_responses.append(f"{response.status} {response.url}")
                    save_statuses.append(response.status)
        page.on("request", _capture_save_request)
        page.on("response", _capture_save_response)
        response = await page.goto(MISSIONS_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(int(_human_delay(0.6, 1.2) * 1000))
        if (local_storage or session_storage) and not storage_state:
            applied_count = await page.evaluate("() => window.__litchiLocalStorageApplied || 0")
            applied_session = await page.evaluate("() => window.__litchiSessionStorageApplied || 0")
            logger.info(
                "Init script storage applied counts: local=%s session=%s",
                applied_count,
                applied_session,
            )

        response_status = response.status if response else None
        if response_status == 429:
            raise RateLimitedError("Rate limited by Litchi (HTTP 429). Retrying shortly.")
        if _detect_rate_limit(await page.content()):
            page_title = await page.title()
            logger.warning("Rate limit detection triggered url=%s title=%s status=%s", page.url, page_title, response_status)
            raise RateLimitedError("Rate limited by Litchi. Retrying shortly.")

        became_user = False
        try:
            became_user = await page.evaluate(
                """
                async () => {
                  if (!window.Parse || !window.Parse.User || !window.Parse.User.become) return false;
                  const key = Object.keys(localStorage).find((item) => item.includes('/currentUser'));
                  if (!key) return false;
                  try {
                    const raw = localStorage.getItem(key);
                    if (!raw) return false;
                    const value = JSON.parse(raw);
                    if (!value || !value.sessionToken) return false;
                    await window.Parse.User.become(value.sessionToken);
                    return true;
                  } catch (err) {
                    return false;
                  }
                }
                """
            )
        except Exception:
            became_user = False
        if became_user:
            logger.info("Attempted Parse.User.become from stored session token after restore.")

        current_user = await page.evaluate(
            """
            () => {
              const key = Object.keys(localStorage).find((item) => item.includes('/currentUser'));
              if (!key) return null;
              return localStorage.getItem(key);
            }
            """
        )
        parse_user = await page.evaluate(
            """
            () => Boolean(window.Parse && window.Parse.User && window.Parse.User.current && window.Parse.User.current())
            """
        )
        if not current_user and local_storage and not storage_state:
            logger.warning("No Parse currentUser found after restore. Reapplying localStorage and reloading.")
            await page.evaluate(
                """
                (entries) => {
                  for (const [key, value] of Object.entries(entries)) {
                    localStorage.setItem(key, value);
                  }
                }
                """,
                local_storage,
            )
            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_timeout(int(_human_delay(0.4, 0.8) * 1000))
            current_user = await page.evaluate(
                """
                () => {
                  const key = Object.keys(localStorage).find((item) => item.includes('/currentUser'));
                  if (!key) return null;
                  return localStorage.getItem(key);
                }
                """
            )
            parse_user = await page.evaluate(
                """
                () => Boolean(window.Parse && window.Parse.User && window.Parse.User.current && window.Parse.User.current())
                """
            )

        if not current_user or not parse_user:
            if not parse_user:
                logger.warning("No Parse currentUser available via Parse.User.current().")
            if not current_user:
                logger.warning("No Parse currentUser found in localStorage after reload.")
            if not relogin_attempted:
                credentials = _load_credentials(table, user_id)
                if credentials and credentials.get("username") and credentials.get("password"):
                    logger.info("Attempting Litchi re-login before upload.")
                    relogin_result = await _run_login_flow(
                        {
                            "userId": user_id,
                            "username": credentials["username"],
                            "password": credentials["password"],
                            "requestedAt": _now_iso(),
                        }
                    )
                    if isinstance(relogin_result, dict) and relogin_result.get("status") not in (None, "active"):
                        return relogin_result
                    retry_payload = dict(payload)
                    retry_payload["reloginAttempted"] = True
                    return await _run_upload_flow(retry_payload)
                _mark_expired(table, user_id, "Session expired. Please reconnect.")
                return {
                    "status": "expired",
                    "message": "Session expired",
                    "waitSeconds": _jitter_seconds(),
                }
            _mark_error(table, user_id, "Litchi session missing. Please reconnect.")
            return {
                "status": "error",
                "message": "Session missing",
                "waitSeconds": _jitter_seconds(),
            }

        login_link = page.get_by_role("link", name="Log In")
        if await login_link.count() > 0 and await login_link.first.is_visible():
            if not relogin_attempted:
                credentials = _load_credentials(table, user_id)
                if credentials and credentials.get("username") and credentials.get("password"):
                    logger.info("Attempting in-context Litchi re-login after login link detected.")
                    login_result = await _login_in_page(
                        page,
                        credentials["username"],
                        credentials["password"],
                        force_form=True,
                    )
                    if login_result == "pending_2fa":
                        _update_status(table, user_id, status="pending_2fa", message="Two-factor code required")
                        return {"status": "pending_2fa", "message": "Two-factor code required"}
                    if login_result == "invalid":
                        _mark_error(table, user_id, "Invalid Litchi credentials")
                        return {"status": "error", "message": "Invalid Litchi credentials"}
                    if login_result != "success":
                        _mark_error(table, user_id, "Login failed. Please reconnect.")
                        return {"status": "error", "message": "Login failed"}
                    local_storage = await page.evaluate(
                        """
                        () => {
                          const entries = {};
                          for (const key of Object.keys(localStorage)) {
                            const value = localStorage.getItem(key);
                            if (value) entries[key] = value;
                          }
                          return entries;
                        }
                        """
                    )
                    session_storage = await page.evaluate(
                        """
                        () => {
                          const entries = {};
                          for (const key of Object.keys(sessionStorage)) {
                            const value = sessionStorage.getItem(key);
                            if (value) entries[key] = value;
                          }
                          return entries;
                        }
                        """
                    )
                    try:
                        storage_state = await context.storage_state()
                        _save_storage_state(table, user_id, storage_state)
                    except Exception as exc:
                        logger.warning("Failed to capture storage state after re-login: %s", exc)
                    cookies = await context.cookies()
                    _save_cookies(
                        table,
                        user_id,
                        cookies,
                        status="active",
                        local_storage=local_storage,
                        session_storage=session_storage,
                    )
                    relogin_attempted = True
            _mark_expired(table, user_id, "Session expired, please reconnect")
            return {"status": "expired", "message": "Session expired"}

        if csv_content:
            await page.evaluate(
                """
                () => {
                  const modal = document.querySelector('#importmodal');
                  if (!modal) return;
                  modal.classList.add('show', 'in');
                  modal.style.display = 'block';
                  modal.style.visibility = 'visible';
                  modal.setAttribute('aria-hidden', 'false');
                  document.body.classList.add('modal-open');
                }
                """
            )
            await page.wait_for_timeout(int(_human_delay(0.4, 0.8) * 1000))
            import_input = page.locator("#fileimport")
            if await import_input.count() == 0:
                import_input = page.locator("input[type='file']:not(#import-dem-file)")
            if await import_input.count() == 0:
                raise RuntimeError("Import file input not found on Litchi hub")
            await import_input.first.set_input_files(
                {
                    "name": f"{mission_name}.csv",
                    "mimeType": "text/csv",
                    "buffer": csv_content.encode("utf-8"),
                }
            )

            import_button = page.locator("#importbtn")
            if await import_button.count() == 0:
                import_button = page.get_by_role("button", name="Import to new mission")
            if await import_button.count() == 0:
                import_button = page.get_by_text("Import to new mission")
            if await import_button.count() > 0:
                try:
                    await _human_click(import_button.first, timeout_ms=20000, force_fallback=True)
                except Exception as exc:
                    logger.warning("Import button click failed, forcing script click: %s", exc)
                    await import_button.first.evaluate("el => el.click()")
            await page.wait_for_timeout(int(_human_delay(0.9, 1.8) * 1000))
            await page.evaluate(
                """
                () => {
                  const modal = document.querySelector('#importmodal');
                  if (!modal) return;
                  modal.classList.remove('show', 'in');
                  modal.style.display = 'none';
                  modal.style.visibility = 'hidden';
                  modal.setAttribute('aria-hidden', 'true');
                  document.body.classList.remove('modal-open');
                  const backdrop = document.querySelector('.modal-backdrop');
                  if (backdrop) backdrop.remove();
                }
                """
            )

        name_input = page.locator("input[name='missionName'], input#missionName, input#mission-name")
        if await name_input.count() > 0:
            await _human_type(name_input.first, mission_name)

        missions_menu = page.locator("#dropdownMenuMissions")
        if await missions_menu.count() == 0:
            missions_menu = page.get_by_role("button", name="MISSIONS")
        if await missions_menu.count() > 0:
            await _human_click(missions_menu.first, timeout_ms=8000, force_fallback=True)
            await page.wait_for_timeout(int(_human_delay(0.4, 0.8) * 1000))

        save_menu_item = page.get_by_role("menuitem", name="Save...")
        if await save_menu_item.count() == 0:
            save_menu_item = page.get_by_text("Save...")
        if await save_menu_item.count() > 0:
            try:
                await _human_click(save_menu_item.first, timeout_ms=8000, force_fallback=True)
            except Exception as exc:
                logger.warning("Save menu click failed, forcing script click: %s", exc)
                await save_menu_item.first.evaluate("el => el.click()")
            await page.wait_for_timeout(int(_human_delay(0.6, 1.2) * 1000))

        await page.evaluate(
            """
            () => {
              const modal = document.querySelector('#downloadalert');
              if (!modal) return;
              modal.classList.add('show', 'in');
              modal.style.display = 'block';
              modal.style.visibility = 'visible';
              modal.setAttribute('aria-hidden', 'false');
              document.body.classList.add('modal-open');
            }
            """
        )
        download_modal = page.locator("#downloadalert")
        if await download_modal.count() > 0:
            await download_modal.first.wait_for(state="visible", timeout=8000)
            try:
                modal_buttons = await page.evaluate(
                    """
                    () => Array.from(document.querySelectorAll('#downloadalert button')).map(btn => ({
                      id: btn.id || '',
                      text: (btn.textContent || '').trim(),
                    }))
                    """
                )
                logger.info("Save modal buttons: %s", modal_buttons)
            except Exception:
                logger.warning("Unable to inspect save modal buttons")

        login_gate_present = False
        not_logged_in = page.locator("#save-notloggedin")
        login_gate_button = page.locator("#downloadalert button", has_text="Log in")
        if (await not_logged_in.count() > 0 and await not_logged_in.first.is_visible()) or (
            await login_gate_button.count() > 0 and await login_gate_button.first.is_visible()
        ):
            login_gate_present = True
            if not relogin_attempted:
                credentials = _load_credentials(table, user_id)
                if credentials and credentials.get("username") and credentials.get("password"):
                    logger.info("Attempting in-context Litchi re-login after save modal login gate.")
                    if await login_gate_button.count() > 0 and await login_gate_button.first.is_visible():
                        try:
                            await _human_click(login_gate_button.first, timeout_ms=8000, force_fallback=True)
                        except PlaywrightTimeoutError:
                            await login_gate_button.first.evaluate("el => el.click()")
                        await page.wait_for_timeout(int(_human_delay(0.4, 0.8) * 1000))
                    login_result = await _login_in_page(
                        page,
                        credentials["username"],
                        credentials["password"],
                        force_form=True,
                    )
                    if login_result == "pending_2fa":
                        _update_status(table, user_id, status="pending_2fa", message="Two-factor code required")
                        return {"status": "pending_2fa", "message": "Two-factor code required"}
                    if login_result == "invalid":
                        _mark_error(table, user_id, "Invalid Litchi credentials")
                        return {"status": "error", "message": "Invalid Litchi credentials"}
                    if login_result != "success":
                        _mark_error(table, user_id, "Login failed. Please reconnect.")
                        return {"status": "error", "message": "Login failed"}
                    local_storage = await page.evaluate(
                        """
                        () => {
                          const entries = {};
                          for (const key of Object.keys(localStorage)) {
                            const value = localStorage.getItem(key);
                            if (value) entries[key] = value;
                          }
                          return entries;
                        }
                        """
                    )
                    session_storage = await page.evaluate(
                        """
                        () => {
                          const entries = {};
                          for (const key of Object.keys(sessionStorage)) {
                            const value = sessionStorage.getItem(key);
                            if (value) entries[key] = value;
                          }
                          return entries;
                        }
                        """
                    )
                    try:
                        storage_state = await context.storage_state()
                        _save_storage_state(table, user_id, storage_state)
                    except Exception as exc:
                        logger.warning("Failed to capture storage state after re-login: %s", exc)
                    cookies = await context.cookies()
                    _save_cookies(
                        table,
                        user_id,
                        cookies,
                        status="active",
                        local_storage=local_storage,
                        session_storage=session_storage,
                    )
                    relogin_attempted = True

                    missions_menu = page.locator("#dropdownMenuMissions")
                    if await missions_menu.count() == 0:
                        missions_menu = page.get_by_role("button", name="MISSIONS")
                    if await missions_menu.count() > 0:
                        await _human_click(missions_menu.first, timeout_ms=8000, force_fallback=True)
                        await page.wait_for_timeout(int(_human_delay(0.4, 0.8) * 1000))

                    save_menu_item = page.get_by_role("menuitem", name="Save...")
                    if await save_menu_item.count() == 0:
                        save_menu_item = page.get_by_text("Save...")
                    if await save_menu_item.count() > 0:
                        try:
                            await _human_click(save_menu_item.first, timeout_ms=8000, force_fallback=True)
                        except Exception as exc:
                            logger.warning("Save menu click failed after re-login, forcing script click: %s", exc)
                            await save_menu_item.first.evaluate("el => el.click()")
                        await page.wait_for_timeout(int(_human_delay(0.6, 1.2) * 1000))

                    await page.evaluate(
                        """
                        () => {
                          const modal = document.querySelector('#downloadalert');
                          if (!modal) return;
                          modal.classList.add('show', 'in');
                          modal.style.display = 'block';
                          modal.style.visibility = 'visible';
                          modal.setAttribute('aria-hidden', 'false');
                          document.body.classList.add('modal-open');
                        }
                        """
                    )
                    download_modal = page.locator("#downloadalert")
                    if await download_modal.count() > 0:
                        await download_modal.first.wait_for(state="visible", timeout=8000)
                    not_logged_in = page.locator("#save-notloggedin")
                    login_gate_button = page.locator("#downloadalert button", has_text="Log in")
                    login_gate_present = (await not_logged_in.count() > 0 and await not_logged_in.first.is_visible()) or (
                        await login_gate_button.count() > 0 and await login_gate_button.first.is_visible()
                    )

        login_modal = page.locator("#login-modal")
        if await login_modal.count() > 0 and await login_modal.first.is_visible():
            credentials = _load_credentials(table, user_id)
            if not credentials or not credentials.get("username") or not credentials.get("password"):
                _mark_error(table, user_id, "Missing Litchi credentials for login modal")
                return {"status": "error", "message": "Missing Litchi credentials"}
            logger.info("Login modal detected during save. Attempting in-modal login.")
            login_modal_iframe = login_modal.first.locator("iframe")
            if await login_modal_iframe.count() > 0:
                logger.info("Login modal contains iframe; attempting frame-based login.")
                frame_locator = page.frame_locator("#login-modal iframe")
                email_input = frame_locator.locator(
                    "input[type='email'], input[name*='email'], input[id*='email'], input[name*='user'], input[id*='user'], input[type='text']"
                )
                password_input = frame_locator.locator("input[type='password']")
                if await email_input.count() > 0 and await password_input.count() > 0:
                    await _human_type(email_input.first, credentials["username"])
                    await _human_type(password_input.first, credentials["password"])
                    login_button = frame_locator.get_by_role("button", name="Log in")
                    if await login_button.count() == 0:
                        login_button = frame_locator.get_by_role("button", name="Login")
                    if await login_button.count() == 0:
                        login_button = frame_locator.locator("button[type='submit'], button#signin")
                    if await login_button.count() > 0:
                        await _human_click(login_button.first, timeout_ms=8000, force_fallback=True)
                        await page.wait_for_timeout(int(_human_delay(0.8, 1.6) * 1000))
            login_result = await _login_in_page(
                page,
                credentials["username"],
                credentials["password"],
                force_form=True,
            )
            if login_result == "pending_2fa":
                _update_status(table, user_id, status="pending_2fa", message="Two-factor code required")
                return {"status": "pending_2fa", "message": "Two-factor code required"}
            if login_result == "invalid":
                _mark_error(table, user_id, "Invalid Litchi credentials")
                return {"status": "error", "message": "Invalid Litchi credentials"}
            if login_result != "success":
                _mark_error(table, user_id, "Login failed. Please reconnect.")
                return {"status": "error", "message": "Login failed"}
            await page.evaluate(
                """
                () => {
                  const modal = document.querySelector('#login-modal');
                  if (!modal) return;
                  modal.classList.remove('show', 'in');
                  modal.style.display = 'none';
                  modal.style.visibility = 'hidden';
                  modal.setAttribute('aria-hidden', 'true');
                  document.body.classList.remove('modal-open');
                  const backdrop = document.querySelector('.modal-backdrop');
                  if (backdrop) backdrop.remove();
                }
                """
            )
            await page.wait_for_timeout(int(_human_delay(0.4, 0.8) * 1000))
            download_modal = page.locator("#downloadalert")
            if await download_modal.count() == 0 or not await download_modal.first.is_visible():
                missions_menu = page.locator("#dropdownMenuMissions")
                if await missions_menu.count() == 0:
                    missions_menu = page.get_by_role("button", name="MISSIONS")
                if await missions_menu.count() > 0:
                    await _human_click(missions_menu.first, timeout_ms=8000, force_fallback=True)
                    await page.wait_for_timeout(int(_human_delay(0.4, 0.8) * 1000))
                save_menu_item = page.get_by_role("menuitem", name="Save...")
                if await save_menu_item.count() == 0:
                    save_menu_item = page.get_by_text("Save...")
                if await save_menu_item.count() > 0:
                    await _human_click(save_menu_item.first, timeout_ms=8000, force_fallback=True)
                    await page.wait_for_timeout(int(_human_delay(0.6, 1.2) * 1000))
                await page.evaluate(
                    """
                    () => {
                      const modal = document.querySelector('#downloadalert');
                      if (!modal) return;
                      modal.classList.add('show', 'in');
                      modal.style.display = 'block';
                      modal.style.visibility = 'visible';
                      modal.setAttribute('aria-hidden', 'false');
                      document.body.classList.add('modal-open');
                    }
                    """
                )
                if await download_modal.count() > 0:
                    await download_modal.first.wait_for(state="visible", timeout=8000)
            not_logged_in = page.locator("#save-notloggedin")
            login_gate_button = page.locator("#downloadalert button", has_text="Log in")
            login_gate_present = (await not_logged_in.count() > 0 and await not_logged_in.first.is_visible()) or (
                await login_gate_button.count() > 0 and await login_gate_button.first.is_visible()
            )

        filename_input = page.locator("#filename")
        if await filename_input.count() > 0:
            await _human_type(filename_input.first, mission_name)

        save_button = page.locator("#downloadalert button#downloadbtn")
        if await save_button.count() == 0:
            save_button = page.locator("#downloadalert button", has_text="Save")
        if await save_button.count() == 0:
            save_button = page.get_by_role("button", name="Save")
        if await save_button.count() > 0:
            try:
                save_state = await save_button.first.evaluate(
                    "el => ({disabled: el.disabled, ariaDisabled: el.getAttribute('aria-disabled'), className: el.className})"
                )
                logger.info("Save button state: %s", save_state)
                save_details = await page.evaluate(
                    """
                    () => {
                      const btn = document.querySelector('#downloadalert #downloadbtn');
                      if (!btn) return null;
                      const onclick = btn.getAttribute('onclick');
                      const data = {};
                      for (const attr of Array.from(btn.attributes)) {
                        if (attr.name.startsWith('data-')) data[attr.name] = attr.value;
                      }
                      return {
                        id: btn.id,
                        text: (btn.textContent || '').trim(),
                        onclick: onclick ? onclick.slice(0, 200) : null,
                        data,
                      };
                    }
                    """
                )
                if save_details:
                    logger.info("Save button details: %s", save_details)
            except Exception:
                logger.warning("Unable to inspect save button state.")
            await _human_click(save_button.first, timeout_ms=8000, force_fallback=True)

        await page.wait_for_timeout(int(_human_delay(1.4, 2.4) * 1000))
        if save_requests:
            logger.info("Mission save requests (last 10): %s", " | ".join(save_requests[-10:]))
        else:
            logger.warning("No Mission save requests captured after save click.")
        if save_responses:
            logger.info("Mission save responses (last 10): %s", " | ".join(save_responses[-10:]))
            response_summary: Dict[str, int] = {}
            for entry in save_responses:
                try:
                    _, raw_url = entry.split(" ", 1)
                    host = urlparse(raw_url).netloc or raw_url
                except ValueError:
                    host = entry
                response_summary[host] = response_summary.get(host, 0) + 1
            logger.info("Mission save response summary: %s", response_summary)
        else:
            logger.warning("No Mission save responses captured after save click.")
        try:
            mission_check = await page.evaluate(
                """
                async (missionName) => {
                  if (!window.Parse || !window.Parse.Cloud || !window.Parse.Cloud.run) {
                    return { ok: false, reason: 'parse_unavailable' };
                  }
                  try {
                    const result = await window.Parse.Cloud.run('listMissionsV3', { limit: 200, skip: 1 });
                    const missions = result?.missions || result?.results || result?.data || [];
                    const names = Array.isArray(missions) ? missions.map((m) => m?.name).filter(Boolean) : [];
                    if (names.length) {
                      return { ok: true, count: names.length, found: names.includes(missionName) };
                    }
                    const tryQuery = async (className) => {
                      const query = new window.Parse.Query(className);
                      query.limit(50);
                      query.descending('updatedAt');
                      const results = await query.find();
                      return results.map((item) => item.get('name')).filter(Boolean);
                    };
                    const queryNames = await tryQuery('Mission').catch(() => tryQuery('MissionV3'));
                    return { ok: true, count: queryNames.length, found: queryNames.includes(missionName), source: 'query' };
                  } catch (err) {
                    const error =
                      err && typeof err === 'object'
                        ? JSON.stringify({ message: err.message, code: err.code, detail: err })
                        : String(err);
                    return { ok: false, error };
                  }
                }
                """,
                mission_name,
            )
            logger.info("Mission list check: %s", mission_check)
        except Exception as exc:
            logger.warning("Mission list check failed: %s", exc)
        save_success = any(200 <= status < 300 for status in save_statuses)
        if login_gate_present and not save_success:
            _mark_error(table, user_id, "Litchi session not authenticated for saving missions")
            return {
                "status": "error",
                "message": "Not logged in to save missions",
                "waitSeconds": _jitter_seconds(),
            }
        if not save_success:
            _mark_error(table, user_id, "Litchi mission save failed")
            return {
                "status": "error",
                "message": "Mission save failed",
                "waitSeconds": _jitter_seconds(),
            }
        completed_progress = None
        if isinstance(mission_index, int) and mission_total:
            current = mission_index + 1
            completed_progress = {
                "current": current,
                "total": mission_total,
                "label": f"Uploaded {current}/{mission_total}",
            }
        _update_status(
            table,
            user_id,
            status="active",
            message=f"Uploaded {mission_name}",
            progress=completed_progress,
        )
        return {"status": "ok", "message": f"Uploaded {mission_name}", "waitSeconds": _jitter_seconds()}
    except RateLimitedError as exc:
        _update_status(table, user_id, status="rate_limited", message=str(exc))
        raise
    except Exception as exc:
        logger.exception("Upload failed")
        _mark_error(table, user_id, f"Upload failed: {exc}")
        return {
            "status": "error",
            "message": "Upload failed",
            "waitSeconds": _jitter_seconds(),
        }
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
