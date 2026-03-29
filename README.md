## agnos

Minimal vendor-agnostic async SDK that normalizes Claude and OpenAI Agents into one event stream API.

### Install

```bash
pip install -e .
```

### Core API

```python
from agnos import AgentOptions, Client, AgentText, AgentThinking, AgentTurnComplete

options = AgentOptions(
    model="gpt-4.1",  # or "claude-sonnet-4-5"
    instructions="You are a helpful assistant.",
    provider="auto",  # "openai", "claude", or "auto"
)

async with Client(options) as client:
    await client.query("Give me one sentence about Rome.")
    async for event in client.receive_response():
        if isinstance(event, AgentThinking):
            print("[thinking]", event.text)
        elif isinstance(event, AgentText):
            print(event.text, end="")
        elif isinstance(event, AgentTurnComplete):
            print("\nDone:", event.is_error, event.stop_reason, event.usage, event.extra)
```

### Event Model

- `AgentText`: visible assistant text chunks
- `AgentThinking`: reasoning/thinking chunks when available
- `AgentTurnComplete`: end-of-turn metadata (`is_error`, `usage`, `extra`, etc.)

### Backend Resolution

`provider="auto"` chooses backend from `model`:

- Claude if the model contains `claude` or `anthropic`
- OpenAI if it starts with `gpt-`, `o1`, `o3`, `o4`, or `chatgpt`

If inference is ambiguous/unknown, set `provider` explicitly.

### Runtime Behavior

- Use the client as an async context manager (`async with Client(...)`).
- Turn order is strict: `query(...)` then `receive_response()`.
- Calling `query(...)` twice without consuming `receive_response()` raises an error.
- Backend exceptions are normalized into `AgentTurnComplete(is_error=True, ...)`.

### Example

Run:

```bash
python examples/example_agnos.py
```
