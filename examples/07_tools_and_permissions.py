import asyncio
import os
from pathlib import Path

from agnos import AgentOptions
from agnos import AgentQueryCompleted
from agnos import AgentText
from agnos import AgnosClient
from agnos import PermissionPolicy


async def main() -> None:
    demo_file = Path("examples/tools_permission_demo.txt")
    options = AgentOptions(
        model=os.getenv("AGNOS_MODEL", "gpt-5.4-mini"),
        cwd=Path.cwd(),
        allowed_tools=("Read", "Glob", "Bash", "Grep", "Write", "Edit"),
        # disallowed_tools=("Bash",),
        permission=PermissionPolicy(mode="ask", edit="ask", execute="deny"),
    )

    prompt = (
        f"Use Write to create `{demo_file}` with one line: "
        "'created by agnos tools example'. Then use Edit to append a second line: "
        "'edit step succeeded'. Finally execute a bash command"
    )
    async with AgnosClient(options) as client:
        async for event in client.query_streamed(prompt):
            if isinstance(event, AgentText):
                print(event.text, end="")
            elif isinstance(event, AgentQueryCompleted):
                print("\n\nis_error:", event.is_error)
                print("stop_reason:", event.stop_reason)


if __name__ == "__main__":
    asyncio.run(main())
