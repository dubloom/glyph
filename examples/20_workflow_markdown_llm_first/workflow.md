---
name: blurbFromTopic
description: First step is an LLM; `{{ ... }}` placeholders are filled from `run(initial_input=...)`.
options:
  model: gpt-5.4-mini
  reasoning_effort: medium
---

## Step: draftBlurb

Write two punchy sentences about {{ topic }}.

Tone: {{ tone }}. No lists, no title.
