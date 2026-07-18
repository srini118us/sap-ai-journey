"""
Session 4: Tool use.

Claude decides to call a Python function you defined, you execute it,
and pass the result back to Claude for the final answer.
"""

import anthropic
import json

client = anthropic.Anthropic()


# ---------- FUNCTION (from Step 2) ----------

def get_weather(city: str) -> dict:
    """Return fake weather data for a city."""
    fake_data = {
        "Paris": {"temperature": 22, "condition": "sunny", "humidity": 40},
        "Tokyo": {"temperature": 18, "condition": "rainy", "humidity": 75},
        "New York": {"temperature": 15, "condition": "cloudy", "humidity": 60},
    }
    return fake_data.get(city, {"error": f"No data for {city}"})


# ---------- TOOL DEFINITION + FIRST API CALL (from Step 3) ----------

tools = [
    {
        "name": "get_weather",
        "description": "Get current weather for a given city. Returns temperature in Celsius, condition, and humidity percentage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name, e.g. Paris, Tokyo, New York"
                }
            },
            "required": ["city"]
        }
    }
]

user_message = "What's the weather like in Paris?"

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": user_message}
    ]
)


print("=== FIRST RESPONSE ===")
print(f"stop_reason: {response.stop_reason}")
print(f"content: {response.content}")
# Step 4 — Execute the tool and send result back to Claude.

# Extract the tool_use block from Claude's response.
tool_use_block = None
for block in response.content:
    if block.type == "tool_use":
        tool_use_block = block
        break

if tool_use_block is None:
    print("Claude did not request a tool. Nothing to do.")
    exit()

# Route to the actual Python function based on the tool name.
tool_name = tool_use_block.name
tool_input = tool_use_block.input
tool_use_id = tool_use_block.id

print(f"\n=== EXECUTING TOOL ===")
print(f"Claude requested: {tool_name}({tool_input})")

# Actually call the function.
if tool_name == "get_weather":
    tool_result = get_weather(**tool_input)
else:
    tool_result = {"error": f"Unknown tool: {tool_name}"}

print(f"Tool returned: {tool_result}")

# Send the result back to Claude in a SECOND API call.
# The messages list must now include:
#   1. Original user message
#   2. Claude's tool_use response (as-is)
#   3. Your tool_result wrapped in the right format
second_response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": response.content},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(tool_result)
                }
            ]
        }
    ]
)

print(f"\n=== FINAL RESPONSE ===")
print(f"stop_reason: {second_response.stop_reason}")
print(f"Claude says: {second_response.content[0].text}")
