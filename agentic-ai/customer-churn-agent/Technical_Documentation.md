# SAP AI Core Mega Lab - Technical Documentation

## System Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Customer Data  │───▶│  ML Prediction   │───▶│  LLM Analysis   │───▶│ Recommendations │
│ Source        │    │  Engine         │    │  Engine         │    │  Engine        │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │                       │
        ▼                       ▼                       ▼                       ▼
   Customer Profiles         Churn Scores           Explanations           Action Plans
```

---

## Code Architecture Breakdown

### 1. Core Components

#### A. GenAI Hub Client (`genai_client.py`)

**Class Structure:**
```python
@dataclass
class GenAIConfig:
    ai_api_url: str              # SAP AI Core API endpoint
    auth_url: str               # OAuth authentication URL  
    client_id: str              # Application client ID
    client_secret: str            # Application client secret
    resource_group: str = "default"     # Resource group
    orchestration_deployment_id: str  # Orchestration deployment ID

class GenAIHubClient:
    - OAuth token management with auto-refresh
    - Orchestration API integration
    - Template-based LLM prompting
    - Error handling and retry logic
```

**Key Methods:**
```python
def _get_token(self) -> str:
    """
    Implements OAuth 2.0 client credentials flow
    Auto-refreshes tokens before expiration
    Caches token for performance
    """

def _get_headers(self) -> Dict[str, str]:
    """
    Builds authenticated request headers
    Includes Bearer token and resource group
    """

def chat(self, message: str, **kwargs) -> str:
    """
    Sends orchestrated requests to SAP AI Core
    Uses template-based prompting with variables
    Returns LLM-generated responses
    """
```

#### B. Churn Agent (`churn_agent.py`)

**Main Classes:**
```python
class Customer:
    - Customer profile and demographic data
    - Usage history and engagement metrics
    - Support ticket history

class ChurnPredictor:
    - Machine learning churn prediction
    - Risk factor analysis
    - Probability calculation

class RetentionAgent:
    - LLM-powered analysis engine
    - Recommendation generation
    - Communication template creation
```

---

## Data Flow Architecture

### 1. Data Ingestion Layer
```python
# Customer Data Input
customer_data = {
    "customer_id": "CUST-1002",
    "name": "TechStart Inc.",
    "industry": "Technology", 
    "tenure_months": 24,
    "monthly_spend": 850.00,
    "support_tickets": 2,
    "nps_score": 8,
    "payment_history": "on_time",
    "product_usage": "moderate"
}

# Data Validation
def validate_customer_data(data):
    - Checks required fields
    - Validates data types
    - Ensures business logic consistency
```

### 2. Machine Learning Pipeline
```python
# Feature Engineering
features = extract_features(customer_data):
    - Tenure-based features
    - Spending patterns
    - Engagement metrics
    - Support interaction frequency
    - Payment reliability

# Risk Prediction
churn_probability = predict_churn(features):
    - Logistic regression model
    - Random forest ensemble
    - Feature importance analysis
    - Confidence interval calculation

# Risk Categorization  
risk_level = categorize_risk(churn_probability):
    - LOW: 0-20% probability
    - MEDIUM: 21-50% probability
    - HIGH: 51-80% probability
    - CRITICAL: 81-100% probability
```

### 3. LLM Integration Layer
```python
# Orchestration Payload Structure
orchestration_payload = {
    "orchestration_config": {
        "module_configurations": {
            "templating_module_config": {
                "template": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "{{user_message}}"}
                ]
            },
            "llm_module_config": {
                "model_name": "gpt-4.1-mini",
                "model_params": {
                    "max_tokens": 1000,
                    "temperature": 0.7
                }
            }
        }
    },
    "input_params": {
        "user_message": dynamic_content
    }
}

# Prompt Engineering Strategy
def build_analysis_prompt(customer_data, ml_results):
    - Context: Customer profile and business context
    - Task: Analyze churn risk factors
    - Format: Structured JSON response
    - Constraints: Business-focused language
