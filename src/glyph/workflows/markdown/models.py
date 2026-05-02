from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Literal

from glyph import AgentOptions


class MarkdownStepKind(Enum):
    EXECUTE = "execute"
    LLM = "llm"

ExecuteLanguage = Literal["python", "bash"]

@dataclass
class MarkdownParameters:
    name: str | None
    description: str | None
    options: AgentOptions | None

@dataclass
class MarkdownStep:
    step_name: str
    kind: MarkdownStepKind

@dataclass
class MarkdownExecuteInlineStep(MarkdownStep):
    kind: MarkdownStepKind = field(init=False, default=MarkdownStepKind.EXECUTE)
    language: ExecuteLanguage
    source: str

@dataclass
class MarkdownExecuteFunctionStep(MarkdownStep):
    kind: MarkdownStepKind = field(init=False, default=MarkdownStepKind.EXECUTE)
    file: str
    function: str

@dataclass
class MarkdownLLMStep(MarkdownStep):
    kind: MarkdownStepKind = field(init=False, default=MarkdownStepKind.LLM)
    prompt: str
    model_override: str | None = None

@dataclass
class MarkdownWorkflow:
    workflow_path: Path
    parameters: MarkdownParameters
    steps: list[MarkdownStep]
