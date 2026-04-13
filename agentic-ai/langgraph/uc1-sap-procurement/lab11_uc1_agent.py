"""
Lab 11 UC1: LangGraph + SAP AI Core + S/4HANA
Production-Ready SAP Procurement Agent

Run: python lab11_uc1_agent.py

Requirements:
- .env file with credentials (see .env template)
- pip install -r requirements.txt
"""

# ============================================
# PART 1: IMPORTS AND SETUP
# ============================================

import os
import re
import json
import uuid
from typing import TypedDict, Annotated, List, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# LangGraph imports
from langgraph.graph import StateGraph, END, add_messages
from langgraph.checkpoint.memory import MemorySaver

# LangChain imports
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

# HTTP client for S/4HANA
import httpx

# OpenAI for LLM-based routing
from openai import OpenAI

# OpenAI for LLM-based routing
from openai import OpenAI


# ============================================
# PART 2: VERIFY ENVIRONMENT
# ============================================

def verify_environment():
    """Check all required environment variables are set."""
    required_vars = [
        'S4HANA_BASE_URL',
        'S4HANA_USER',
        'S4HANA_PASSWORD',
        'OPENAI_API_KEY',
    ]
    
    optional_vars = [
        'AICORE_AUTH_URL',
        'AICORE_CLIENT_ID',
        'AICORE_CLIENT_SECRET',
        'AICORE_BASE_URL',
        'ORCHESTRATION_DEPLOYMENT_ID',
        'LANGCHAIN_API_KEY',
        'BPA_API_URL',
        'BPA_AUTH_URL',
        'BPA_CLIENT_ID',
        'BPA_CLIENT_SECRET',
        'BPA_DEFINITION_ID',
        'REQUESTOR_EMAIL',
    ]
    
    print("=" * 50)
    print("ENVIRONMENT CHECK")
    print("=" * 50)
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'PASSWORD' in var or 'SECRET' in var or 'KEY' in var:
                print(f"  [OK] {var}: ****")
            else:
                print(f"  [OK] {var}: {value[:40]}..." if len(str(value)) > 40 else f"  [OK] {var}: {value}")
        else:
            print(f"  [MISSING] {var}")
            missing.append(var)
    
    print("\nOptional:")
    for var in optional_vars:
        value = os.getenv(var)
        status = "[SET]" if value else "[NOT SET]"
        print(f"  {status} {var}")
    
    if missing:
        print(f"\nERROR: Missing required variables: {missing}")
        return False
    
    # Show BPA status
    bpa_configured = all([
        os.getenv('BPA_API_URL'),
        os.getenv('BPA_CLIENT_ID'),
        os.getenv('BPA_CLIENT_SECRET'),
        os.getenv('BPA_DEFINITION_ID')
    ])
    print(f"\nSAP BPA Integration: {'ENABLED' if bpa_configured else 'DISABLED'}")
    
    print("\nEnvironment OK")
    return True


# ============================================
# PART 3: AGENT STATE DEFINITION
# ============================================

class AgentState(TypedDict):
    """
    State that flows through our procurement agent.
    
    The 'add_messages' annotation appends new messages
    instead of replacing the list (maintains conversation history).
    """
    
    # Core conversation
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Intent classification
    intent: Optional[str]  # 'po_query', 'policy_lookup', 'po_action', 'general'
    
    # Tool execution results
    tool_results: Optional[dict]
    
    # RAG context from policy lookup
    rag_context: Optional[str]
    
    # Human-in-the-Loop
    requires_approval: bool
    approval_status: Optional[str]  # 'pending', 'approved', 'rejected'
    approval_reason: Optional[str]
    
    # PO metadata
    po_number: Optional[str]
    po_amount: Optional[float]


# ============================================
# PART 4: S/4HANA CLIENT AND TOOLS
# ============================================