```

---

## Implementation Details

### 1. Authentication Flow
```python
# OAuth 2.0 Client Credentials Flow
def authentication_flow():
    """
    Step 1: Request token with client credentials
    Step 2: Cache token with expiration time
    Step 3: Auto-refresh before expiration
    Step 4: Include Bearer token in API calls
    """
    
# Token Management
token_response = requests.post(auth_url, data={
    "grant_type": "client_credentials",
    "client_id": client_id,
    "client_secret": client_secret
})

access_token = token_response.json()["access_token"]
expires_in = token_response.json()["expires_in"]
token_expires = datetime.now() + timedelta(seconds=expires_in)
```

### 2. Error Handling Strategy
```python
# Multi-Level Error Handling
try:
    # API call
    response = make_api_request()
except requests.exceptions.ConnectionError:
    handle_network_error()
except requests.exceptions.Timeout:
    handle_timeout_error()  
except requests.exceptions.HTTPError as e:
    handle_http_error(e)
except Exception as e:
    handle_generic_error(e)

# Retry Logic
def with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
```

### 3. State Management
```python
# Application State
class ApplicationState:
    def __init__(self):
        self.current_customer = None
        self.analysis_results = {}
        self.llm_responses = {}
        self.recommendations = []
    
    def update_customer(self, customer_data):
        self.current_customer = Customer(**customer_data)
        
    def add_analysis_result(self, key, value):
        self.analysis_results[key] = value
        
    def generate_recommendations(self):
        # Combines ML and LLM insights
        return self.recommendation_engine.generate(
            self.current_customer,
            self.analysis_results
        )
```

---

## API Integration Patterns

### 1. SAP AI Core Orchestration API
```python
# Endpoint Structure
POST /v2/inference/deployments/{deployment_id}/completion

# Request Headers
headers = {
    "Authorization": f"Bearer {token}",
    "AI-Resource-Group": resource_group,
    "Content-Type": "application/json"
}

# Response Processing
response = requests.post(url, headers=headers, json=payload)
result = response.json()["module_results"]["llm"]["choices"][0]["message"]["content"]
```

### 2. Template System
```python
# Dynamic Template Variables
template_variables = {
    "customer_name": customer.name,
    "churn_probability": ml_results.probability,
    "risk_factors": ml_results.factors,
    "industry": customer.industry,
    "monthly_spend": customer.monthly_spend,
    "recommendation_type": "retention_strategy"
}

# Template Resolution
resolved_template = resolve_template(template, variables)
# Replaces {{customer_name}}, {{churn_probability}}, etc.
```

---

## Data Structures

### 1. Customer Data Model
```python
@dataclass
class Customer:
    customer_id: str              # Unique identifier
    name: str                    # Company name
    industry: str                 # Industry sector
    tenure_months: int             # Customer lifetime
    monthly_spend: float          # Monthly revenue
    support_tickets: int           # Support interactions
    nps_score: int              # Satisfaction score
    payment_history: str          # Payment reliability
    product_usage: str           # Usage patterns
```

### 2. ML Results Model
```python
@dataclass
class ChurnAnalysis:
    probability: float            # Churn probability (0-1)
    risk_level: str              # LOW/MEDIUM/HIGH/CRITICAL
    risk_factors: List[str]       # Identified risk factors
    confidence_interval: tuple    # Statistical confidence
    feature_importance: dict     # Key predictive features
```

### 3. LLM Response Model
```python
@dataclass  
class LLMAnalysis:
    explanation: str             # Why customer might churn
    insights: List[str]          # Key business insights
    recommendations: List[str]    # Actionable suggestions
    confidence_score: float       # Analysis confidence
    next_steps: List[str]        # Recommended actions
```

---

## Configuration Management

### 1. Environment Variables
```bash
# Required Configuration
AI_API_URL=https://ai.api.sap.com/v2
AUTH_URL=https://oauth.accounts.sap.com  
CLIENT_ID=your_application_id
CLIENT_SECRET=your_client_secret
RESOURCE_GROUP=default
ORCH_DEPLOYMENT_ID=orchestration_deployment_id

