import json
from pathlib import Path

import pytest

import glyph.cli
from glyph import AgentQueryCompleted


@pytest.mark.asyncio
async def test_run_cli_executes_markdown_workflow(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    called_with: list[Path] = []

    async def fake_run_markdown_workflow(path: Path) -> dict[str, str]:
        called_with.append(path)
        return {"file_path": "postcard.txt"}

    monkeypatch.setattr(glyph.cli, "run_markdown_workflow", fake_run_markdown_workflow)

    exit_code = await glyph.cli.run_cli(["workflow.md"])

    assert exit_code == 0
    assert called_with == [Path("workflow.md")]
    assert capsys.readouterr().out.strip() == json.dumps({"file_path": "postcard.txt"})


def test_render_result_handles_scalars_and_none() -> None:
    assert glyph.cli._render_result("hello") == "hello"
    assert glyph.cli._render_result(42) == "42"
    assert glyph.cli._render_result(None) is None


def test_render_result_returns_message_for_agent_query_completed() -> None:
    completed = AgentQueryCompleted(message="done", usage={"input_tokens": 1})
    assert glyph.cli._render_result(completed) == "done"


def test_render_result_agent_query_completed_without_message_is_none() -> None:
    assert glyph.cli._render_result(AgentQueryCompleted(message=None)) is None