class S4HANAClient:
    """Client for S/4HANA OData APIs."""
    
    def __init__(self):
        self.base_url = os.getenv('S4HANA_BASE_URL')
        self.user = os.getenv('S4HANA_USER')
        self.password = os.getenv('S4HANA_PASSWORD')
        
    def get_purchase_order(self, po_number: str) -> dict:
        """Fetch a single PO by number with item-level amounts."""
        # Expand to get items for calculating total amount
        url = f"{self.base_url}/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder('{po_number}')?$expand=to_PurchaseOrderItem"
        
        try:
            response = httpx.get(
                url,
                auth=(self.user, self.password),
                headers={'Accept': 'application/json'},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json().get('d', {})
                
                # Calculate total amount from items
                items = data.get('to_PurchaseOrderItem', {}).get('results', [])
                total_amount = sum(
                    float(item.get('NetPriceAmount', 0) or 0) * float(item.get('OrderQuantity', 1) or 1)
                    for item in items
                )
                
                return {
                    'po_number': data.get('PurchaseOrder'),
                    'vendor': data.get('Supplier'),
                    'vendor_name': data.get('AddressName', 'N/A'),
                    'amount': total_amount,
                    'currency': data.get('DocumentCurrency'),
                    'status': data.get('PurchasingProcessingStatus', 'N/A'),
                    'created_date': data.get('CreationDate'),
                    'company_code': data.get('CompanyCode'),
                    'item_count': len(items)
                }
            elif response.status_code == 404:
                return {'error': f'PO {po_number} not found'}
            else:
                return {'error': f'API error: {response.status_code}'}
                
        except Exception as e:
            return {'error': f'Connection error: {str(e)}'}
    
    def list_purchase_orders(self, top: int = 5) -> list:
        """List recent POs with calculated amounts."""
        url = f"{self.base_url}/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder"
        params = {'$top': top, '$format': 'json', '$expand': 'to_PurchaseOrderItem'}
        
        try:
            response = httpx.get(
                url,
                params=params,
                auth=(self.user, self.password),
                timeout=60.0  # Longer timeout for expanded query
            )
            
            if response.status_code == 200:
                results = response.json().get('d', {}).get('results', [])
                po_list = []
                
                for po in results:
                    # Calculate total from items
                    items = po.get('to_PurchaseOrderItem', {}).get('results', [])
                    total_amount = sum(
                        float(item.get('NetPriceAmount', 0) or 0) * float(item.get('OrderQuantity', 1) or 1)
                        for item in items
                    )
                    
                    po_list.append({
                        'po_number': po.get('PurchaseOrder'),
                        'vendor': po.get('Supplier'),
                        'vendor_name': po.get('AddressName', 'N/A'),
                        'amount': total_amount,
                        'currency': po.get('DocumentCurrency'),
                        'item_count': len(items)
                    })
                
                return po_list
            return []
            
        except Exception as e:
            return [{'error': str(e)}]


# Initialize S/4HANA client
s4_client = S4HANAClient()


# Define tools
@tool
def get_purchase_order(po_number: str) -> dict:
    """
    Fetch a Purchase Order from S/4HANA by PO number.
    
    Args:
        po_number: The purchase order number (e.g., '4500000001')
    
    Returns:
        Dictionary with PO details including vendor, amount, status
    """
    return s4_client.get_purchase_order(po_number)


@tool
def list_purchase_orders(count: int = 5) -> list:
    """
    List recent Purchase Orders from S/4HANA.
    
    Args:
        count: Number of POs to return (default 5)
    
    Returns:
        List of PO summaries
    """
    return s4_client.list_purchase_orders(top=count)


@tool
def calculate_po_value(po_number: str) -> dict:
    """
    Get the total value of a Purchase Order for approval checks.
    
    Args:
        po_number: The purchase order number
    
    Returns:
        Dictionary with amount and currency
    """
    po = s4_client.get_purchase_order(po_number)
    if 'error' in po:
        return po
    return {
        'po_number': po_number,
        'amount': float(po.get('amount', 0) or 0),
        'currency': po.get('currency', 'USD')
    }


# Collect tools
tools = [get_purchase_order, list_purchase_orders, calculate_po_value]


# ============================================
# PART 5: RAG SYSTEM (CHROMADB + OPENAI)
# ============================================

# Sample procurement policies
PROCUREMENT_POLICIES = """
# Procurement Policy Manual

## Purchase Order Approval Thresholds

The following approval levels apply to all purchase orders:

- Orders under $10,000: Auto-approved by system
- Orders $10,000 to $50,000: Requires manager approval
- Orders $50,000 to $100,000: Requires director approval  
- Orders over $100,000: Requires VP approval
- Orders over $500,000: Requires CFO approval

## Vendor Requirements

All vendors must meet these requirements before purchase orders can be issued:

1. Must be registered in SAP Vendor Master
2. Must have valid tax identification on file
3. Must complete annual compliance certification
4. Must maintain current insurance certificates
5. Must pass financial stability assessment for orders over $100,000

## Emergency Purchases

Emergency purchases may bypass standard approval workflow under these conditions:

- Documented business justification must be provided
- CFO must be notified within 24 hours
- Retroactive approval must be obtained within 5 business days
- Maximum emergency purchase amount: $25,000

## Payment Terms

Standard payment terms by vendor category:

- Strategic vendors: Net 60
- Preferred vendors: Net 45
- Standard vendors: Net 30
- New vendors (first 6 months): Net 15

## Compliance Requirements

All purchases must comply with:

- SOX controls for financial reporting
- GDPR requirements for data-related purchases
- Export control regulations for international vendors
- Anti-bribery and corruption policies

## Three-Way Match

All invoices require three-way match:
1. Purchase Order
2. Goods Receipt
3. Vendor Invoice

Tolerance levels:
- Quantity variance: +/-5%
- Price variance: +/-2%
"""


def initialize_rag():
    """Initialize RAG system with ChromaDB and OpenAI embeddings."""
    print("\nInitializing RAG system...")
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    # Split policies into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=['\n\n', '\n', '. ', ' ']
    )
    
    chunks = text_splitter.split_text(PROCUREMENT_POLICIES)
    print(f"  Split into {len(chunks)} chunks")
    
    # Create documents
    documents = [
        Document(
            page_content=chunk,
            metadata={'source': 'procurement_policies.md', 'chunk_id': i}
        )
        for i, chunk in enumerate(chunks)
    ]
    
    # Initialize ChromaDB
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name='procurement_policies'
    )
    
    print(f"  ChromaDB initialized with {len(documents)} documents")
    return vectorstore


