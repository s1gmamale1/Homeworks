"""
Regression guard: every <script src="/js/..."> tag on every dashboard
page must point at a file that actually exists in frontend/js/.

Background: frontend/builder.html shipped a <script> tag for
/js/editors/grading.js that never had a matching file (PR #17 -> PR
[this one]). Browsers silently 404'd on every page load.

This test fences against the same footgun. Pattern mirrors PR #35's
test_no_internal_script_or_link_tag_skips_cache_bust — strict guard,
parametrized over surfaces.
"""
import re
from pathlib import Path
import pytest

_SCRIPT_SRC_RE = re.compile(
    r'''<script[^>]+src=["'](/js/[^"'?]+)(?:\?[^"']*)?["']''',
    re.IGNORECASE,
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@pytest.mark.parametrize("path", ["/", "/builder.html", "/library.html"])
def test_no_dead_script_tags(client, path):
    """Every <script src="/js/..."> tag must resolve to an existing file."""
    r = client.get(path)
    assert r.status_code == 200
    srcs = _SCRIPT_SRC_RE.findall(r.text)
    assert srcs, f"no <script src='/js/...'> tags found on {path}"
    for src in srcs:
        # Strip leading /js/ to make a filesystem path
        # /js/editors/foo.js -> editors/foo.js
        rel = src.lstrip("/").removeprefix("js/")
        target = FRONTEND_DIR / "js" / rel
        assert target.is_file(), (
            f"DEAD SCRIPT TAG on {path}: <script src='{src}'> "
            f"resolves to {target} which does not exist. "
            f"Either add the file or remove the tag."
        )
