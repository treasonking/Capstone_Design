from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_HTML = PROJECT_ROOT / "frontend" / "demo.html"
DEMO_ASYNC_TEST = PROJECT_ROOT / "frontend" / "demo_async.test.js"


def _html() -> str:
    return DEMO_HTML.read_text(encoding="utf-8")


def _inline_script() -> str:
    match = re.search(r"<script>([\s\S]*?)</script>", _html())
    assert match is not None
    return match.group(1)


def test_demo_ui_has_pre_auth_origin_and_no_default_admin_secret() -> None:
    html = _html()

    assert 'id="authApiBase"' in html
    assert html.index('id="authApiBase"') < html.index('id="authEmail"')
    assert 'id="adminToken" type="password"' in html
    assert 'value="dev-admin-token"' not in html
    assert 'id="adminActionFilter"' not in html


def test_demo_ui_pins_user_token_to_authenticated_origin() -> None:
    script = _inline_script()

    assert 'const ORIGIN_STORAGE_KEY = "orca_auth_origin"' in script
    assert "requestOrigin !== authOrigin" in script
    assert "Authorization: `Bearer ${authToken}`" in script
    assert "sessionStorage.setItem(ORIGIN_STORAGE_KEY, authOrigin)" in script


def test_demo_ui_distinguishes_errors_and_prevents_stale_results() -> None:
    script = _inline_script()

    for status in ("401", "403", "409", "422", "429"):
        assert f"status === {status}" in script
    assert "status >= 500" in script
    assert 'kind: "invalid-response"' in script
    assert '"timeout"' in script
    assert "proxyRequestSequence" in script
    assert "operation.version === inputVersion" in script
    assert "blockedInputVersion === inputVersion" in script


def test_demo_ui_separates_request_ownership_from_success_application() -> None:
    script = _inline_script()

    assert "function ownsAuthRequest(requestId, controller)" in script
    assert "function canApplyAuthSuccess(requestId, controller)" in script
    assert "function ownsAdminRequest(context)" in script
    assert "function canApplyAdminSuccess(context)" in script
    assert "ownsAuthRequest(requestId, controller)\n        && !controller.signal.aborted" in script
    assert "ownsAdminRequest(context)\n        && !context.controller.signal.aborted" in script
    assert "function isCurrentAuthRequest" not in script
    assert "function isCurrentAdminRequest" not in script


def test_demo_ui_uses_text_rendering_for_server_values() -> None:
    script = _inline_script()

    assert ".innerHTML" not in script
    assert "replaceChildren" in script
    assert "textContent" in script
    assert "validator?.validator_result" in script
    assert "integrity.verified === true" in script
    assert "integrity.verified === false" in script


def test_demo_ui_mobile_grids_allow_children_to_shrink() -> None:
    html = _html()

    assert ".grid > *," in html
    assert ".stack > *," in html
    assert "grid-template-columns: minmax(0, 1fr);" in html


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_demo_inline_javascript_has_valid_syntax() -> None:
    result = subprocess.run(
        [shutil.which("node") or "node", "--check", "-"],
        input=_inline_script(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_demo_async_regressions_execute() -> None:
    result = subprocess.run(
        [shutil.which("node") or "node", "--test", str(DEMO_ASYNC_TEST)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
