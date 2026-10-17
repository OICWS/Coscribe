"""The file tools cannot write coscribe's own settings, policies and state, even when the user's
workspace contains them (decision 0002: approval is the gate for scripts, but Accept Edits
writes files without asking, so a policy file the model could reach would be changed unasked)."""

from __future__ import annotations

from pathlib import Path

import pytest

from coscribe.config import Settings
from coscribe.tools.files import build_file_tools


def _tools(workspace: Path, settings: Settings) -> dict[str, object]:
    tools = build_file_tools(workspace, protected=settings.protected_paths())
    return {tool.__name__: tool for tool in tools}


def _settings(workspace: Path) -> Settings:
    return Settings(
        default_model="openai:gpt-test",
        workspace_root=workspace,
        state_dir=workspace / "state",
        memory_path=workspace / "MEMORY.md",
        exec_policy_path=workspace / "exec_policy.json",
        hooks_config_path=workspace / "hooks.json",
        mcp_config_path=workspace / "mcp.json",
        providers_config_path=workspace / "providers.json",
        _env_file=None,
    )


@pytest.mark.parametrize(
    "target",
    ["exec_policy.json", "hooks.json", "mcp.json", "providers.json", "MEMORY.md", "state/x.json"],
)
def test_the_file_tools_refuse_to_write_a_settings_file_inside_the_workspace(
    tmp_path: Path, target: str
) -> None:
    tools = _tools(tmp_path, _settings(tmp_path))
    (tmp_path / "state").mkdir()

    with pytest.raises(PermissionError, match="settings"):
        tools["write_file"](path=target, content="{}")  # type: ignore[operator]

    assert not (tmp_path / target).exists()


def test_the_dotenv_in_the_working_directory_is_protected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    tools = _tools(tmp_path, _settings(tmp_path / "ws"))
    tools_ws = _tools(tmp_path, _settings(tmp_path))

    with pytest.raises(PermissionError, match="settings"):
        tools["write_file"](path=".env", content="X=1")  # type: ignore[operator]
    tools_ws["write_file"](path="notes.txt", content="hi")  # type: ignore[operator]

    assert not (tmp_path / ".env").exists()
    assert (tmp_path / "notes.txt").is_file()


def test_a_symlink_to_a_settings_file_does_not_get_around_it(tmp_path: Path) -> None:
    policy = tmp_path / "outside" / "exec_policy.json"
    policy.parent.mkdir()
    policy.write_text("{}", encoding="utf-8")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    link = workspace / "innocent.json"
    try:
        link.symlink_to(policy)
    except OSError:
        pytest.skip("symlinks need a privilege on this machine")
    settings = _settings(tmp_path / "unused")
    settings = settings.model_copy(update={"exec_policy_path": policy})
    tools = _tools(workspace, settings)

    with pytest.raises(PermissionError, match="settings"):
        tools["write_file"](path="innocent.json", content='{"rules": []}')  # type: ignore[operator]

    assert policy.read_text(encoding="utf-8") == "{}"


def test_ordinary_files_in_the_same_workspace_are_still_written(tmp_path: Path) -> None:
    tools = _tools(tmp_path, _settings(tmp_path))

    tools["write_file"](path="notes/todo.txt", content="buy milk")  # type: ignore[operator]

    assert (tmp_path / "notes" / "todo.txt").read_text(encoding="utf-8") == "buy milk"
