import asyncio
import importlib.util
import inspect
import json
import os
from pathlib import Path
import re
import textwrap
import types
from typing import Any
from typing import Callable

from glyph.messages import AgentQueryCompleted
from glyph.workflows.decorators import step as glyph_step
from glyph.workflows.markdown.models import MarkdownExecuteFunctionStep
from glyph.workflows.markdown.models import MarkdownExecuteInlineStep
from glyph.workflows.markdown.models import MarkdownLLMStep
from glyph.workflows.markdown.models import MarkdownStep
from glyph.workflows.markdown.models import MarkdownWorkflow


def build_step_methods(workflow: MarkdownWorkflow) -> dict[str, Callable[..., Any]]:
    workflow_path = Path(workflow.workflow_path).expanduser().resolve()
    step_methods: dict[str, Callable[..., Any]] = {}

    for index, markdown_step in enumerate(workflow.steps):
        method_name = _method_name(index, markdown_step.step_name)
        step_methods[method_name] = build_step_method(
            step=markdown_step,
            method_name=method_name,
            workflow_path=workflow_path,
        )

    return step_methods


def build_step_method(
    *,
    step: MarkdownStep,
    method_name: str,
    workflow_path: Path,
) -> Callable[..., Any]:
    if isinstance(step, MarkdownLLMStep):
        async def _llm_step(self: Any, step_input: Any = None) -> None:
            self.prompt = _expand_mustache_prompt(step.prompt, step_input)
            return None

        return glyph_step(prompt=step.prompt, model=step.model_override)(
            _name_function(_llm_step, method_name)
        )

    if isinstance(step, (MarkdownExecuteInlineStep, MarkdownExecuteFunctionStep)):
        handler = _load_execute_handler(step, workflow_path)

        async def _execute_step(self: Any, step_input: Any = None) -> Any:
            return await _invoke_execute_handler(handler, step_input)

        return glyph_step(_name_function(_execute_step, method_name))

    raise TypeError(f"Unsupported markdown step type: {type(step).__name__}.")


def _load_execute_handler(
    step: MarkdownExecuteInlineStep | MarkdownExecuteFunctionStep,
    workflow_path: Path,
) -> Callable[..., Any]:
    if isinstance(step, MarkdownExecuteInlineStep):
        if step.language == "bash":
            return _build_bash_handler(
                step_name=step.step_name,
                workflow_path=workflow_path,
                bash_args=["-c", step.source],
                error_label="Inline Bash",
            )

        function_name = _method_name(0, f"inline_{step.step_name}")
        function_source = (
            f"async def {function_name}(step_input=None):\n"
            f"{textwrap.indent(step.source, '    ')}\n"
        )
        namespace = {"__file__": str(workflow_path)}
        exec(compile(function_source, str(workflow_path), "exec"), namespace)
        return namespace[function_name]

    script_path = _resolve_script_path(step.file, workflow_path)
    if script_path.suffix == ".sh":
        return _build_bash_handler(
            step_name=step.step_name,
            workflow_path=workflow_path,
            bash_args=[str(script_path)],
            error_label="Bash script",
        )

    module_name = f"_glyph_markdown_{abs(hash((str(script_path), step.function)))}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {script_path}.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    handler = getattr(module, step.function, None)
    if handler is None:
        raise AttributeError(f"{script_path} does not define {step.function!r}.")
    return handler


def _build_bash_handler(
    *,
    step_name: str,
    workflow_path: Path,
    bash_args: list[str],
    error_label: str,
) -> Callable[..., Any]:
    async def _run_bash(step_input: Any = None) -> dict[str, Any]:
        return await _run_bash_step(
            step_name=step_name,
            workflow_path=workflow_path,
            step_input=step_input,
            bash_args=bash_args,
            error_label=error_label,
        )

    return _run_bash


