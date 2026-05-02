from pathlib import Path

import pytest

from glyph import AgentQueryCompleted
import glyph.workflows as workflows_module
from glyph.workflows.markdown import load_markdown_workflow
from glyph.workflows.markdown import parse_markdown_workflow
from glyph.workflows.markdown.models import MarkdownExecuteFunctionStep
from glyph.workflows.markdown.models import MarkdownExecuteInlineStep
from glyph.workflows.markdown.models import MarkdownLLMStep
from glyph.workflows.markdown.models import MarkdownStepKind


def test_parse_markdown_workflow_accepts_mapping_returns(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: writePostcard
---

## Step: loadTripContext
execute:
  file: handlers.py
  function: load_trip_context
returns:
  city: str
  mood: str
  memory: str
""",
        encoding="utf-8",
    )

    definition = parse_markdown_workflow(workflow_path)

    assert definition.steps[0].step_name == "loadTripContext"
    assert len(definition.steps) == 1
    step0 = definition.steps[0]
    assert isinstance(step0, MarkdownExecuteFunctionStep)
    assert step0.file == "handlers.py"
    assert step0.function == "load_trip_context"


def test_parse_markdown_workflow_execute_file_defaults_to_main(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: savePostcard
---

## Step: savePostcard
execute:
  file: handlers.py
returns:
  file_path: str
""",
        encoding="utf-8",
    )

    definition = parse_markdown_workflow(workflow_path)

    assert len(definition.steps) == 1
    step0 = definition.steps[0]
    assert isinstance(step0, MarkdownExecuteFunctionStep)
    assert step0.file == "handlers.py"
    assert step0.function == "main"


def test_parse_markdown_workflow_allows_blank_line_between_step_metadata_keys(tmp_path: Path) -> None:
    """Blank lines between `execute:` and `returns:` must not turn `returns` into prompt text."""

    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: savePostcard
---

## Step: savePostcard

execute:
  file: handlers.py

returns:
  file_path: str
""",
        encoding="utf-8",
    )

    definition = parse_markdown_workflow(workflow_path)

    assert len(definition.steps) == 1
    assert definition.steps[0].kind is MarkdownStepKind.EXECUTE


def test_parse_markdown_workflow_treats_key_value_prompt_lines_as_prompt(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: writePostcard
---

## Step: draftPostcard
Subject: Lisbon postcard
Tone: warm
Keep it to 3 sentences maximum.
""",
        encoding="utf-8",
    )

    definition = parse_markdown_workflow(workflow_path)

    assert len(definition.steps) == 1
    step0 = definition.steps[0]
    assert isinstance(step0, MarkdownLLMStep)
    assert step0.kind is MarkdownStepKind.LLM
    assert step0.prompt == (
        "Subject: Lisbon postcard\n"
        "Tone: warm\n"
        "Keep it to 3 sentences maximum."
    )


def test_parse_markdown_workflow_uses_first_step_as_entrypoint(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: writePostcard
---

## Step: loadTripContext
execute:
  file: handlers.py
  function: load_trip_context

## Step: draftPostcard
Write a warm postcard from Lisbon in 3 sentences max.
""",
        encoding="utf-8",
    )

    definition = parse_markdown_workflow(workflow_path)

    assert definition.steps[0].step_name == "loadTripContext"


def test_parse_markdown_workflow_accepts_inline_python_without_execute_key(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: writePostcard
---

## Step: loadTripContext

```python
return {
  "city": "Lisbon",
  "mood": "warm and nostalgic",
}
```

returns:
  city: str
  mood: str
""",
        encoding="utf-8",
    )

    definition = parse_markdown_workflow(workflow_path)

    assert len(definition.steps) == 1
    step0 = definition.steps[0]
    assert isinstance(step0, MarkdownExecuteInlineStep)
    assert step0.kind is MarkdownStepKind.EXECUTE
    assert step0.language == "python"
    assert step0.source == 'return {\n  "city": "Lisbon",\n  "mood": "warm and nostalgic",\n}\n'


def test_parse_markdown_workflow_accepts_inline_bash_without_execute_key(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: inspectWorkspace
---

## Step: inspectWorkspace

```bash
printf 'hello from bash'
```

returns:
  stdout: str
  stderr: str
  exit_code: int
""",
        encoding="utf-8",
    )

    definition = parse_markdown_workflow(workflow_path)

    assert len(definition.steps) == 1
    step0 = definition.steps[0]
    assert isinstance(step0, MarkdownExecuteInlineStep)
    assert step0.kind is MarkdownStepKind.EXECUTE
    assert step0.language == "bash"
    assert step0.source == "printf 'hello from bash'\n"


def test_parse_markdown_workflow_treats_prompt_with_fenced_code_as_prompt(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: explainCode
---

## Step: explainCode
Explain this code:
```python
print("hello")
```
""",
        encoding="utf-8",
    )

    definition = parse_markdown_workflow(workflow_path)

    assert len(definition.steps) == 1
    step0 = definition.steps[0]
    assert isinstance(step0, MarkdownLLMStep)
    assert step0.prompt == 'Explain this code:\n```python\nprint("hello")\n```'


