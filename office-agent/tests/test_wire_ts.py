import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).parents[1] / "scripts" / "gen_wire_ts.py"


def _generator():
    spec = importlib.util.spec_from_file_location("gen_wire_ts", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_checked_in_wire_types_match_the_generator() -> None:
    generator = _generator()
    checked_in = generator.OUTPUT.read_text(encoding="utf-8")
    assert checked_in == generator.render(), (
        f"{generator.OUTPUT.name} is out of date with conversation/wire.py; "
        f"run `{generator.REGENERATE}` from office-agent/ and commit the result"
    )


def test_every_wire_type_is_generated() -> None:
    from coscribe.conversation import wire

    generated = _generator().render()
    for classes in (*wire.SERVER_EVENTS.values(), *wire.CLIENT_MESSAGES.values()):
        for cls in classes:
            assert f"export interface {cls.__name__} {{" in generated


@pytest.mark.parametrize("annotation", [set, tuple[int, ...]])
def test_a_type_without_a_typescript_form_is_refused(annotation: object) -> None:
    with pytest.raises(TypeError):
        _generator().ts_type(annotation)
