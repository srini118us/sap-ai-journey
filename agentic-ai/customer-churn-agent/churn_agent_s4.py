"""
Churn Prevention Agent with S/4HANA Integration
"""
import getpass
from typing import Dict
from dotenv import load_dotenv

load_dotenv()


class ChurnPredictor:
    def predict(self, customer: Dict) -> Dict:
        risk_score = 0.0
        risk_factors = []
        
        tenure = customer.get("tenure_months", 12)
        if tenure < 6:
            risk_score += 0.25
            risk_factors.append(f"Very new customer ({tenure} months)")
        elif tenure < 12:
            risk_score += 0.15
            risk_factors.append(f"Relatively new customer ({tenure} months)")
        
        spend = customer.get("monthly_spend", 500)
        if spend < 200:
            risk_score += 0.20
            risk_factors.append(f"Low monthly spend (${spend:.2f})")
        elif spend < 400:
            risk_score += 0.10
            risk_factors.append(f"Below average spend (${spend:.2f})")
        
        tickets = customer.get("support_tickets", 0)
        if tickets > 8:
            risk_score += 0.20
            risk_factors.append(f"High support tickets ({tickets})")
        elif tickets > 5:
            risk_score += 0.10
            risk_factors.append(f"Elevated support tickets ({tickets})")
        
        contract = customer.get("contract_type", "annual")
        if contract == "monthly":
            risk_score += 0.15
            risk_factors.append("Monthly contract (no commitment)")
        
        usage = customer.get("product_usage", "stable")
        if usage == "declining":
            risk_score += 0.15
            risk_factors.append("Declining product usage")
        
        nps = customer.get("nps_score", 7)
        if nps < 5:
            risk_score += 0.15
            risk_factors.append(f"Low NPS score ({nps}/10)")
        elif nps < 7:
            risk_score += 0.05
            risk_factors.append(f"Below average NPS ({nps}/10)")
        
        late = customer.get("late_payments", 0)
        dunning = customer.get("dunning_level", 0)
        if late > 0 or dunning > 0:
            risk_score += 0.15
            risk_factors.append(f"Payment issues (dunning level: {dunning})")
        
        churn_probability = min(0.95, risk_score)
        
        if churn_probability >= 0.6:
            risk_level = "HIGH"
        elif churn_probability >= 0.3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "churn_probability": round(churn_probability * 100),
            "risk_level": risk_level,
            "risk_factors": risk_factors
        }


def run_demo():
    from s4hana_client import S4HANAClient, S4HANAConfig
    from genai_client import GenAIHubClient, GenAIConfig
    
    print("=" * 60)
    print(" CHURN PREVENTION AGENT - S/4HANA Integration")
    print("=" * 60)
    
    # S/4HANA connection
    print("\n[INIT] Connecting to S/4HANA...")
    s4_config = S4HANAConfig(
        host="http://mtsapserver3.themdlabs.com:8003",
        username="sdasari",
        password=getpass.getpass("Enter S/4HANA password: ")
    )
    s4_client = S4HANAClient(s4_config)
    
    # GenAI Hub connection
    print("\n[INIT] Connecting to GenAI Hub...")
    llm_client = None
    try:
        genai_config = GenAIConfig.from_env()
        llm_client = GenAIHubClient(genai_config)
        print("[OK] GenAI Hub connected")
    except Exception as e:
        print(f"[WARN] GenAI Hub not available: {e}")
    
    predictor = ChurnPredictor()
    
    # Fetch customers
    print("\n[INFO] Fetching customers from S/4HANA...")
    customers = s4_client.get_customers_for_churn(top=5)
    print(f"[OK] Retrieved {len(customers)} customers")
    
    high_risk_count = 0
    
    for i, customer in enumerate(customers, 1):
        cust_id = customer.get("customer_id", "Unknown")
        cust_name = customer.get("customer_name", "Unknown")
        
        print("\n" + "=" * 60)
        print(f" CUSTOMER {i}/{len(customers)}: {cust_id} - {cust_name}")
        print("=" * 60)
        
        print("\n[CUSTOMER DATA]")
        print(f"  Industry: {customer.get('industry', 'N/A')}")
        print(f"  Tenure: {customer.get('tenure_months', 'N/A')} months")
        print(f"  Account Manager: {customer.get('account_manager', 'N/A')}")
        print(f"  Monthly Spend: ${customer.get('monthly_spend', 0):.2f}")
        print(f"  Support Tickets: {customer.get('support_tickets', 0)}")
        print(f"  Contract Type: {customer.get('contract_type', 'N/A')}")
        print(f"  NPS Score: {customer.get('nps_score', 'N/A')}/10")
        print(f"  Dunning Level: {customer.get('dunning_level', 0)}")
        
        prediction = predictor.predict(customer)
        
        print(f"\n[ML PREDICTION]")
        print(f"  Churn Probability: {prediction['churn_probability']}%")
        print(f"  Risk Level: {prediction['risk_level']}")
        
        if prediction["risk_factors"]:
            print(f"  Risk Factors:")
            for factor in prediction["risk_factors"]:
                print(f"    - {factor}")
        else:
            print(f"  Risk Factors: None (healthy customer)")
        
        if prediction["risk_level"] in ["HIGH", "MEDIUM"] and llm_client:
            print(f"\n[LLM ANALYSIS]")
            
            prompt = f"""Analyze this customer's churn risk in 2-3 sentences:
Customer: {cust_name}
Industry: {customer.get('industry')}
Tenure: {customer.get('tenure_months')} months
Risk: {prediction['churn_probability']}%
Factors: {', '.join(prediction['risk_factors'])}"""

            explanation = llm_client.chat(prompt, temperature=0.3, max_tokens=150)
            print(f"  {explanation}")
            
            print(f"\n[RECOMMENDATIONS]")
            rec_prompt = f"""Give 3 brief retention actions for {cust_name}:
1. Immediate:
2. Short-term:
3. Long-term:"""
            
            recommendations = llm_client.chat(rec_prompt, temperature=0.5, max_tokens=200)
            print(recommendations)
            
            if prediction["risk_level"] == "HIGH":
                print(f"\n[DRAFT EMAIL]")
                print("-" * 40)
                email_prompt = f"""Draft a 50-word retention email to {cust_name} from {customer.get('account_manager')}. 
Be helpful, don't mention churn."""
                email = llm_client.chat(email_prompt, temperature=0.6, max_tokens=150)
                print(email)
                print("-" * 40)
        
        if prediction["risk_level"] == "HIGH":
            high_risk_count += 1
        
        input("\nPress Enter for next customer...")
    
    print("\n" + "=" * 60)
    print(" SUMMARY")
    print("=" * 60)
    print(f"  Total Analyzed: {len(customers)}")
    print(f"  High Risk: {high_risk_count}")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()