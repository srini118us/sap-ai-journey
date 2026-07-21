
"""
Session 2: Interactive chatbot with system prompt and multi-turn memory.

Extends Session 1 by:
- Adding a system prompt (defines Claude's role)
- Maintaining conversation history across turns
- Running in a loop until user types 'quit'
"""

import anthropic

# Create the API client. Reads ANTHROPIC_API_KEY from environment.
client = anthropic.Anthropic()

# The conversation history starts empty.
# We will append to this list as the conversation grows.
messages = []

# The system prompt defines Claude's role for the entire conversation.
# It applies to every turn, so we set it once here.
system_prompt = "You are a helpful Python tutor. Be concise. Explain concepts before showing code."

# Greeting message so the user knows the chat has started.
print("Chat with Claude. Type 'quit' to exit.")
print()  # blank line

# The main conversation loop. Runs until we break out.
while True:
    # Ask the user for input. input() shows the prompt and waits.
    user_input = input("You: ")

    # If user typed 'quit', break out of the loop and end the program.
    if user_input.lower() == "quit":
        print("Goodbye.")
        break

	# Append the user's message to conversation history.
    messages.append({"role": "user", "content": user_input})

    # Call the API. Note we pass:
    # - system: the persistent role from our variable
    # - messages: the FULL history (user always sees all past turns)
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=system_prompt,
        messages=messages
    )

    # Extract Claude's reply text.
    assistant_reply = response.content[0].text

    # CRITICAL: append Claude's reply to history so next turn has context.
    messages.append({"role": "assistant", "content": assistant_reply})

    # Print the reply to the user.
    print(f"Claude: {assistant_reply}")
    print()