@pytest.mark.asyncio
async def test_load_markdown_workflow_runs_inline_python_steps(tmp_path: Path) -> None:
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: writePostcard
---

## Step: loadTripContext

```python
return {
  "city": "Lisbon",
}
```

returns:
  city: str

## Step: savePostcard

```python
from pathlib import Path

output_path = Path(__file__).with_name("postcard.txt")
output_path.write_text(step_input["city"], encoding="utf-8")
return {"file_path": str(output_path)}
```

returns:
  file_path: str
""",
        encoding="utf-8",
    )

    workflow_cls = load_markdown_workflow(workflow_path)
    result = await workflow_cls.run()

    assert result["file_path"] == str(tmp_path / "postcard.txt")
    assert (tmp_path / "postcard.txt").read_text(encoding="utf-8") == "Lisbon"


@pytest.mark.asyncio
async def test_load_markdown_workflow_runs_inline_bash_steps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: inspectWorkspace
options:
  model: gpt-4.1-mini
---

## Step: inspectWorkspace

```bash
printf 'stdout=%s' "$GLYPH_WORKFLOW_DIR"
```

returns:
  stdout: str
  stderr: str
  exit_code: int

## Step: summarize
Output: {{ stdout }}
Exit code: {{ exit_code }}
""",
        encoding="utf-8",
    )

    fake_client = _FakeMarkdownClient()
    monkeypatch.setattr(workflows_module, "GlyphClient", lambda options: fake_client)

    workflow_cls = load_markdown_workflow(workflow_path)
    result = await workflow_cls.run(session_id="markdown-bash")

    assert fake_client.prompts == [
        (f"Output: stdout={tmp_path}\nExit code: 0", "markdown-bash"),
    ]
    assert isinstance(result, AgentQueryCompleted)
    assert result.message == f"Output: stdout={tmp_path}\nExit code: 0"


@pytest.mark.asyncio
async def test_load_markdown_workflow_runs_bash_file_step(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "probe.sh").write_text(
        """#!/usr/bin/env bash
printf 'dir=%s' "$GLYPH_WORKFLOW_DIR"
""",
        encoding="utf-8",
    )
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: probeDir
options:
  model: gpt-4.1-mini
---

## Step: probeDir
execute:
  file: probe.sh
returns:
  stdout: str
  stderr: str
  exit_code: int

## Step: summarize
Output: {{ stdout }}
""",
        encoding="utf-8",
    )

    fake_client = _FakeMarkdownClient()
    monkeypatch.setattr(workflows_module, "GlyphClient", lambda options: fake_client)

    workflow_cls = load_markdown_workflow(workflow_path)
    result = await workflow_cls.run(session_id="markdown-bash-file")

    assert fake_client.prompts == [(f"Output: dir={tmp_path}", "markdown-bash-file")]
    assert isinstance(result, AgentQueryCompleted)
    assert result.message == f"Output: dir={tmp_path}"


class _FakeMarkdownClient:
    def __init__(self) -> None:
        self.prompts: list[tuple[str, str]] = []

    async def __aenter__(self) -> "_FakeMarkdownClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def query_and_receive_response(self, prompt: str, session_id: str = "default") -> list[object]:
        self.prompts.append((prompt, session_id))
        return [AgentQueryCompleted(message=prompt)]


@pytest.mark.asyncio
async def test_load_markdown_workflow_injects_initial_input_into_first_llm_step(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: askCommand
options:
  model: gpt-4.1-mini
---

## Step: draftCommand
Flat: {{ query }}
Nested: {{ step_input.query }}
Missing: {{ missing }}
""",
        encoding="utf-8",
    )

    fake_client = _FakeMarkdownClient()
    monkeypatch.setattr(workflows_module, "GlyphClient", lambda options: fake_client)

    workflow_cls = load_markdown_workflow(workflow_path)
    result = await workflow_cls.run(initial_input={"query": "git status"}, session_id="markdown-test")

    assert fake_client.prompts == [
        ("Flat: git status\nNested: git status\nMissing: {{ missing }}", "markdown-test")
    ]
    assert isinstance(result, AgentQueryCompleted)
    assert result.message == "Flat: git status\nNested: git status\nMissing: {{ missing }}"


@pytest.mark.asyncio
async def test_load_markdown_workflow_exposes_scalar_initial_input_as_step_input(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workflow_path = tmp_path / "workflow.md"
    workflow_path.write_text(
        """---
name: askCommand
options:
  model: gpt-4.1-mini
---

## Step: draftCommand
Prompt: {{ step_input }}
""",
        encoding="utf-8",
    )

    fake_client = _FakeMarkdownClient()
    monkeypatch.setattr(workflows_module, "GlyphClient", lambda options: fake_client)

    workflow_cls = load_markdown_workflow(workflow_path)
    result = await workflow_cls.run(initial_input="git status", session_id="markdown-scalar")

    assert fake_client.prompts == [("Prompt: git status", "markdown-scalar")]
    assert isinstance(result, AgentQueryCompleted)
    assert result.message == "Prompt: git status"
