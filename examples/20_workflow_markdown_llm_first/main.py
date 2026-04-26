import asyncio
from pathlib import Path

from glyph import run_markdown_workflow


async def main() -> None:
    workflow_path = Path(__file__).with_name("workflow.md")
    result = await run_markdown_workflow(
        workflow_path,
        initial_input={
            "topic": "a CLI that turns Markdown into Glyph workflows",
            "tone": "confident and friendly",
        },
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
