"""
AWS Bedrock Lab 2: SAP Procurement Agent
Demonstrates multi-tool agent with SAP-like operations
"""
import boto3
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
MODEL_ID = os.getenv('BEDROCK_MODEL_SONNET', 'us.anthropic.claude-sonnet-4-20250514-v1:0')
RETRY_ATTEMPTS = int(os.getenv('BEDROCK_RETRY_ATTEMPTS', 3))
RETRY_DELAY = int(os.getenv('BEDROCK_RETRY_DELAY', 5))

# Create Bedrock client
bedrock = boto3.client('bedrock-runtime', region_name=AWS_REGION)

# =============================================================================
# MOCK SAP DATA (Replace with OData calls in production)
# =============================================================================
PURCHASE_ORDERS = {
    "4500000123": {
        "po_number": "4500000123",
        "vendor": "ACME Corp",
        "vendor_id": "VEND-001",
        "created_date": "2026-04-10",
        "status": "Approved",
        "total_amount": 15000.00,
        "currency": "USD",
        "items": [
            {"item": 10, "material": "MAT-1001", "description": "Steel Plates", "quantity": 100, "unit": "EA", "price": 100.00},
            {"item": 20, "material": "MAT-1002", "description": "Copper Wire", "quantity": 50, "unit": "KG", "price": 100.00}
        ]
    },
    "4500000124": {
        "po_number": "4500000124",
        "vendor": "Global Supplies",
        "vendor_id": "VEND-002",
        "created_date": "2026-04-12",
        "status": "Pending",
        "total_amount": 8500.00,
        "currency": "USD",
        "items": [
            {"item": 10, "material": "MAT-2001", "description": "Aluminum Sheets", "quantity": 200, "unit": "EA", "price": 42.50}
        ]
    },
    "4500000125": {
        "po_number": "4500000125",
        "vendor": "ACME Corp",
        "vendor_id": "VEND-001",
        "created_date": "2026-04-15",
        "status": "Approved",
        "total_amount": 22000.00,
        "currency": "USD",
        "items": [
            {"item": 10, "material": "MAT-1001", "description": "Steel Plates", "quantity": 150, "unit": "EA", "price": 100.00},
            {"item": 20, "material": "MAT-3001", "description": "Bolts M10", "quantity": 1000, "unit": "EA", "price": 7.00}
        ]
    }
}

INVENTORY = {
    "MAT-1001": {"material": "MAT-1001", "description": "Steel Plates", "available": 500, "unit": "EA", "plant": "1710"},
    "MAT-1002": {"material": "MAT-1002", "description": "Copper Wire", "available": 200, "unit": "KG", "plant": "1710"},
    "MAT-2001": {"material": "MAT-2001", "description": "Aluminum Sheets", "available": 150, "unit": "EA", "plant": "1710"},
    "MAT-3001": {"material": "MAT-3001", "description": "Bolts M10", "available": 5000, "unit": "EA", "plant": "1710"}
}

VENDORS = {
    "VEND-001": {"id": "VEND-001", "name": "ACME Corp", "rating": 4.5, "on_time_delivery": "95%"},
    "VEND-002": {"id": "VEND-002", "name": "Global Supplies", "rating": 4.2, "on_time_delivery": "88%"}
}

# Sales order counter
so_counter = 5680

# =============================================================================
# TOOL DEFINITIONS
# =============================================================================
tools = [
    {
        "toolSpec": {
            "name": "get_purchase_orders",
            "description": "Search and list purchase orders. Can filter by vendor name, status, or date range.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "vendor": {"type": "string", "description": "Vendor name to filter by"},
                        "status": {"type": "string", "description": "PO status: Approved, Pending, Rejected"},
                        "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"}
                    },
                    "required": []
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "get_po_details",
            "description": "Get detailed information about a specific purchase order including line items",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "po_number": {"type": "string", "description": "Purchase order number"}
                    },
                    "required": ["po_number"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "check_inventory",
            "description": "Check available inventory/stock for a material",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "material": {"type": "string", "description": "Material number or description"}
                    },
                    "required": ["material"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "get_vendor_info",
            "description": "Get vendor information including performance metrics",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "vendor_id": {"type": "string", "description": "Vendor ID"},
                        "vendor_name": {"type": "string", "description": "Vendor name"}
                    },
                    "required": []
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "create_sales_order",
            "description": "Create a sales order from a purchase order",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "po_number": {"type": "string", "description": "Source purchase order number"},
                        "customer": {"type": "string", "description": "Customer name"}
                    },
                    "required": ["po_number", "customer"]
                }
            }
        }
    }
]

# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================
def execute_tool(tool_name, tool_input):
    """Execute a tool and return result"""
    global so_counter
    
    if tool_name == "get_purchase_orders":
        vendor_filter = tool_input.get("vendor", "").lower()
        status_filter = tool_input.get("status", "").lower()
        
        results = []
        for po in PURCHASE_ORDERS.values():
            if vendor_filter and vendor_filter not in po["vendor"].lower():
                continue
            if status_filter and status_filter != po["status"].lower():
                continue
            results.append({
                "po_number": po["po_number"],
                "vendor": po["vendor"],
                "status": po["status"],
                "total_amount": po["total_amount"],
                "created_date": po["created_date"]
            })
        return {"purchase_orders": results, "count": len(results)}
    
    elif tool_name == "get_po_details":
        po_number = tool_input.get("po_number")
        if po_number in PURCHASE_ORDERS:
            return PURCHASE_ORDERS[po_number]
        return {"error": f"PO {po_number} not found"}
    
    elif tool_name == "check_inventory":
        material = tool_input.get("material", "").upper()
        # Search by material number or description
        for mat_id, mat_data in INVENTORY.items():
            if material in mat_id or material.lower() in mat_data["description"].lower():
                return mat_data
        return {"error": f"Material {material} not found"}
    
    elif tool_name == "get_vendor_info":
        vendor_id = tool_input.get("vendor_id", "")
        vendor_name = tool_input.get("vendor_name", "").lower()
        
        for v_id, v_data in VENDORS.items():
            if vendor_id == v_id or vendor_name in v_data["name"].lower():
                return v_data
        return {"error": "Vendor not found"}
    
    elif tool_name == "create_sales_order":
        po_number = tool_input.get("po_number")
        customer = tool_input.get("customer")
        
        if po_number not in PURCHASE_ORDERS:
            return {"error": f"PO {po_number} not found"}
        
        po = PURCHASE_ORDERS[po_number]
        so_counter += 1
        return {
            "sales_order": f"SO-{so_counter}",
            "source_po": po_number,
            "customer": customer,
            "items": len(po["items"]),
            "total_amount": po["total_amount"],
            "status": "Created"
        }
    
    return {"error": f"Unknown tool: {tool_name}"}

# =============================================================================
# AGENT LOGIC
# =============================================================================
def converse_with_retry(messages, max_retries=RETRY_ATTEMPTS):
    """Call converse API with retry logic"""
    for attempt in range(max_retries):
        try:
            return bedrock.converse(
                modelId=MODEL_ID,
                messages=messages,
                toolConfig={"tools": tools},
                system=[{"text": """You are an SAP Procurement Assistant. You help users with:
- Finding and analyzing purchase orders
- Checking inventory levels
- Getting vendor information
- Creating sales orders from purchase orders

Always use the available tools to get accurate data. Be concise and professional.
When presenting data, format it clearly with key information highlighted."""}]
            )
        except Exception as e:
            if "ThrottlingException" in str(e):
                wait_time = (attempt + 1) * RETRY_DELAY
                print(f"   [WAIT] Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e
    raise Exception("Max retries exceeded")

def process_tool_calls(response, messages):
    """Process tool calls and get final response"""
    output_message = response['output']['message']
    
    # Collect all tool uses
    tool_results = []
    for content in output_message['content']:
        if 'toolUse' in content:
            tool_use = content['toolUse']
            tool_name = tool_use['name']
            tool_input = tool_use['input']
            tool_use_id = tool_use['toolUseId']
            
            print(f"   [TOOL] {tool_name}: {json.dumps(tool_input)}")
            
            result = execute_tool(tool_name, tool_input)
            tool_results.append({
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "content": [{"json": result}]
                }
            })
    
    # Add assistant message and tool results
    messages.append(output_message)
    messages.append({"role": "user", "content": tool_results})
    
    # Get next response
    time.sleep(2)  # Small delay to avoid rate limiting
    return converse_with_retry(messages)

def chat(user_message, conversation_history=None):
    """Main chat function with conversation history support"""
    if conversation_history is None:
        conversation_history = []
    
    print(f"\n[USER] {user_message}")
    print("-" * 60)
    
    # Add user message
    conversation_history.append({
        "role": "user", 
        "content": [{"text": user_message}]
    })
    
    # Get response
    response = converse_with_retry(conversation_history)
    
    # Handle tool use loop
    while response['stopReason'] == 'tool_use':
        response = process_tool_calls(response, conversation_history)
    
    # Extract final text
    final_message = response['output']['message']
    conversation_history.append(final_message)
    
    response_text = ""
    for content in final_message['content']:
        if 'text' in content:
            response_text += content['text']
    
    print(f"\n[BEDROCK] {response_text}")
    return response_text, conversation_history

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("SAP PROCUREMENT AGENT - AWS Bedrock Lab 2")
    print("=" * 60)
    print("\nCommands: 'quit' to exit, 'clear' to reset conversation\n")
    
    history = []
    
    while True:
        try:
            user_input = input("\n[INPUT] You: ").strip()
            
            if user_input.lower() == 'quit':
                print("\nExiting...")
                break
            elif user_input.lower() == 'clear':
                history = []
                print("\n[INFO] Conversation cleared")
                continue
            elif not user_input:
                continue
            
            _, history = chat(user_input, history)
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            time.sleep(3)