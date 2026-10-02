"""
Session 1: First Claude API call.

Sends a single user message to Claude and prints the response.
Learning goal: understand the basic shape of an API call.
"""

import anthropic

# Create a client. Reads ANTHROPIC_API_KEY from environment.
client = anthropic.Anthropic()

# Make the API call.
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "What is 2+2? Answer in one word."}
    ]
)

# The response object contains more than just text.
# Print stop_reason first so we can see why generation ended.
print("STOP REASON:", response.stop_reason)
print("TEXT:", response.content[0].text)
