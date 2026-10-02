"""
S/4HANA OData Client
====================
Connects to S/4HANA On-Premise via OData API.
Fetches customer data for churn prediction.

Author: Srinivasa Dasari
Date: March 2026
"""

import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timezone
from typing import Dict, List, Optional
import random
import getpass
import os


class S4HANAConfig:
    """S/4HANA connection configuration."""
    
    def __init__(
        self,
        host: str,
        username: str,
        password: str
    ):
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.base_url = f"{self.host}/sap/opu/odata/sap"
    
    @classmethod
    def from_env(cls):
        """Create config from environment variables."""
        host = os.getenv('S4_HOST', 'http://mtsapserver3.themdlabs.com:8003')
        username = os.getenv('S4_USERNAME', 'sdasari')
        password = os.getenv('S4_PASSWORD')
        if not password:
            password = getpass.getpass("S/4HANA password: ")
        return cls(host, username, password)
    
    @classmethod
    def from_input(cls):
        """Create config from user input."""
        host = input("S/4HANA Host URL: ") or "http://mtsapserver3.themdlabs.com:8003"
        username = input("Username: ") or "sdasari"
        password = getpass.getpass("Password: ")
        return cls(host, username, password)


class S4HANAClient:
    """
    S/4HANA OData Client for Customer Data.
    
    Fetches:
    - Customer master data
    - Dunning information (payment behavior)
    - Sales area data
    """
    
    def __init__(self, config: S4HANAConfig):
        self.config = config
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(config.username, config.password)
        print("[OK] S/4HANA Client initialized")
        print(f"     Host: {config.host}")
        print(f"     User: {config.username}")
    
    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Execute GET request."""
        url = f"{self.config.base_url}/{endpoint}"
        default_params = {"$format": "json"}
        if params:
            default_params.update(params)
        
        response = self.session.get(url, params=default_params)
        response.raise_for_status()
        return response.json()
    
    def _parse_sap_date(self, sap_date: str) -> Optional[datetime]:
        """Parse SAP OData date format: /Date(1234567890000)/"""
        if not sap_date:
            return None
        try:
            # Extract milliseconds from /Date(xxxxx)/
            ms = int(sap_date.replace("/Date(", "").replace(")/", ""))
            return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        except:
            return None
    
    def _calculate_tenure_months(self, creation_date: str) -> int:
        """Calculate tenure in months from creation date."""
        created = self._parse_sap_date(creation_date)
        if not created:
            return 12  # Default
        
        now = datetime.now(timezone.utc)
        months = (now.year - created.year) * 12 + (now.month - created.month)
        return max(1, months)
    
    def get_customers(self, top: int = 100) -> List[dict]:
        """Fetch customer list."""
        data = self._get(
            "API_BUSINESS_PARTNER/A_Customer",
            {"$top": str(top)}
        )
        return data.get("d", {}).get("results", [])
    
    def get_customer_detail(self, customer_id: str) -> Optional[dict]:
        """Fetch single customer with details."""
        try:
            data = self._get(
                f"API_BUSINESS_PARTNER/A_Customer('{customer_id}')"
            )
            return data.get("d", {})
        except:
            return None
    
    def get_customer_dunning(self, customer_id: str) -> List[dict]:
        """Fetch dunning data (payment behavior)."""
        try:
            data = self._get(
                f"API_BUSINESS_PARTNER/A_CustomerDunning",
                {"$filter": f"Customer eq '{customer_id}'"}
            )
            return data.get("d", {}).get("results", [])
        except:
            return []
    
    def get_customer_sales_area(self, customer_id: str) -> List[dict]:
        """Fetch sales area data."""
        try:
            data = self._get(
                f"API_BUSINESS_PARTNER/A_CustomerSalesArea",
                {"$filter": f"Customer eq '{customer_id}'"}
            )
            return data.get("d", {}).get("results", [])
        except:
            return []
    
    def get_customer_for_churn(self, customer_id: str) -> Optional[dict]:
        """
        Fetch customer data formatted for churn model.
        
        Combines:
        - Master data (name, industry, tenure)
        - Dunning data (payment behavior)
        - Sales area (account manager)
        - Simulated data (fields not in S/4HANA)
        """
        # Fetch base customer data
        customer = self.get_customer_detail(customer_id)
        if not customer:
            return None
        
        # Fetch additional data
        dunning = self.get_customer_dunning(customer_id)
        sales_area = self.get_customer_sales_area(customer_id)
        
        # Calculate tenure
        tenure = self._calculate_tenure_months(customer.get("CreationDate"))
        
        # Check for payment issues (dunning)
        has_dunning = len(dunning) > 0
        dunning_level = 0
        if has_dunning and dunning[0].get("DunningLevel"):
            try:
                dunning_level = int(dunning[0].get("DunningLevel", 0))
            except:
                dunning_level = 0
        
        # Get industry from customer or BP
        industry = customer.get("IndustrySector") or "General"
        if industry == "N/A" or not industry.strip():
            industry = "General"
        
        # Simulated data (not available in BP API)
        # In production, this would come from other systems
        simulated = self._generate_simulated_data(tenure, has_dunning, dunning_level)
        
        return {
            # Real S/4HANA data
            "customer_id": customer_id,
            "customer_name": customer.get("CustomerName", f"Customer {customer_id}"),
            "industry": industry,
            "tenure_months": tenure,
            "creation_date": customer.get("CreationDate"),
            "has_dunning_record": has_dunning,
            "dunning_level": dunning_level,
            "sales_areas": len(sales_area),
            
            # Account manager (from sales area or simulated)
            "account_manager": self._get_account_manager(sales_area),
            
            # Simulated data (would come from other systems)
            "monthly_spend": simulated["monthly_spend"],
            "support_tickets": simulated["support_tickets"],
            "contract_type": simulated["contract_type"],
            "product_usage": simulated["product_usage"],
            "nps_score": simulated["nps_score"],
            "late_payments": simulated["late_payments"],
            
            # Source tracking
            "data_source": "S/4HANA + Simulated"
        }
    
    def _get_account_manager(self, sales_areas: List[dict]) -> str:
        """Extract or generate account manager name."""
        # In real system, this would come from partner function
        managers = [
            "John Smith", "Sarah Johnson", "Mike Chen", 
            "Lisa Wong", "David Lee", "Emily Brown"
        ]
        return random.choice(managers)
    
    def _generate_simulated_data(
        self, 
        tenure: int, 
        has_dunning: bool,
        dunning_level: int
    ) -> dict:
        """
        Generate simulated data for fields not in S/4HANA BP API.
        
        In production, these would come from:
        - Support tickets: ServiceNow, SAP CRM
        - Product usage: Application logs, telemetry
        - NPS score: Survey systems (Qualtrics, etc.)
        - Monthly spend: SD/FI modules
        """
        
        # Base risk from dunning
        base_risk = 0.3 if has_dunning else 0.1
        base_risk += dunning_level * 0.1
        
        # Tenure affects risk (newer = higher risk)
        if tenure < 6:
            base_risk += 0.2
        elif tenure < 12:
            base_risk += 0.1
        
        # Generate correlated simulated data
        is_high_risk = random.random() < base_risk
        
        if is_high_risk:
            return {
                "monthly_spend": round(random.uniform(100, 400), 2),
                "support_tickets": random.randint(5, 15),
                "contract_type": random.choice(["monthly", "monthly", "annual"]),
                "product_usage": random.choice(["declining", "declining", "stable"]),
                "nps_score": random.randint(3, 6),
                "late_payments": random.randint(1, 4)
            }
        else:
            return {
                "monthly_spend": round(random.uniform(500, 2000), 2),
                "support_tickets": random.randint(0, 4),
                "contract_type": random.choice(["annual", "annual", "multi-year"]),
                "product_usage": random.choice(["stable", "growing", "growing"]),
                "nps_score": random.randint(7, 10),
                "late_payments": 0
            }
    
    def get_customers_for_churn(self, customer_ids: List[str] = None, top: int = 10) -> List[dict]:
        """
        Fetch multiple customers formatted for churn model.
        
        Args:
            customer_ids: Specific IDs to fetch, or None for top N
            top: Number of customers if no IDs specified
        """
        if customer_ids:
            customers = []
            for cid in customer_ids:
                customer = self.get_customer_for_churn(cid)
                if customer:
                    customers.append(customer)
            return customers
        else:
            # Fetch top N customers
            raw_customers = self.get_customers(top)
            customers = []
            for raw in raw_customers:
                cid = raw.get("Customer")
                if cid:
                    customer = self.get_customer_for_churn(cid)
                    if customer:
                        customers.append(customer)
            return customers


def run_demo():
    """Demo: Fetch S/4HANA customers for churn analysis."""
    print("=" * 60)
    print(" S/4HANA CLIENT - Customer Data Demo")
    print("=" * 60)
    
    # Initialize client
    config = S4HANAConfig(
        host="http://mtsapserver3.themdlabs.com:8003",
        username="sdasari",
        password=getpass.getpass("Enter S/4HANA password: ")
    )
    
    client = S4HANAClient(config)
    
    # Fetch customers
    print("\n[INFO] Fetching customers from S/4HANA...")
    customers = client.get_customers_for_churn(top=5)
    
    print(f"\n[OK] Retrieved {len(customers)} customers\n")
    
    for c in customers:
        print("-" * 60)
        print(f"[CUSTOMER] {c['customer_id']}: {c['customer_name']}")
        print("-" * 60)
        print(f"  Industry:        {c['industry']}")
        print(f"  Tenure:          {c['tenure_months']} months")
        print(f"  Account Manager: {c['account_manager']}")
        print(f"  Has Dunning:     {c['has_dunning_record']}")
        print(f"  Dunning Level:   {c['dunning_level']}")
        print("")
        print("  [Simulated Data]")
        print(f"  Monthly Spend:   ${c['monthly_spend']}")
        print(f"  Support Tickets: {c['support_tickets']}")
        print(f"  Contract Type:   {c['contract_type']}")
        print(f"  Product Usage:   {c['product_usage']}")
        print(f"  NPS Score:       {c['nps_score']}/10")
        print(f"  Late Payments:   {c['late_payments']}")
        print("")
    
    print("=" * 60)
    print("[DONE] S/4HANA data fetch complete")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()