# Optional Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
MAX_RETRIES=3                     # API retry attempts
TIMEOUT_SECONDS=30                  # Request timeout
CACHE_ENABLED=true                  # Enable token caching
```

### 2. Runtime Configuration
```python
# Model Parameters
model_config = {
    "model_name": "gpt-4.1-mini",     # LLM model
    "max_tokens": 1000,                # Response length
    "temperature": 0.7,                # Creativity level
    "top_p": 0.9,                    # Nucleus sampling
}

# Application Settings  
app_config = {
    "mock_mode": False,                  # Use mock LLM
    "batch_size": 1,                     # Customers per batch
    "output_format": "detailed",          # Output verbosity
    "save_results": True                 # Persist results
}
```

---

## Performance Optimization

### 1. Caching Strategy
```python
# Token Caching
class TokenCache:
    def __init__(self):
        self.token = None
        self.expires_at = None
        
    def get_valid_token(self):
        if self.is_valid():
            return self.token
        return self.refresh_token()
        
    def is_valid(self):
        return datetime.now() < self.expires_at - timedelta(minutes=5)

# Response Caching
class ResponseCache:
    def cache_analysis(self, customer_id, result):
        # Cache ML predictions for 1 hour
        # Cache LLM responses for 30 minutes
        # Reduces API calls and improves performance
```

### 2. Concurrent Processing
```python
# Async Processing (Future Enhancement)
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_customers_batch(customers):
    tasks = []
    for customer in customers:
        task = asyncio.create_task(analyze_customer(customer))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results

# Thread Pool (Current Implementation)
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = []
    for customer in customers:
        future = executor.submit(analyze_customer, customer)
        futures.append(future)
    
    results = [future.result() for future in futures]
```

---

## Security Implementation

### 1. Authentication Security
```python
# Secure Credential Storage
def load_config():
    """Load configuration from environment variables only"""
    return GenAIConfig.from_env()  # Never hardcode credentials

# Token Security
def secure_token_storage():
    """Store tokens in memory only"""
    # No file system storage
    # Auto-expiration handling
    # Secure transmission only
```

### 2. Data Privacy
```python
# Data Anonymization
def anonymize_customer_data(data):
    """Remove PII for logging/monitoring"""
    return {
        "customer_id": hash(data.customer_id),
        "name": mask_company_name(data.name),
        # Remove sensitive financial details
        "spend_category": categorize_spend(data.monthly_spend)
    }

# Audit Logging
def log_analysis_event(customer_id, event_type, metadata):
    """Security audit trail"""
    audit_log = {
        "timestamp": datetime.now().isoformat(),
        "customer_id": hash(customer_id),  # Anonymized
        "event_type": event_type,
        "metadata": metadata,
        "user_context": get_user_context()
    }
    write_audit_log(audit_log)
```

---

## Testing Strategy

### 1. Unit Testing
```python
# Component Isolation
class TestGenAIClient(unittest.TestCase):
    def test_token_retrieval(self):
        # Test OAuth flow
        # Mock token endpoint
        
    def test_api_call(self):
        # Test LLM integration
        # Mock API responses

class TestChurnPredictor(unittest.TestCase):
    def test_prediction_accuracy(self):
        # Test ML model
        # Known inputs/outputs
        
class TestRetentionAgent(unittest.TestCase):
    def test_recommendation_generation(self):
        # Test end-to-end workflow
        # Mock LLM responses
```

### 2. Integration Testing
```python
# Mock Mode Testing
def run_mock_tests():
    """Test full workflow without external dependencies"""
    test_customer = create_test_customer()
    result = churn_agent.analyze_customer(test_customer)
    assert result.recommendations is not None
    assert result.ml_results.probability >= 0

# API Integration Testing  
def run_integration_tests():
    """Test with actual SAP AI Core"""
    # Requires valid credentials
    # Tests real API responses
    # Validates authentication flow
