# ruff: noqa: E402
"""Web tests: the Files panel's routes list, search and serve a conversation's folders."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from coscribe.web.routes.workspace import find_files, list_folder

from .helpers import FakeToolCallingChatModel, _client_lg


def _tree(root: Path) -> None:
    (root / "docs" / "notes").mkdir(parents=True)
    (root / "docs" / "notes" / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (root / "Readme.md").write_text("hi", encoding="utf-8")
    (root / "app.py").write_text("print(1)\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / "node_modules" / "plan").mkdir(parents=True)
    (root / "~$report.docx").write_text("lock", encoding="utf-8")


def test_a_listing_puts_folders_first_hides_git_and_lock_files_and_greys_heavy_folders(
    tmp_path: Path,
) -> None:
    _tree(tmp_path)
    entries = list_folder(tmp_path)["entries"]

    assert [e["name"] for e in entries] == ["docs", "node_modules", "app.py", "Readme.md"]
    assert entries[1].get("dim") is True and "dim" not in entries[0]
    assert entries[2]["size"] == len("print(1)\n") and entries[0]["size"] is None


def test_a_search_finds_names_at_any_depth_but_not_inside_heavy_folders(tmp_path: Path) -> None:
    _tree(tmp_path)
    found = find_files(tmp_path, "PLAN")["entries"]

    assert [e["path"] for e in found] == ["docs/notes/plan.md"]


def test_the_routes_serve_the_conversations_folder_and_nothing_outside_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        workspace = tmp_path / "workspace"
        _tree(workspace)
        (workspace / "page.html").write_text("<p>x</p><script>1</script>", encoding="utf-8")
        (tmp_path / "secret.txt").write_text("no", encoding="utf-8")
        base = "/api/threads/t_files/workspace"

        roots = client.get(base).json()["roots"]
        top = client.get(f"{base}/0/list").json()["entries"]
        inner = client.get(f"{base}/0/list", params={"path": "docs/notes"}).json()["entries"]
        found = client.get(f"{base}/0/search", params={"q": "plan"}).json()["entries"]
        page = client.get(f"{base}/0/raw/page.html")
        outside = client.get(f"{base}/0/list", params={"path": ".."})
        escaped = client.get(f"{base}/0/raw/..%2Fsecret.txt")
        no_root = client.get(f"{base}/3/list")

    assert roots == [{"name": "workspace", "path": str(workspace.resolve())}]
    assert "docs" in [e["name"] for e in top]
    assert [e["name"] for e in inner] == ["plan.md"]
    assert [e["path"] for e in found] == ["docs/notes/plan.md"]
    assert page.status_code == 200 and page.text.startswith("<p>x</p>")
    # Shown, never run: no script, also when the file is opened in a tab of its own.
    assert "script-src 'none'" in page.headers["content-security-policy"]
    assert "attachment" not in page.headers.get("content-disposition", "")
    assert outside.status_code == 404 and escaped.status_code == 404
    assert no_root.status_code == 404