async def _run_bash_step(
    *,
    step_name: str,
    workflow_path: Path,
    step_input: Any,
    bash_args: list[str],
    error_label: str,
) -> dict[str, Any]:
    process = await asyncio.create_subprocess_exec(
        "/bin/bash",
        *bash_args,
        cwd=str(workflow_path.parent),
        env={
            **os.environ,
            "GLYPH_WORKFLOW_PATH": str(workflow_path),
            "GLYPH_WORKFLOW_DIR": str(workflow_path.parent),
            "GLYPH_STEP_ID": step_name,
            "GLYPH_STEP_INPUT_JSON": _serialize_step_input(step_input),
        },
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    result = {
        "stdout": stdout_bytes.decode("utf-8"),
        "stderr": stderr_bytes.decode("utf-8"),
        "exit_code": process.returncode,
    }
    if process.returncode != 0:
        raise RuntimeError(_format_bash_error(step_name, result, error_label))
    return result


def _resolve_script_path(script: str, workflow_path: Path) -> Path:
    script_path = Path(script)
    if not script_path.is_absolute():
        script_path = (workflow_path.parent / script_path).resolve()

    if script_path.suffix not in {".py", ".sh"}:
        raise ValueError(f"Execute target {script!r} must point to a `.py` or `.sh` file.")
    if not script_path.exists():
        raise ValueError(f"Execute target script {script_path} does not exist.")
    return script_path


async def _invoke_execute_handler(handler: Callable[..., Any], step_input: Any) -> Any:
    parameter_count = len(inspect.signature(handler).parameters)
    if parameter_count == 0:
        result = handler()
    elif parameter_count == 1:
        result = handler(step_input)
    else:
        raise TypeError(
            f"Execute handler {handler.__name__!r} must accept zero or one argument, got {parameter_count}."
        )

    if inspect.isawaitable(result):
        return await result
    return result


def _serialize_step_input(step_input: Any) -> str:
    if isinstance(step_input, AgentQueryCompleted):
        payload = {
            "is_error": step_input.is_error,
            "stop_reason": step_input.stop_reason,
            "message": step_input.message,
            "usage": step_input.usage,
            "total_cost_usd": step_input.total_cost_usd,
            "extra": step_input.extra,
        }
        return json.dumps(payload)
    return json.dumps(step_input, default=str)


def _format_bash_error(step_name: str, result: dict[str, Any], label: str) -> str:
    details = [f"{label} step {step_name!r} failed with exit code {result['exit_code']}."]
    stderr = str(result["stderr"]).strip()
    stdout = str(result["stdout"]).strip()
    if stderr:
        details.append(f"stderr:\n{stderr}")
    elif stdout:
        details.append(f"stdout:\n{stdout}")
    return "\n".join(details)


def _name_function(candidate: Callable[..., Any], method_name: str) -> Callable[..., Any]:
    candidate.__name__ = method_name
    candidate.__qualname__ = method_name
    return candidate


def _expand_mustache_prompt(template: str, step_input: Any) -> str:
    """Replace ``{{ expr }}`` from ``step_input``; leave unknown placeholders unchanged."""

    ctx = _prompt_substitution_context(step_input)

    def _repl(match: re.Match[str]) -> str:
        expr = match.group(1).strip()
        try:
            value = _resolve_prompt_expression(expr, ctx)
        except (KeyError, AttributeError, TypeError):
            return match.group(0)
        return str(value)

    return re.sub(r"\{\{([^{}]+)\}\}", _repl, template)


def _prompt_substitution_context(step_input: Any) -> dict[str, Any]:
    if step_input is None:
        return {}
    if isinstance(step_input, dict):
        return {**step_input, "step_input": types.SimpleNamespace(**step_input)}
    return {"step_input": step_input}


def _resolve_prompt_expression(expr: str, ctx: dict[str, Any]) -> Any:
    head, _, tail = expr.partition(".")
    current: Any = ctx[head]
    for part in filter(None, tail.split(".")):
        current = getattr(current, part)
    return current


def _method_name(index: int, step_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", step_name).strip("_") or "step"
    if normalized[0].isdigit():
        normalized = f"step_{normalized}"
    return f"_markdown_step_{index}_{normalized}"
