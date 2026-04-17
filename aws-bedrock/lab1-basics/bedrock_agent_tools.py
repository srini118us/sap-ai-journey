"""
AWS Bedrock Lab 1: Agent with Tool Use
Demonstrates the Converse API with tool definitions
"""
import boto3
import json
import time

# Create Bedrock client
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

# Define tools
tools = [
    {
        "toolSpec": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "City name"
                        }
                    },
                    "required": ["city"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "get_stock_price",
            "description": "Get current stock price for a ticker symbol",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock ticker symbol"
                        }
                    },
                    "required": ["symbol"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "search_sap_orders",
            "description": "Search SAP sales orders by customer",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer name or ID"
                        }
                    },
                    "required": []
                }
            }
        }
    }
]

# Simulated tool implementations
def execute_tool(tool_name, tool_input):
    """Execute a tool and return result"""
    if tool_name == "get_weather":
        city = tool_input.get("city", "Unknown")
        return {"city": city, "temperature": 72, "condition": "sunny", "humidity": 45}
    elif tool_name == "get_stock_price":
        symbol = tool_input.get("symbol", "UNKNOWN")
        prices = {"AAPL": 178.50, "MSFT": 415.20, "SAP": 225.80}
        return {"symbol": symbol, "price": prices.get(symbol, 100.00), "currency": "USD"}
    elif tool_name == "search_sap_orders":
        return {"orders": [
            {"order_id": "SO-10001", "customer": "ACME Corp", "amount": 15000},
            {"order_id": "SO-10002", "customer": "ACME Corp", "amount": 8500},
        ], "total": 2}
    return {"error": "Unknown tool"}

def converse_with_retry(messages, max_retries=3):
    """Call converse API with retry logic"""
    for attempt in range(max_retries):
        try:
            return bedrock.converse(
                modelId='us.anthropic.claude-sonnet-4-20250514-v1:0',
                messages=messages,
                toolConfig={"tools": tools}
            )
        except bedrock.exceptions.ThrottlingException:
            wait_time = (attempt + 1) * 5
            print(f"   ⏳ Rate limited, waiting {wait_time}s...")
            time.sleep(wait_time)
    raise Exception("Max retries exceeded")

def chat_with_tools(user_message):
    """Complete conversation with tool use"""
    print(f"\n👤 User: {user_message}")
    print("-" * 50)
    
    messages = [{"role": "user", "content": [{"text": user_message}]}]
    
    # First call
    response = converse_with_retry(messages)
    
    stop_reason = response['stopReason']
    output_message = response['output']['message']
    
    if stop_reason == 'tool_use':
        for content in output_message['content']:
            if 'toolUse' in content:
                tool_use = content['toolUse']
                tool_name = tool_use['name']
                tool_input = tool_use['input']
                tool_use_id = tool_use['toolUseId']
                
                print(f"🔧 Tool Call: {tool_name}")
                print(f"   Input: {json.dumps(tool_input)}")
                
                tool_result = execute_tool(tool_name, tool_input)
                print(f"   Result: {json.dumps(tool_result)}")
                
                messages.append(output_message)
                messages.append({
                    "role": "user",
                    "content": [{
                        "toolResult": {
                            "toolUseId": tool_use_id,
                            "content": [{"json": tool_result}]
                        }
                    }]
                })
                
                # Small delay before next call
                time.sleep(2)
                
                final_response = converse_with_retry(messages)
                final_text = final_response['output']['message']['content'][0]['text']
                print(f"\n🤖 Claude: {final_text}")
                return final_text
    
    response_text = output_message['content'][0]['text']
    print(f"\n🤖 Claude: {response_text}")
    return response_text

# =============================================================================
# TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("AWS BEDROCK - AGENT WITH TOOLS")
    print("=" * 60)
    
    # Test 1: Weather
    chat_with_tools("What's the weather in Atlanta?")
    time.sleep(3)
    
    # Test 2: Stock
    chat_with_tools("What's SAP's stock price?")
    time.sleep(3)
    
    # Test 3: SAP Orders
    chat_with_tools("Find orders for ACME Corp")
    
    print("\n" + "=" * 60)
    print("✅ Agent with tools complete!")