# ============================================
# PART 6: AGENT NODES
# ============================================

# --- 6.1 Guardrails ---

PII_PATTERNS = {
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
}


def mask_pii(text: str) -> str:
    """Mask PII in input text."""
    masked = text
    for pii_type, pattern in PII_PATTERNS.items():
        masked = re.sub(pattern, f'[MASKED_{pii_type.upper()}]', masked)
    return masked


def validate_input(text: str) -> Tuple[bool, str]:
    """Validate input for safety."""
    injection_patterns = [
        r'ignore previous instructions',
        r'forget your training',
        r'you are now',
        r'act as if',
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, text.lower()):
            return False, 'Potential prompt injection detected'
    
    if len(text) > 10000:
        return False, 'Input too long'
    
    return True, 'Valid'


def sanitize_input(text: str) -> str:
    """Clean and normalize user input."""
    # Strip leading/trailing whitespace
    text = text.strip()
    # Normalize multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    # Remove any invisible/control characters
    text = ''.join(char for char in text if char.isprintable() or char == ' ')
    return text


def guardrails_node(state: AgentState) -> dict:
    """Apply input sanitization, validation and PII masking."""
    print("  [Guardrails] Checking input...")
    
    last_message = state['messages'][-1]
    content = last_message.content
    
    # Sanitize input first
    content = sanitize_input(content)
    
    # Validate
    is_valid, reason = validate_input(content)
    if not is_valid:
        print(f"    Blocked: {reason}")
        return {
            'messages': [AIMessage(content=f'Request blocked: {reason}')]
        }
    
    # Mask PII
    masked_content = mask_pii(content)
    
    # If content was sanitized or PII masked, update the message
    if masked_content != last_message.content:
        if masked_content != content:
            print("    PII masked in input")
        new_messages = list(state['messages'][:-1])
        new_messages.append(HumanMessage(content=masked_content))
        print("    Input sanitized and validated")
        return {'messages': new_messages}
    
    print("    Input validated")
    return {}


