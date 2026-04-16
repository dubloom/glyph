import asyncio
import os

from agnos import AgentOptions
from agnos import AgentQueryCompleted
from agnos import AgentText
from agnos import AgnosClient


async def main() -> None:
    options = AgentOptions(model=os.getenv("AGNOS_MODEL", "gpt-4.1-mini"))

    async with AgnosClient(options) as client:
        await client.query("Give a short definition of technical debt.")
        async for event in client.receive_response():
            if isinstance(event, AgentText):
                print(event.text, end="")
            elif isinstance(event, AgentQueryCompleted):
                print("\n\nTurn completed:", not event.is_error)


if __name__ == "__main__":
    asyncio.run(main())
