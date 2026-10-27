import pytest

from coscribe.tools.exec import child_env
from coscribe.tools.exec import script_env as script_env_module


def test_only_listed_names_pass_and_keys_do_not() -> None:
    server = {
        "PATH": "/usr/bin",
        "HOME": "/home/a",
        "LC_ALL": "C.UTF-8",
        "ANTHROPIC_API_KEY": "sk-ant",
        "OPENAI_API_KEY": "sk-openai",
        "GEMINI_API_KEY": "g",
        "COSCRIBE_LAUNCH_TOKEN": "t",
        "PYTHONPATH": "/srv/coscribe/src",
    }

    assert child_env(base=server) == {"PATH": "/usr/bin", "HOME": "/home/a", "LC_ALL": "C.UTF-8"}


def test_windows_names_pass_whatever_their_case() -> None:
    server = {"SystemRoot": r"C:\Windows", "COMSPEC": r"C:\Windows\system32\cmd.exe"}

    assert child_env(base=server) == server


@pytest.mark.parametrize(
    ("proxy", "passed"),
    [
        ("http://alice:hunter2@proxy.example:8080", "http://proxy.example:8080"),
        ("http://alice@proxy.example:8080/", "http://proxy.example:8080/"),
        ("alice:hunter2@proxy.example:8080", "proxy.example:8080"),
        ("http://alice:pa/ss@word@proxy.example:8080", "http://proxy.example:8080"),
        ("http://proxy.example:8080", "http://proxy.example:8080"),
    ],
)
def test_a_proxy_passes_without_its_user_name_and_password(proxy: str, passed: str) -> None:
    server = {"HTTPS_PROXY": proxy, "http_proxy": proxy, "NO_PROXY": "localhost,127.0.0.1"}

    assert child_env(base=server) == {
        "HTTPS_PROXY": passed,
        "http_proxy": passed,
        "NO_PROXY": "localhost,127.0.0.1",
    }


def test_the_conversations_variables_come_last_and_may_name_anything() -> None:
    server = {"PATH": "/usr/bin", "OPENAI_API_KEY": "server's"}

    env = child_env({"OPENAI_API_KEY": "the person's own", "REGION": "north"}, base=server)

    assert env == {"PATH": "/usr/bin", "OPENAI_API_KEY": "the person's own", "REGION": "north"}


def test_a_variable_replaces_a_listed_name_differing_only_in_case_on_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(script_env_module.os, "name", "nt")

    assert child_env({"Path": "/mine"}, base={"PATH": "/bin"}) == {"PATH": "/mine"}


def test_reads_the_servers_environment_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.setenv("PATH", "/usr/bin")

    env = child_env()

    assert "ANTHROPIC_API_KEY" not in env and env["PATH"] == "/usr/bin"
