import asyncio
import os

from agnos import AgentOptions
from agnos import AgentQueryCompleted
from agnos import AgentText
from agnos import AgnosClient


async def main() -> None:
    options = AgentOptions(
        model=os.getenv("AGNOS_MODEL", "gpt-5.4-mini"),
        reasoning_effort="low",
        reasoning_summary="summary",
        instructions="Answer in at most three bullet points.",
    )

    async with AgnosClient(options) as client:
        async for event in client.query_streamed(
            "How can I reduce Python cold-start time in serverless apps?"
        ):
            if isinstance(event, AgentText):
                print(event.text, end="")
            elif isinstance(event, AgentQueryCompleted):
                print("\n\nusage:", event.usage)


if __name__ == "__main__":
    asyncio.run(main())
