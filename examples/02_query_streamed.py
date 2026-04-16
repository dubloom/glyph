import asyncio
import os

from agnos import AgentOptions
from agnos import AgentQueryCompleted
from agnos import AgentText
from agnos import AgentThinking
from agnos import AgentToolCall
from agnos import AgentToolResult
from agnos import AgnosClient


async def main() -> None:
    options = AgentOptions(
        model=os.getenv("AGNOS_MODEL", "gpt-4.1-mini"),
        instructions="You are helpful and brief.",
    )

    async with AgnosClient(options) as client:
        async for event in client.query_streamed("List two benefits of unit tests."):
            if isinstance(event, AgentThinking):
                print("[thinking]", event.text)
            elif isinstance(event, AgentText):
                print(event.text, end="")
            elif isinstance(event, AgentToolCall):
                print(f"\n[tool call] name={event.name} call_id={event.call_id}")
            elif isinstance(event, AgentToolResult):
                print(f"\n[tool result] call_id={event.call_id} status={event.status}")
            elif isinstance(event, AgentQueryCompleted):
                print("\n\n[completed]")
                print("stop_reason:", event.stop_reason)
                print("usage:", event.usage)
                print("extra:", event.extra)


if __name__ == "__main__":
    asyncio.run(main())
