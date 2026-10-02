"""
Session 3: Structured output via prefilling.

Extract structured JSON data from unstructured text about a person.
Uses assistant message prefilling to force JSON output.
"""

import anthropic
import json

client = anthropic.Anthropic()

# The text we want to extract structured data from.
input_text = """Priya Sharma is a 32-year-old data scientist from Bangalore.
She has 8 years of experience and specializes in NLP.
Her email is priya@example.com."""

# System prompt: define what fields to extract.
system_prompt = """You extract structured data from text about a person.
Return valid JSON with these fields exactly:
- name (string)
- age (number)
- role (string)
- location (string)
- years_of_experience (number)
- specialization (string)
- email (string)
If a field is missing from the text, use null."""

# The prefilling trick: we start Claude's reply with "{"
# Claude MUST continue with valid JSON.
response = client.messages.create(
#    model="claude-opus-4-7",
	model="claude-sonnet-4-5",
    max_tokens=1024,
    system=system_prompt,
    messages=[
        {"role": "user", "content": f"Extract data from this text:\n\n{input_text}"},
#        {"role": "assistant", "content": "{"}
    ]
)

# Claude's reply is the CONTINUATION of "{" — so we need to prepend "{" back.
#raw_output = "{" + response.content[0].text
raw_output = response.content[0].text
# Print the raw text so we can see what Claude produced.
print("=== RAW OUTPUT ===")
print(raw_output)

# Parse the JSON into a Python dictionary.
# Defensive: strip markdown code fences if Claude added them.
raw_output = raw_output.strip()
if raw_output.startswith("```json"):
    raw_output = raw_output[7:]     # remove ```json
elif raw_output.startswith("```"):
    raw_output = raw_output[3:]     # remove ```
if raw_output.endswith("```"):
    raw_output = raw_output[:-3]    # remove trailing ```
raw_output = raw_output.strip()
#data = json.loads(raw_output)
data = json.loads(raw_output)
# Now we can access fields programmatically.
print("\n=== PARSED DATA ===")
print(f"Name: {data['name']}")
print(f"Age: {data['age']}")
print(f"Role: {data['role']}")
print(f"Email: {data['email']}"
)

