from pathlib import Path
import re
from typing import Any
from typing import Literal
from typing import cast

import yaml

from glyph import AgentOptions
from glyph.workflows.markdown.models import MarkdownExecuteFunctionStep
from glyph.workflows.markdown.models import MarkdownExecuteInlineStep
from glyph.workflows.markdown.models import MarkdownLLMStep
from glyph.workflows.markdown.models import MarkdownParameters
from glyph.workflows.markdown.models import MarkdownStep
from glyph.workflows.markdown.models import MarkdownWorkflow


GLYPH_WORKFLOW_KEYS = frozenset({"execute", "model", "returns"})
SUPPORTED_LANGUAGES = frozenset({"bash", "python"})


def _match_inline_execute_block(step_text: str) -> re.Match[str] | None:
    return re.match(
        r'(?s)^\s*(?:(?:execute|model|returns):.*?\n)*\s*```(\w+)\n(.*?)```\s*(?:(?:execute|model|returns):.*?\n|\s)*$',
        step_text,
    )

def parse_workflow_parameters(raw_parameters: str) -> MarkdownParameters:
    """Parse YAML front matter into workflow name, description, and agent options."""
    try:
        parameters = yaml.safe_load(raw_parameters)
    except yaml.YAMLError as e:
        print("Failed to parse workflow parameters, expect YAML format:", e)
        raise

    return MarkdownParameters(
        parameters["name"] if "name" in parameters else None,
        parameters["description"] if "description" in parameters else None,
        AgentOptions(**parameters["options"]) if "options" in parameters else None,
    )

def parse_workflow_steps(raw_workflow_body: str) -> list[MarkdownStep]:
    """Parse `## Step:` sections into inline code, execute-file, or LLM steps."""
    raw_steps = re.findall(
        r'(?ims)^#+\s*step\s*:\s*(.+?)\s*$\n(.*?)(?=^#+\s*step\s*:|\Z)',
        raw_workflow_body,
    )

    steps: list[Any] = []
    for step_name, step_text in raw_steps:
        step_language: Literal["python", "bash"]
        inline_source: str

        check_inline_code = _match_inline_execute_block(step_text)
        if check_inline_code:
            step_language = check_inline_code.group(1) or ""
            if step_language not in SUPPORTED_LANGUAGES:
                raise RuntimeError(
                    f"{step_language} is not supported in GlyphWorkflow, "
                    f"supported languages: {SUPPORTED_LANGUAGES}"
                )

            inline_source = check_inline_code.group(2)

            steps.append(MarkdownExecuteInlineStep(
                step_name=step_name,
                language=step_language,
                source=inline_source
            ))
        # It is a code step as well but the user is providing a script
        elif cast(str,step_text).startswith("execute:"):
            step_body = yaml.safe_load(step_text)
            file = str(step_body["execute"]["file"])
            function = step_body["execute"]["function"].strip() if "function" in step_body["execute"] else "main"

            if not (file.endswith(".py") or file.endswith(".sh")):
                raise RuntimeError("Only bash and python files are supported for now")

            steps.append(MarkdownExecuteFunctionStep(
                step_name=step_name,
                file=file,
                function=function
            ))
        else:
            # This case means we are in an LLM step and text should be interpreted
            # as a prompt
            extract_prompt_model_re = re.search(r'(?im)^\s*model:\s*(.+?)\s*$', step_text)
            model = extract_prompt_model_re.group(1) if extract_prompt_model_re else None

            prompt = re.sub(
                r'(?ims)^\s*model:\s*.*?$[\r\n]*|^\s*returns?:\s*\n(?:[ \t]+.*(?:\n|$))*',
                '',
                step_text,
            ).strip()

            if not prompt:
                raise RuntimeError(f"LLM step must have a prompt, instead received: {prompt}")

            steps.append(MarkdownLLMStep(
                step_name=step_name,
                prompt=prompt,
                model_override=model,
            ))

    return steps


def parse_markdown_workflow(workflow_path: Path) -> Any:
    """Load a markdown workflow file and return parameters plus parsed steps."""
    raw_markdown = workflow_path.read_text(encoding="utf-8")

    # Get workflow parameters and the workflow body
    splitter_pattern = re.compile(r'^(-{3,})\n(.*?)\n\1\n(.*)$', re.DOTALL)
    match = splitter_pattern.match(raw_markdown)
    if not match:
        raise ValueError("Invalid worfklow format")

    raw_parameters = match.group(2)
    raw_worfklow_body = match.group(3)

    # Remove the comments
    raw_worfklow_body = re.compile(r"<!--.*?-->", re.DOTALL).sub("", raw_worfklow_body)

    parameters: MarkdownParameters = parse_workflow_parameters(raw_parameters)
    steps: list[MarkdownStep] = parse_workflow_steps(raw_worfklow_body)
    if not steps:
        raise ValueError(f"{workflow_path} must declare at least one `## Step: ...` section.")

    return MarkdownWorkflow(
        workflow_path=workflow_path,
        parameters=parameters,
        steps=steps,
    )
