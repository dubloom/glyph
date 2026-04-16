import asyncio
import os

from agnos import AgentOptions
from agnos import AgentText
from agnos import AgnosClient


async def ask(client: AgnosClient, session_id: str, prompt: str) -> None:
    print(f"\n[{session_id}] user:", prompt)
    async for event in client.query_streamed(prompt, session_id=session_id):
        if isinstance(event, AgentText):
            print(event.text, end="")
    print()


async def main() -> None:
    options = AgentOptions(model=os.getenv("AGNOS_MODEL", "gpt-4.1-mini"))

    async with AgnosClient(options) as client:
        await ask(client, "session-a", "Remember my favorite language is Python.")
        await ask(client, "session-a", "What is my favorite language?")

        await ask(client, "session-b", "What is my favorite language?")
        await ask(client, "session-b", "Remember my favorite language is Rust.")
        await ask(client, "session-b", "What is my favorite language now?")


if __name__ == "__main__":
    asyncio.run(main())
