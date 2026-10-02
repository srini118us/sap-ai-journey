import os
from typing import TypedDict
from dotenv import load_dotenv
# Load AI Core environment variables
load_dotenv()

from gen_ai_hub.proxy.native.openai import chat
from langgraph.graph import StateGraph, START, END

# Load AI Core environment variables
load_dotenv()

# 1. Define the Graph State schema
class GraphState(TypedDict):
    user_query: str
    prompt_payload: list[dict]
    model_response: str


# 2. Define Node 1: Prepare
def prepare_node(state: GraphState) -> dict:
    """Formats system instructions and packages the query into messages."""
    messages = [
        {"role": "system", "content": "You are a concise enterprise assistant operating via SAP AI Core."},
        {"role": "user", "content": state["user_query"]}
    ]
    return {"prompt_payload": messages}


# 3. Define Node 2: Call Model
def call_model_node(state: GraphState) -> dict:
    """Invokes the active gpt-4o-mini deployment via SAP GenAI Hub SDK."""
    model = os.getenv("MODEL_NAME", "gpt-4o-mini")
    
    response = chat.completions.create(
        model_name=model,
        messages=state["prompt_payload"],
        max_tokens=80
    )
    
    output_text = response.choices[0].message.content
    return {"model_response": output_text}


# 4. Assemble the Graph
builder = StateGraph(GraphState)

# Add nodes
builder.add_node("prepare", prepare_node)
builder.add_node("call_model", call_model_node)

# Wire the edges: START -> prepare -> call_model -> END
builder.add_edge(START, "prepare")
builder.add_edge("prepare", "call_model")
builder.add_edge("call_model", END)

# Compile into a runnable
graph = builder.compile()


# 5. Execute and Validate
if __name__ == "__main__":
    initial_input = {
        "user_query": "Explain what a two-node LangGraph pipeline does in one punchy sentence."
    }
    # 1. Print ASCII Topology
    print("\n--- Graph Visualization ---")
    print(graph.get_graph().draw_ascii())
    print("\n--- Invoking Graph ---")
    result = graph.invoke(initial_input)
    print("\n--- Final Graph Output ---")
    print(f"Prepared Payload: {result['prompt_payload']}")
    print(f"\nModel Response:\n{result['model_response']}")
    png_bytes = graph.get_graph().draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(png_bytes)