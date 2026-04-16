import asyncio
import os

from agnos import AgentOptions
from agnos import AgentQueryCompleted
from agnos import AgentText
from agnos import AgnosClient


async def main() -> None:
    options = AgentOptions(model=os.getenv("AGNOS_MODEL", "gpt-4.1-mini"))

    async with AgnosClient(options) as client:
        events = await client.query_and_receive_response(
            "Name one advantage and one drawback of microservices."
        )

    for event in events:
        if isinstance(event, AgentText):
            print(event.text, end="")
        elif isinstance(event, AgentQueryCompleted):
            print("\n\nusage:", event.usage)
            print("total_cost_usd:", event.total_cost_usd)


if __name__ == "__main__":
    asyncio.run(main())
