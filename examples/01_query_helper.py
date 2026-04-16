import asyncio
import os

from agnos import AgentOptions
from agnos import AgentQueryCompleted
from agnos import AgentText
from agnos import query


async def main() -> None:
    options = AgentOptions(
        model=os.getenv("AGNOS_MODEL", "gpt-4.1-mini"),
        instructions="You are concise and accurate.",
    )
    async for event in query(
        prompt="In one sentence, explain what an API is.",
        options=options,
    ):
        if isinstance(event, AgentText):
            print(event.text, end="")
        elif isinstance(event, AgentQueryCompleted):
            print("\n\nis_error:", event.is_error)
            print("usage:", event.usage)
            print("total_cost_usd:", event.total_cost_usd)


if __name__ == "__main__":
    asyncio.run(main())
