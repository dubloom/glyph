"""Markdown workflow loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from glyph.options import AgentOptions
from glyph.workflows.markdown.models import MarkdownWorkflow
from glyph.workflows.markdown.parser import parse_markdown_workflow
from glyph.workflows.markdown.step_builder import build_step_methods


def load_markdown_workflow(path: str | Path) -> type:
    """Build a ``GlyphWorkflow`` subclass from ``path``."""

    from glyph.workflows import GlyphWorkflow

    workflow_path = Path(path).expanduser().resolve()
    workflow: MarkdownWorkflow = parse_markdown_workflow(workflow_path)
    step_methods = build_step_methods(workflow)

    workflow_cls = type(
        "MarkdownGlyphWorkflow",
        (GlyphWorkflow,),
        {
            "__module__": GlyphWorkflow.__module__,
            "__doc__": f"Markdown workflow loaded from {workflow_path}.",
            "options": workflow.parameters.options,
            "_glyph_markdown_path": str(workflow_path),
            **step_methods,
        },
    )
    setattr(workflow_cls, "_glyph_markdown_definition", workflow)
    return workflow_cls


async def run_markdown_workflow(
    path: str | Path,
    *,
    options: AgentOptions | None = None,
    session_id: str | None = None,
    initial_input: Any = None,
) -> Any:
    """Load and run a workflow defined in Markdown."""

    workflow_cls = load_markdown_workflow(path)
    return await workflow_cls.run(
        options=options,
        session_id=session_id,
        initial_input=initial_input,
    )


__all__ = [
    "load_markdown_workflow",
    "run_markdown_workflow",
]
