from __future__ import annotations
import asyncio

from agnos import AgentOptions, AgentText, AgentThinking, AgentQueryCompleted, Client, resolve_backend



async def main() -> None:
    options = AgentOptions(
        model="gpt-4.1",
        instructions="You are a helpful assistant. Answer clearly and concisely.",
    )

    async with Client(options=options) as client:
        await client.query("Hello, how are you pal")

        async for message in client.receive_response():
            print(message)


if __name__ == "__main__":
    asyncio.run(main())
