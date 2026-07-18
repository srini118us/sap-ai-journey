# Claude API — Session 1: First Call

First hands-on session with the Anthropic Python SDK. Goal: understand
what an API call actually is, get one working end-to-end, and build
intuition by breaking it in five different ways.

## What this session teaches

- How to authenticate to the Claude API via environment variables
- The shape of a messages.create() call (model, max_tokens, messages)
- How the response object is structured (response.content[0].text, response.stop_reason)
- Why the API has no memory between calls (and how to work around it)
- How to read Anthropic error types (401, 400, 404) and what they mean

## Files

- chat_basic.py — Working first API call. Sends "What is 2+2?" and prints the answer.
- README.md — This file.

## Setup

    pip install anthropic --break-system-packages
    export ANTHROPIC_API_KEY="sk-ant-YOUR-KEY"
    echo \${ANTHROPIC_API_KEY:0:10}...
    python3 chat_basic.py

Expected output:

    STOP REASON: end_turn
    TEXT: Four

## Concepts learned

### 1. anthropic.Anthropic() is a class, not a function

The anthropic package contains a class called Anthropic.
Calling anthropic.Anthropic() constructs an instance.
The constructor automatically reads the ANTHROPIC_API_KEY
environment variable.

### 2. Every API call takes a messages list

Each message has a role ("user" or "assistant") and content.
Normally alternating user/assistant, though the API is more
lenient than docs suggest.

### 3. Claude has no memory between calls

Every call, you rebuild and resend the whole conversation.
Claude reads the entire messages list as one context.
This IS how memory works.

### 4. response.stop_reason tells you why generation ended

- end_turn — Claude finished naturally
- max_tokens — Hit the max_tokens limit
- stop_sequence — Hit a custom stop word
- tool_use — Claude wants to call a tool

### 5. Tokens are not words

Rough rule: about 4 characters per token in English. Non-English
languages, code, and JSON use more tokens per character.

## The five break-and-fix exercises

| Exercise | What broke | Result | What it taught |
|---|---|---|---|
| 1 | Fake API key | 401 AuthenticationError | HTTP 401 = auth. Bad key rejected on first API call. |
| 2 | Fake model name | 404 NotFoundError | HTTP 404 = not found. Model must exist exactly. |
| 3 | max_tokens=30 | Cut off mid-sentence | Token limit is hard cutoff. Tokens are not words. |
| 4 | messages=[] empty | 400 BadRequestError | API validates input before running model. |
| 5 | Two user messages | Worked, Claude read both | Claude reads whole array. This IS memory. |

## HTTP error reference

| Code | Meaning | Typical fix |
|---|---|---|
| 200 | Success | - |
| 400 | Bad Request | Fix your input format |
| 401 | Unauthorized | Check API key |
| 403 | Forbidden | Not allowed for this action |
| 404 | Not Found | Check model or endpoint spelling |
| 429 | Rate Limit | Slow down requests |
| 500 | Server Error | Anthropic problem, retry |

## Security lesson

Never paste your API key into a chat window, screenshot, or
public document. Store it as an environment variable. If it
leaks, rotate immediately at console.anthropic.com.

For safe verification, use: echo \${ANTHROPIC_API_KEY:0:10}...

This shows only the first 10 characters — enough to confirm
it's set without exposing the whole key.

## Next session

Session 2: System prompts and multi-turn conversation.
Build an interactive chatbot that maintains memory across turns.