# --- 6.2 Router (LLM-based) ---

# Initialize OpenAI client
openai_client = OpenAI()


def classify_intent_with_llm(query: str) -> str:
    """Use LLM to classify user intent."""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an intent classifier for a procurement agent. 
Classify the user query into exactly one of these intents:

- po_query: Questions about specific purchase orders, PO status, PO details, listing POs, anything with PO numbers
- policy_lookup: Questions about procurement policies, rules, guidelines, approval thresholds, payment terms, compliance
- general: Greetings, help requests, general questions

Respond with ONLY the intent name, nothing else."""
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0,
            max_tokens=20
        )
        
        intent = response.choices[0].message.content.strip().lower()
        
        # Validate intent
        if intent in ['po_query', 'policy_lookup', 'general']:
            return intent
        else:
            return 'general'
            
    except Exception as e:
        print(f"    LLM classification error: {e}")
        # Fallback to keyword matching
        return classify_intent_keywords(query)


def classify_intent_keywords(query: str) -> str:
    """Fallback keyword-based classification."""
    query_lower = query.lower()
    
    if any(kw in query_lower for kw in ['policy', 'rule', 'guideline', 'compliance', 'approval threshold', 'requirement', 'payment terms']):
        return 'policy_lookup'
    elif any(kw in query_lower for kw in ['po', 'purchase order', 'order', 'vendor', 'list', 'status', '450000']):
        return 'po_query'
    else:
        return 'general'


def router_node(state: AgentState) -> dict:
    """Classify intent using LLM and route to appropriate handler."""
    print("  [Router] Classifying intent with LLM...")
    
    last_message = state['messages'][-1].content.strip()
    
    intent = classify_intent_with_llm(last_message)
    
    print(f"    Intent: {intent}")
    return {'intent': intent}


def route_by_intent(state: AgentState) -> str:
    """Routing function for conditional edges."""
    intent = state.get('intent', 'general')
    
    if intent == 'policy_lookup':
        return 'rag'
    elif intent in ['po_query', 'po_action']:
        return 'tools'
    else:
        return 'respond'


# --- 6.3 RAG Node ---

# Will be set after initialization
vectorstore = None


def rag_node(state: AgentState) -> dict:
    """Retrieve relevant policy context."""
    print("  [RAG] Searching policies...")
    
    query = state['messages'][-1].content
    
    # Search for relevant policies
    results = vectorstore.similarity_search(query, k=3)
    
    # Format context
    context_parts = []
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get('source', 'Policy')
        context_parts.append(f"[Source {i}: {source}]\n{doc.page_content}")
    
    context = '\n\n'.join(context_parts)
    
    print(f"    Found {len(results)} relevant policy sections")
    return {'rag_context': context}


# --- 6.4 Tool Executor ---

def extract_amount_filter(query: str) -> tuple:
    """Extract amount filter from query (e.g., '> 50000', 'over 50000')."""
    query_lower = query.lower()
    
    # Patterns: "> 50000", "greater than 50000", "over 50000", "above 50000", "more than 50000"
    patterns = [
        (r'>\s*(\d+)', 'gt'),
        (r'greater\s+than\s+(\d+)', 'gt'),
        (r'over\s+(\d+)', 'gt'),
        (r'above\s+(\d+)', 'gt'),
        (r'more\s+than\s+(\d+)', 'gt'),
        (r'<\s*(\d+)', 'lt'),
        (r'less\s+than\s+(\d+)', 'lt'),
        (r'under\s+(\d+)', 'lt'),
        (r'below\s+(\d+)', 'lt'),
    ]
    
    for pattern, op in patterns:
        match = re.search(pattern, query_lower)
        if match:
            return (op, float(match.group(1)))
    
    return (None, None)


def tool_executor_node(state: AgentState) -> dict:
    """Execute S/4HANA tools based on query."""
    print("  [Tools] Executing S/4HANA query...")
    
    # Strip whitespace and normalize
    query = state['messages'][-1].content.strip().lower()
    
    results = {}
    po_amount = None
    
    # Extract amount filter if present
    filter_op, filter_amount = extract_amount_filter(query)
    if filter_op:
        print(f"    Amount filter: {filter_op} ${filter_amount:,.0f}")
    
    # Extract PO number if present (flexible regex)
    po_match = re.search(r'(45\d{8})', query.replace(' ', ''))
    
    if po_match:
        po_number = po_match.group(1)
        print(f"    Found PO number: {po_number}")
        results = get_purchase_order.invoke({'po_number': po_number})
        po_amount = float(results.get('amount', 0) or 0)
    elif any(kw in query for kw in ['list', 'show', 'all', 'recent', 'order']):
        print("    Listing POs...")
        all_pos = list_purchase_orders.invoke({'count': 10})  # Fetch more to allow filtering
        
        # Apply amount filter if present
        if filter_op and isinstance(all_pos, list):
            if filter_op == 'gt':
                results = [po for po in all_pos if (po.get('amount') or 0) > filter_amount]
                print(f"    Filtered to {len(results)} POs with amount > ${filter_amount:,.0f}")
            elif filter_op == 'lt':
                results = [po for po in all_pos if (po.get('amount') or 0) < filter_amount]
                print(f"    Filtered to {len(results)} POs with amount < ${filter_amount:,.0f}")
        else:
            results = all_pos
    else:
        # Try to find any 10-digit number starting with 45
        any_po = re.search(r'45\d{8}', query.replace(' ', ''))
        if any_po:
            po_number = any_po.group(0)
            print(f"    Found PO number: {po_number}")
            results = get_purchase_order.invoke({'po_number': po_number})
            po_amount = float(results.get('amount', 0) or 0)
        else:
            results = {'message': 'No specific PO action identified. Try: "list purchase orders" or "show PO 4500000001"'}
    
    return {
        'tool_results': results,
        'po_amount': po_amount
    }


# --- 6.5 SAP BPA Client ---

class SAPBPAClient:
    """Client for SAP Build Process Automation API."""
    
    def __init__(self):
        self.api_url = os.getenv('BPA_API_URL')
        self.auth_url = os.getenv('BPA_AUTH_URL')
        self.client_id = os.getenv('BPA_CLIENT_ID')
        self.client_secret = os.getenv('BPA_CLIENT_SECRET')
        self.definition_id = os.getenv('BPA_DEFINITION_ID')
        self.token = None
    
    def get_token(self) -> str:
        """Get OAuth token from SAP BTP."""
        if self.token:
            return self.token
        
        print("    Getting BPA OAuth token...")
        
        token_url = f"{self.auth_url}/oauth/token"
        
        response = httpx.post(
            token_url,
            data={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30.0
        )
        
        if response.status_code == 200:
            self.token = response.json().get('access_token')
            print("    Token obtained successfully")
            return self.token
        else:
            raise Exception(f"Failed to get token: {response.status_code} - {response.text}")
    
    def determine_release_code(self, amount: float) -> str:
        """Determine approval level based on amount (SAP Release Strategy pattern)."""
        if amount < 10000:
            return 'auto'
        elif amount < 50000:
            return 'manager'
        elif amount < 100000:
            return 'director'
        elif amount < 500000:
            return 'vp'
        else:
            return 'cfo'
    
    def trigger_approval_workflow(self, po_data: dict) -> dict:
        """Trigger PO approval workflow in SAP BPA."""
        print("    Triggering SAP BPA workflow...")
        
        token = self.get_token()
        
        # Prepare workflow payload (lowercase property names as required by BPA)
        payload = {
            "definitionId": self.definition_id,
            "context": {
                "purchaseorder": po_data.get('po_number', ''),
                "netamount": float(po_data.get('amount', 0) or 0),
                "currency": po_data.get('currency', 'USD'),
                "vendor": po_data.get('vendor', ''),
                "vendorname": po_data.get('vendor_name', ''),
                "companycode": po_data.get('company_code', '1710'),
                "releasecode": self.determine_release_code(float(po_data.get('amount', 0) or 0)),
                "requestoremail": os.getenv('REQUESTOR_EMAIL', 'support3@manbitech.com')
            }
        }
        
        # Call BPA API to start workflow instance
        url = f"{self.api_url}/workflow/rest/v1/workflow-instances"
        
        response = httpx.post(
            url,
            json=payload,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            },
            timeout=30.0
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"    Workflow triggered! Instance ID: {result.get('id', 'N/A')}")
            return {
                'success': True,
                'instance_id': result.get('id'),
                'status': result.get('status'),
                'message': 'Approval request sent to SAP Build Process Automation'
            }
        else:
            print(f"    BPA API error: {response.status_code}")
            return {
                'success': False,
                'error': f"BPA API error: {response.status_code} - {response.text[:200]}"
            }


# Initialize BPA client
bpa_client = SAPBPAClient()


# --- 6.6 HITL Node ---

APPROVAL_THRESHOLD = float(os.getenv('HITL_APPROVAL_THRESHOLD', '50000'))


def hitl_check_node(state: AgentState) -> dict:
    """Check if human approval is required and trigger SAP BPA if needed."""
    print(f"  [HITL] Checking approval requirements (threshold: ${APPROVAL_THRESHOLD:,.0f})...")
    
    po_amount = state.get('po_amount', 0) or 0
    tool_results = state.get('tool_results', {})
    
    if po_amount > APPROVAL_THRESHOLD:
        print(f"    Amount ${po_amount:,.2f} exceeds threshold!")
        
        # Trigger SAP BPA workflow
        bpa_enabled = os.getenv('BPA_API_URL')
        
        if bpa_enabled and isinstance(tool_results, dict) and 'po_number' in tool_results:
            try:
                bpa_result = bpa_client.trigger_approval_workflow(tool_results)
                
                if bpa_result.get('success'):
                    return {
                        'requires_approval': True,
                        'approval_status': 'pending_bpa',
                        'approval_reason': f"PO amount ${po_amount:,.2f} exceeds threshold. {bpa_result.get('message')}. Instance ID: {bpa_result.get('instance_id')}"
                    }
                else:
                    return {
                        'requires_approval': True,
                        'approval_status': 'bpa_error',
                        'approval_reason': f"PO amount ${po_amount:,.2f} exceeds threshold. BPA trigger failed: {bpa_result.get('error')}"
                    }
            except Exception as e:
                print(f"    BPA error: {str(e)}")
                return {
                    'requires_approval': True,
                    'approval_status': 'bpa_error',
                    'approval_reason': f"PO amount ${po_amount:,.2f} exceeds threshold. Could not trigger BPA: {str(e)}"
                }
        else:
            # BPA not configured - fall back to manual flag
            return {
                'requires_approval': True,
                'approval_status': 'pending',
                'approval_reason': f'PO amount ${po_amount:,.2f} exceeds ${APPROVAL_THRESHOLD:,.0f} threshold (BPA not configured)'
            }
    
    print(f"    Amount ${po_amount:,.2f} within auto-approval limit")
    return {
        'requires_approval': False,
        'approval_status': 'auto_approved',
        'approval_reason': 'Amount within auto-approval limit'
    }


def should_wait_for_approval(state: AgentState) -> str:
    """Routing function for HITL."""
    if state.get('requires_approval', False):
        return 'wait_approval'
    return 'respond'


# --- 6.6 Response Node ---

def response_node(state: AgentState) -> dict:
    """Generate response based on gathered context."""
    print("  [Response] Generating answer...")
    
    parts = []
    
    if state.get('rag_context'):
        parts.append(f"Based on our procurement policies:\n\n{state['rag_context'][:500]}")
    
    if state.get('tool_results'):
        if isinstance(state['tool_results'], list):
            parts.append(f"Here are the Purchase Orders:\n{json.dumps(state['tool_results'], indent=2)}")
        elif isinstance(state['tool_results'], dict):
            if 'error' in state['tool_results']:
                parts.append(f"Error: {state['tool_results']['error']}")
            else:
                parts.append(f"Purchase Order Details:\n{json.dumps(state['tool_results'], indent=2)}")
    
    # Show approval status prominently for high-value POs
    if state.get('requires_approval'):
        approval_status = state.get('approval_status', 'pending')
        if approval_status == 'pending_bpa':
            parts.append(f"\n*** APPROVAL REQUIRED ***\n{state.get('approval_reason')}")
        elif approval_status == 'bpa_error':
            parts.append(f"\n*** APPROVAL REQUIRED (BPA Error) ***\n{state.get('approval_reason')}")
        else:
            parts.append(f"\n*** APPROVAL REQUIRED ***\n{state.get('approval_reason')}")
    elif state.get('approval_status') == 'auto_approved':
        po_amount = state.get('po_amount') or 0
        if po_amount > 0:
            parts.append(f"\nStatus: Auto-approved (amount ${po_amount:,.2f} within threshold)")
    
    if not parts:
        response = "I can help you with purchase orders and procurement policies. What would you like to know?"
    else:
        response = '\n\n'.join(parts)
    
    return {'messages': [AIMessage(content=response)]}


# ============================================
# PART 7: BUILD AGENT GRAPH
# ============================================

def build_procurement_agent():
    """Build the complete procurement agent graph."""
    print("\nBuilding agent graph...")
    
    # Create graph with our state
    workflow = StateGraph(AgentState)
    
    # Add all nodes
    workflow.add_node('guardrails', guardrails_node)
    workflow.add_node('router', router_node)
    workflow.add_node('rag', rag_node)
    workflow.add_node('tools', tool_executor_node)
    workflow.add_node('hitl', hitl_check_node)
    workflow.add_node('respond', response_node)
    
    # Set entry point
    workflow.set_entry_point('guardrails')
    
    # Add edges
    workflow.add_edge('guardrails', 'router')
    
    # Conditional routing from router
    workflow.add_conditional_edges(
        'router',
        route_by_intent,
        {
            'rag': 'rag',
            'tools': 'tools',
            'respond': 'respond'
        }
    )
    
    # RAG -> respond
    workflow.add_edge('rag', 'respond')
    
    # Tools -> HITL check
    workflow.add_edge('tools', 'hitl')
    
    # HITL conditional routing - always go through respond to show results
    workflow.add_conditional_edges(
        'hitl',
        should_wait_for_approval,
        {
            'respond': 'respond',
            'wait_approval': 'respond'  # Changed from END - show results before ending
        }
    )
    
    # Response ends the graph
    workflow.add_edge('respond', END)
    
    # Compile with memory
    memory = MemorySaver()
    agent = workflow.compile(checkpointer=memory)
    
    print("Agent graph built successfully")
    return agent


def print_graph_structure(agent):
    """Print the graph structure."""
    print("\n" + "=" * 50)
    print("AGENT GRAPH STRUCTURE")
    print("=" * 50)
    
    try:
        print(agent.get_graph().draw_ascii())
    except Exception as e:
        print(f"(ASCII drawing not available: {e})")
    
    print("\n" + "=" * 50)
    print("GRAPH COMPONENTS")
    print("=" * 50)
    
    graph = agent.get_graph()
    
    print("\nNODES:")
    for node in graph.nodes:
        print(f"  - {node}")
    
    print("\nEDGES:")
    for edge in graph.edges:
        print(f"  - {edge}")


def save_graph_image(agent, filename="procurement_agent_graph.png"):
    """Save workflow graph as PNG image."""
    print("\n" + "=" * 50)
    print("SAVING GRAPH IMAGE")
    print("=" * 50)
    
    try:
        image_bytes = agent.get_graph(xray=True).draw_mermaid_png()
        with open(filename, "wb") as f:
            f.write(image_bytes)
        print(f"  Workflow graph saved to {filename}")
    except Exception as e:
        print(f"  Could not generate workflow graph image: {e}")
        print("  Make sure 'grandalf' is installed: pip install grandalf")


def print_mermaid_code(agent):
    """Print Mermaid code for manual visualization."""
    print("\n" + "=" * 50)
    print("MERMAID DIAGRAM CODE")
    print("=" * 50)
    print("\nCopy to https://mermaid.live to visualize:\n")
    
    try:
        mermaid_code = agent.get_graph().draw_mermaid()
        print(mermaid_code)
    except Exception as e:
        print(f"(Mermaid generation not available: {e})")


# ============================================
# PART 8: RUN AGENT
# ============================================

def ask_agent(agent, query: str, thread_id: str = None):
    """Send a query to the agent and display the response."""
    if thread_id is None:
        thread_id = str(uuid.uuid4())
    
    config = {'configurable': {'thread_id': thread_id}}
    
    print("\n" + "=" * 60)
    print(f"USER: {query}")
    print("=" * 60)
    
    # Create initial state
    initial_state = {
        'messages': [HumanMessage(content=query)],
        'intent': None,
        'tool_results': None,
        'rag_context': None,
        'requires_approval': False,
        'approval_status': None,
        'approval_reason': None,
        'po_number': None,
        'po_amount': None
    }
    
    # Run agent
    result = agent.invoke(initial_state, config)
    
    # Display response
    print("\n" + "-" * 60)
    print("AGENT RESPONSE:")
    print("-" * 60)
    print(result['messages'][-1].content)
    
    return result, thread_id


def stream_agent(agent, query: str):
    """Stream agent execution showing each step."""
    print("\n" + "=" * 60)
    print(f"STREAMING: {query}")
    print("=" * 60)
    
    initial_state = {
        'messages': [HumanMessage(content=query)],
        'intent': None,
        'tool_results': None,
        'rag_context': None,
        'requires_approval': False,
        'approval_status': None,
        'approval_reason': None,
        'po_number': None,
        'po_amount': None
    }
    
    config = {'configurable': {'thread_id': str(uuid.uuid4())}}
    
    for event in agent.stream(initial_state, config):
        for node_name, node_output in event.items():
            print(f"\n>> NODE: {node_name}")
            
            if node_output is None:
                print("   Output: None")
                continue
            
            if isinstance(node_output, dict):
                print(f"   Keys: {list(node_output.keys())}")
                if 'intent' in node_output:
                    print(f"   Intent: {node_output['intent']}")
                if 'rag_context' in node_output and node_output['rag_context']:
                    print(f"   RAG context: {len(node_output['rag_context'])} chars")
                if 'requires_approval' in node_output:
                    print(f"   Requires approval: {node_output['requires_approval']}")


# ============================================
# PART 9: MAIN
# ============================================

def main():
    """Main entry point."""
    global vectorstore
    
    print("\n" + "=" * 60)
    print("LAB 11 UC1: LangGraph + SAP AI Core + S/4HANA")
    print("Production-Ready SAP Procurement Agent")
    print("=" * 60)
    
    # Verify environment
    if not verify_environment():
        print("\nPlease fix environment issues and try again.")
        return
    
    # Initialize RAG
    vectorstore = initialize_rag()
    
    # Build agent
    agent = build_procurement_agent()
    
    # Print graph structure
    print_graph_structure(agent)
    
    # Save graph as PNG image
    save_graph_image(agent, "procurement_agent_graph.png")
    
    # Print Mermaid code (optional - for manual visualization)
    print_mermaid_code(agent)
    
    # Run test queries
    print("\n" + "=" * 60)
    print("RUNNING TEST QUERIES")
    print("=" * 60)
    
    test_queries = [
        "What are the approval thresholds for purchase orders?",
        "What are the payment terms for vendors?",
        "Hello, what can you help me with?",
    ]
    
    for query in test_queries:
        ask_agent(agent, query)
        print()
    
    # Interactive mode
    print("\n" + "=" * 60)
    print("INTERACTIVE MODE")
    print("Type 'quit' to exit, 'stream' for streaming mode")
    print("=" * 60)
    
    thread_id = str(uuid.uuid4())
    streaming_mode = False
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("Goodbye!")
                break
            
            if user_input.lower() == 'stream':
                streaming_mode = not streaming_mode
                print(f"Streaming mode: {'ON' if streaming_mode else 'OFF'}")
                continue
            
            if streaming_mode:
                stream_agent(agent, user_input)
            else:
                _, thread_id = ask_agent(agent, user_input, thread_id)
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == '__main__':
    main()
