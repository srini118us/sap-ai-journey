# Claude API — Session 3: Structured Output

Get Claude to return machine-parseable JSON instead of prose. This is the
leap from "chatbot" to "component in software."

## What this session teaches

- Why structured output matters (bridge to real programs)
- Three techniques for reliable structured output:
  1. Ask nicely in system prompt (unreliable)
  2. Show examples in system prompt (better)
  3. Prefilling — start Claude's reply for it (most reliable)
- Model-specific behavior — techniques vary by model
- Defensive parsing — never trust LLM output blindly

## Files

- extract_person.py — Extract structured data from unstructured text
- README.md — This file

## Setup

    pip install anthropic --break-system-packages
    export ANTHROPIC_API_KEY="sk-ant-YOUR-KEY"
    python3 extract_person.py

## The use case

Given a paragraph about a person, extract structured JSON.

Input:
    "Priya Sharma is a 32-year-old data scientist from Bangalore.
    She has 8 years of experience and specializes in NLP.
    Her email is priya@example.com."

Output:
    {
      "name": "Priya Sharma",
      "age": 32,
      "role": "data scientist",
      "location": "Bangalore",
      "years_of_experience": 8,
      "specialization": "NLP",
      "email": "priya@example.com"
    }

Real-world equivalents: resume parsers, log analyzers, email classifiers,
extraction from customer support tickets.

## Technique 1: Prefilling

Start Claude's reply with a structural character like `{`:

    messages=[
        {"role": "user", "content": "Extract data from: ..."},
        {"role": "assistant", "content": "{"}   # <-- prefill
    ]

Claude MUST continue from `{` — cannot add prose or markdown fences
before it. Structurally forces valid JSON.

Downside: not all models support prefill. `claude-opus-4-7` does not.
`claude-sonnet-4-5` does.

## Technique 2: Defensive parsing

Assume Claude will occasionally disobey instructions. Strip markdown
fences before parsing:

    raw_output = raw_output.strip()
    if raw_output.startswith("```json"):
        raw_output = raw_output[7:]
    elif raw_output.startswith("```"):
        raw_output = raw_output[3:]
    if raw_output.endswith("```"):
        raw_output = raw_output[:-3]
    raw_output = raw_output.strip()

Works on any model. Handles the common case of Claude wrapping JSON in
markdown code fences even when told not to.

## Real-world lesson learned

The system prompt in this script literally says:
    "Do not use markdown code fences."

Claude ignored this instruction and added fences anyway. This is a real
truth about LLMs: instructions are hints, not guarantees. Production
code always needs defensive layers.

## When to use which technique

| Situation | Best technique |
|---|---|
| Simple output, model supports prefill | Prefill |
| Model doesn't support prefill | Defensive stripping |
| Production reliability | Both together |
| Prototyping | Either works |

## Real use cases this pattern unlocks

Session 3 is where Claude API stops being "just chat" and starts being
a component in software:

- Log analyzers — feed log line, get structured fields
- Resume parsers — feed resume text, get structured skills/experience
- Email classifiers — category + priority + suggested action
- Extraction from customer tickets, contracts, forms
- Reasoning layer of agents — Claude decides what to do next

## What this does NOT do

- Cannot call external systems (still needs Session 4: tool use)
- Cannot chain multiple decisions autonomously (needs agent patterns)

## Next session

Session 4: Tool use — Claude calls YOUR Python functions. The pattern
that maps directly to LangGraph/ADK style agents.
