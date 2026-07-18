# Claude API — Session 2: System Prompts + Multi-Turn Memory

Extends Session 1 by adding a system prompt (defines Claude's role) and
maintaining conversation history across multiple turns.

## What this session teaches

- What a system prompt is and why it's a separate parameter from messages
- How to maintain conversation history in a Python list
- Why every turn re-sends the whole history (LLMs have no built-in memory)
- The critical bug of forgetting to append assistant replies to history
- Interactive input loops with input() and while True

## Files

- chat_multi_turn.py — Interactive chatbot with system prompt and memory
- README.md — This file

## Setup

    pip install anthropic --break-system-packages
    export ANTHROPIC_API_KEY="sk-ant-YOUR-KEY"
    python3 chat_multi_turn.py

## How it works

Every turn:
1. User types a message
2. Message appended to history: {"role": "user", "content": "..."}
3. Full history sent to Claude (along with system prompt)
4. Claude's reply appended to history: {"role": "assistant", "content": "..."}
5. Loop until user types "quit"

## The critical rule

You MUST append Claude's reply to history after each turn. If you skip
this, Claude forgets what IT said in previous turns. The bug is silent —
Claude still works, but loses its own contributions to memory.

## Concepts learned

### System prompts define role, not questions
- Persistent across all turns (unlike user messages)
- Higher trust weight than user messages
- Passed as a separate `system` parameter, not in messages list

### Memory is client-side
- Claude has no server-side memory between calls
- Every call rebuilds the full messages list from scratch
- "Memory" is really just resending accumulated history

### Verified with 4-turn conversation
Tested by telling Claude 3 different facts across 3 turns, then asking it
to recall all 3 in turn 4. Claude correctly recalled name, employer, and
favorite color — proving history-based memory works.

## Real use cases this pattern supports

Personal productivity tools where the whole task = conversation:
- Interview prep coach
- Writing assistant / editor
- Language tutor
- Domain expert consultant (SAP, medical, legal, etc.)
- Meeting notes structurer
- Decision journal

## What this does NOT do

- Cannot call external systems (needs Session 4: tool use)
- Cannot read files (needs file I/O patterns)
- Cannot search the web (needs tool use)
- Cannot produce structured JSON reliably (needs Session 3 techniques)

## Next session

Session 3: Structured output with JSON — bridging chat to real programs.
