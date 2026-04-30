from pathlib import Path
import re

from server.app import SECURITY_HEADERS


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_viewport_allows_mobile_zoom():
    template = (ROOT / "server/template/perfect_homework.html").read_text(encoding="utf-8")
    match = re.search(
        r'<meta\s+name=["\']viewport["\']\s+content=["\']([^"\']+)["\']',
        template,
        flags=re.IGNORECASE,
    )

    assert match, "viewport meta tag missing from runtime template"
    content = match.group(1).lower()
    assert "width=device-width" in content
    assert "maximum-scale" not in content
    assert "minimum-scale" not in content
    assert "user-scalable=no" not in content


def test_security_headers_on_dashboard_api_and_runtime(client, sample_homework):
    paths = [
        "/",
        "/library.html",
        "/builder.html",
        "/api/homeworks?limit=1",
        f"/api/homeworks/{sample_homework['id']}/preview",
        f"/h/{sample_homework['id']}",
    ]

    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, path
        for header, expected in SECURITY_HEADERS.items():
            assert response.headers.get(header) == expected, f"{path} missing {header}"


def test_content_security_policy_keeps_required_runtime_sources():
    csp = SECURITY_HEADERS["Content-Security-Policy"]

    assert "default-src 'self'" in csp
    assert "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net" in csp
    assert "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net" in csp
    assert "img-src 'self' data: blob: http: https:" in csp
    assert "font-src 'self' data: https://cdn.jsdelivr.net" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'self'" in csp
    assert SECURITY_HEADERS["X-Frame-Options"] == "SAMEORIGIN"


def test_csp_frame_ancestors_allows_same_origin():
    """Builder preview iframe ships from the same origin; CSP must allow self.

    Regression for the PR #73 → PR #76 case where 'none' blocked
    the builder's /api/homeworks/{id}/preview iframe.
    """
    csp = SECURITY_HEADERS["Content-Security-Policy"]
    assert "frame-ancestors 'self'" in csp, (
        f"frame-ancestors should be 'self' (was: {csp!r})"
    )
    assert "frame-ancestors 'none'" not in csp, (
        f"frame-ancestors must not be 'none' (regression of PR #73)"
    )


def test_e2e_scripts_use_shared_chrome_launcher():
    e2e_dir = ROOT / "scripts/e2e"
    scripts = sorted(
        path for path in e2e_dir.glob("*.cjs")
        if path.name != "puppeteer_launcher.cjs"
    )

    assert scripts, "no e2e scripts found"
    for script in scripts:
        source = script.read_text(encoding="utf-8")
        assert "require('./puppeteer_launcher.cjs')" in source, script.name
        assert "launchOptions(" in source, script.name
        assert "puppeteer.launch({" not in source, script.name
