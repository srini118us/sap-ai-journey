# Claude API — Session 4: Tool Use

The primitive under every agentic AI framework. Claude decides to call
YOUR Python function, you execute it, results go back to Claude for the
final synthesis.

This is what LangGraph, ADK, CrewAI, MCP, and Claude Code all use
internally.

## What this session teaches

- How Claude requests tool calls (`ToolUseBlock`, `stop_reason: tool_use`)
- The two-API-call pattern per user turn
- How to route tool names to actual Python functions
- Sending tool results back (as user role with `type: tool_result`)
- The `tool_use_id` for matching results to requests

## Files

- weather_tool.py — Full working tool-use round-trip with fake weather data
- README.md — This file

## Setup

    pip install anthropic --break-system-packages
    export ANTHROPIC_API_KEY="sk-ant-YOUR-KEY"
    python3 weather_tool.py

## Expected output

    === FIRST RESPONSE ===
    stop_reason: tool_use
    content: [ToolUseBlock(id='toolu_...', input={'city': 'Paris'}, ...)]

    === EXECUTING TOOL ===
    Claude requested: get_weather({'city': 'Paris'})
    Tool returned: {'temperature': 22, 'condition': 'sunny', 'humidity': 40}

    === FINAL RESPONSE ===
    stop_reason: end_turn
    Claude says: The weather in Paris is currently sunny with a temperature
    of 22°C and humidity at 40%.

## The pattern (works for any tool)

    Turn 1 API call:
      user_message + tools list
      -> Claude returns ToolUseBlock with name + input + id
      -> stop_reason: "tool_use"

    Your code:
      Execute the actual Python function
      Get structured result

    Turn 2 API call:
      Original user message
      + Claude's assistant response (with tool_use block)
      + New user message with tool_result (matching id, JSON string content)
      -> Claude synthesizes final natural language answer
      -> stop_reason: "end_turn"

## Key structural details

- Tool result is packaged as USER role content, not assistant
- content field in tool_result must be a JSON string (use json.dumps)
- tool_use_id must match exactly - critical for parallel tool calls
- Pass Claude's original response.content as-is when echoing back

## How this maps to production systems

Every agent framework wraps this pattern:

| Framework | Its abstraction |
|---|---|
| LangGraph | @tool decorator + graph node |
| Google ADK | tools=[] list in Agent() |
| CrewAI | Tool class with _run method |
| MCP | Server exposing tools over protocol |
| Claude Code | Same pattern, wrapped in CLI |

Under the hood, all of them make Anthropic API calls that look like
weather_tool.py. Learning this pattern raw = you understand what every
framework hides.

## Real production considerations (not in this lab)

- Loop: call tools in sequence until stop_reason: end_turn
- Error handling: what if function crashes? Send error back to Claude
- Timeouts: what if function is slow?
- Cost: each turn is 2 API calls, not 1
- Streaming: real UIs stream tokens as Claude generates
- Multi-tool: Claude may request multiple tools in one turn
- Validation: don't blindly trust tool arguments from Claude

## Next steps

Foundation phase complete. Not planning Sessions 5+ formally.

Practical follow-ups:
- Try Claude Code on EWA Analyzer (next week)
- Apply this pattern in one small real project
- Deloitte demo prep + Raj outreach take priority for 2 weeks