```

### 3. Performance Testing
```python
# Load Testing
def performance_test(customer_count=100):
    """Test system under load"""
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(analyze_customer, customer)
            for customer in generate_test_customers(customer_count)
        ]
        results = [future.result() for future in futures]
    
    end_time = time.time()
    print(f"Processed {customer_count} customers in {end_time - start_time:.2f} seconds")
    print(f"Average time per customer: {(end_time - start_time) / customer_count:.3f} seconds")
```

---

## Deployment Considerations

### 1. Environment Setup
```bash
# Production Deployment
docker build -t mega-lab:latest .
docker run -d \
  --env-file .env \
  --name mega-lab-prod \
  mega-lab:latest

# Kubernetes Deployment (SAP AI Core)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mega-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mega-lab
  template:
    metadata:
      labels:
        app: mega-lab
    spec:
      containers:
      - name: mega-lab
        image: mega-lab:latest
        env:
        - name: AI_API_URL
          valueFrom:
            secretKeyRef:
              name: ai-core-credentials
              key: api-url
```

### 2. Monitoring & Observability
```python
# Health Checks
def health_check():
    """System health monitoring"""
    return {
        "api_status": check_ai_core_connection(),
        "ml_model_status": check_ml_model(),
        "database_status": check_database(),
        "memory_usage": get_memory_usage(),
        "response_time": get_average_response_time()
    }

# Metrics Collection
def collect_metrics():
    """Business and technical metrics"""
    return {
        "customers_analyzed": get_customer_count(),
        "predictions_made": get_prediction_count(),
        "llm_calls_made": get_llm_call_count(),
        "error_rate": get_error_rate(),
        "average_response_time": get_avg_response_time()
    }
```

---

## Troubleshooting Guide

### 1. Common Issues
```python
# Authentication Issues
if response.status_code == 401:
    print("❌ Invalid credentials - Check CLIENT_ID and CLIENT_SECRET")
    
if response.status_code == 403:
    print("❌ Access denied - Check RESOURCE_GROUP permissions")

# API Issues  
if response.status_code == 429:
    print("⚠️ Rate limited - Implement retry logic")
    
if response.status_code >= 500:
    print("🔥 Server error - Check SAP AI Core status")
```

### 2. Debug Tools
```python
# Debug Mode
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

if DEBUG:
    print("🐛 Debug mode enabled")
    print(f"API URL: {config.ai_api_url}")
    print(f"Customer data: {customer_data}")
    print(f"ML results: {ml_results}")
    print(f"LLM prompt: {prompt}")
    print(f"LLM response: {response}")

# Logging Configuration
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mega-lab.log'),
        logging.StreamHandler()
    ]
)
```

---

## Future Architecture Enhancements

### 1. Microservices Pattern
```python
# Service Decomposition
class CustomerService:
    """Customer data management"""
    
class MLEngine:
    """Machine learning predictions"""
    
class LLMService:  
    """Large language model integration"""
    
class RecommendationEngine:
    """Business rule engine"""
```

### 2. Event-Driven Architecture
```python
# Event Streaming
import asyncio
from kafka import KafkaProducer

async def process_customer_events():
    """Real-time customer event processing"""
    consumer = KafkaConsumer('customer-events')
    
    async for event in consumer:
        if event.type == 'CHURN_RISK_UPDATE':
            await update_risk_analysis(event.customer_id)
        elif event.type == 'CUSTOMER_SUPPORT_TICKET':
            await trigger_retention_workflow(event.customer_id)
```

---

## Conclusion

This technical documentation provides a comprehensive view of the Mega Lab's internal architecture, data flows, and implementation patterns. The system demonstrates enterprise-grade AI integration with robust error handling, security considerations, and scalable design patterns.

**Key Technical Achievements:**
- ✅ Modular architecture with clear separation of concerns
- ✅ Production-ready authentication and security
- ✅ Scalable data processing pipelines  
- ✅ Comprehensive error handling and monitoring
- ✅ Flexible configuration management
- ✅ Testable and maintainable code structure

The implementation showcases best practices for SAP AI Core integration and enterprise AI application development.
