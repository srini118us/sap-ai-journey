import os
from dotenv import load_dotenv


load_dotenv()
print("AICORE_BASE_URL:", os.environ.get("AICORE_BASE_URL"))
print("AICORE_AUTH_URL:", os.environ.get("AICORE_AUTH_URL"))
print("AICORE_API_KEY:", os.environ.get("AICORE_API_KEY"))

from gen_ai_hub.proxy.native.openai import chat

model = os.getenv("MODEL_NAME", "gpt-4o-mini")


response = chat.completions.create(
    model_name=model,
    messages=[
        {"role": "user", "content": "Ping test: confirm connection in one sentence."}
    ],
    max_tokens=60
)

print("\n--- Response from SAP AI Core ---")
print(response.choices[0].message.content)