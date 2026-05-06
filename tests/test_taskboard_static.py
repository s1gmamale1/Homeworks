"""
Static markup smoke tests for the Kanban taskboard page.

These guard the contract between the JS renderer and the HTML shell —
e.g. js/taskboard.js looks up #tb-board, the type/assignee selects, and
the bottom-dock buttons. If a future refactor renames or removes any of
these IDs without updating the JS, this test fails fast.
"""
import re
import pytest


@pytest.fixture(scope="module")
def taskboard_html(client):
    r = client.get("/taskboard.html")
    assert r.status_code == 200
    return r.text


# ── shell + board structure ────────────────────────────────────────────────

def test_board_container_present(taskboard_html):
    assert 'id="tb-board"' in taskboard_html
    assert 'class="tb-board"' in taskboard_html


def test_header_action_buttons_present(taskboard_html):
    assert 'id="tb-new-task"' in taskboard_html
    assert 'id="tb-new-user"' in taskboard_html


# ── extended task modal fields the JS reads ────────────────────────────────

@pytest.mark.parametrize("input_id", [
    "tb-task-title",
    "tb-task-desc",
    "tb-task-type",
    "tb-task-assignee",
    "tb-task-subtotal",
    "tb-task-subdone",
    "tb-task-attach",
    "tb-task-cover",
])
def test_task_modal_inputs_present(taskboard_html, input_id):
    assert f'id="{input_id}"' in taskboard_html


def test_task_type_select_includes_all_types(taskboard_html):
    for value in ("general", "development", "design", "research", "ops"):
        assert f'value="{value}"' in taskboard_html


# ── user modal — color swatches container ──────────────────────────────────

def test_user_modal_has_color_swatches_container(taskboard_html):
    assert 'id="tb-user-color-swatches"' in taskboard_html


# ── bottom dock ────────────────────────────────────────────────────────────

def test_bottom_dock_present_with_four_buttons(taskboard_html):
    assert 'class="tb-bottom-dock' in taskboard_html
    # The four canonical dock entries (Inbox, Planner, Board, Switch boards).
    dock_block = re.search(
        r'<nav[^>]*class="tb-bottom-dock[^"]*"[^>]*>(.*?)</nav>',
        taskboard_html,
        re.DOTALL,
    )
    assert dock_block, "tb-bottom-dock block not found"
    inner = dock_block.group(1)
    matches = re.findall(r'class="tb-dock-btn[^"]*"', inner)
    assert len(matches) == 4, f"expected 4 dock buttons, got {len(matches)}"


def test_dock_includes_switch_boards_button(taskboard_html):
    assert 'id="tb-switch-boards"' in taskboard_html
