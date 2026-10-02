"""
Email Classifier
================
Part 4 of MEGA LAB: Intelligent Email Classification

Uses SAP GenAI Hub to classify and draft responses.

Author: Srinivasa Dasari
Date: March 2026
"""

import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from genai_client import GenAIHubClient, GenAIConfig

load_dotenv()


# Sample emails for classification
SAMPLE_EMAILS = [
    {
        "id": "email_001",
        "from": "john.smith@acme.com",
        "subject": "Urgent: System down - need immediate help",
        "body": """Hi Support,

Our SAP S/4HANA system has been down for the past 2 hours. 
We cannot process any sales orders and this is affecting our operations.
Please escalate this immediately.

Regards,
John Smith
IT Manager, Acme Corp"""
    },
    {
        "id": "email_002",
        "from": "sarah.jones@techstart.com",
        "subject": "Question about API integration",
        "body": """Hello,

I'm trying to integrate our application with SAP using REST APIs.
Can you point me to the documentation for authentication?
Also, what are the rate limits for the API calls?

Thanks,
Sarah Jones
Developer, TechStart Inc"""
    },
    {
        "id": "email_003",
        "from": "mike.chen@globalretail.com",
        "subject": "Feature request: Bulk export functionality",
        "body": """Hi Team,

We love using the platform but would like to request a new feature.
Currently we can only export records one at a time. It would be great
if we could select multiple records and export them in bulk as CSV.

This would save us hours of manual work each week.

Best,
Mike Chen
Operations Manager"""
    },
    {
        "id": "email_004",
        "from": "lisa.wong@healthcare.com",
        "subject": "Invoice discrepancy - Account #12345",
        "body": """Dear Billing Team,

I noticed a discrepancy in our latest invoice (INV-2026-0342).
We were charged $2,500 but our contract states $2,000/month.
Please review and issue a corrected invoice.

I've attached the contract for reference.

Lisa Wong
Finance Director, HealthCare Plus"""
    },
    {
        "id": "email_005",
        "from": "david.lee@partner.com",
        "subject": "Partnership opportunity discussion",
        "body": """Hi,

I'm reaching out from TechPartners Inc. We specialize in SAP implementations
and would like to explore a potential partnership opportunity.

Would you be available for a call next week to discuss how we might
collaborate on enterprise projects?

Best regards,
David Lee
Business Development Manager"""
    }
]

# Classification categories
CATEGORIES = {
    "URGENT_SUPPORT": "Critical system issues requiring immediate attention",
    "TECHNICAL_QUESTION": "Technical queries about APIs, integration, configuration",
    "FEATURE_REQUEST": "Requests for new features or enhancements",
    "BILLING_INQUIRY": "Questions about invoices, payments, pricing",
    "PARTNERSHIP": "Business development and partnership inquiries",
    "GENERAL_INQUIRY": "Other general questions"
}


class EmailClassifier:
    """
    Intelligent email classifier using SAP GenAI Hub.
    
    Capabilities:
    1. Classify emails into predefined categories
    2. Extract key information (urgency, sentiment, entities)
    3. Generate draft responses
    """
    
    def __init__(self):
        config = GenAIConfig.from_env()
        self.client = GenAIHubClient(config)
        print("[OK] Email Classifier initialized")
    
    def classify(self, email: Dict) -> Dict:
        """Classify an email into a category."""
        
        categories_text = "\n".join([
            f"- {cat}: {desc}" for cat, desc in CATEGORIES.items()
        ])
        
        prompt = f"""Classify this email into ONE of these categories:

{categories_text}

EMAIL:
From: {email['from']}
Subject: {email['subject']}
Body: {email['body']}

Respond with ONLY the category name (e.g., URGENT_SUPPORT), nothing else."""

        response = self.client.chat(
            message=prompt,
            temperature=0,
            max_tokens=50
        )
        
        # Extract category from response
        category = response.strip().upper().replace(" ", "_")
        
        # Validate category
        if category not in CATEGORIES:
            category = "GENERAL_INQUIRY"
        
        return category
    
    def analyze(self, email: Dict) -> Dict:
        """Full analysis: classify, extract info, assess urgency."""
        
        prompt = f"""Analyze this email and provide a structured assessment:

EMAIL:
From: {email['from']}
Subject: {email['subject']}
Body: {email['body']}

Provide your analysis in this exact format:
CATEGORY: [one of: URGENT_SUPPORT, TECHNICAL_QUESTION, FEATURE_REQUEST, BILLING_INQUIRY, PARTNERSHIP, GENERAL_INQUIRY]
URGENCY: [HIGH/MEDIUM/LOW]
SENTIMENT: [POSITIVE/NEUTRAL/NEGATIVE/FRUSTRATED]
KEY_POINTS: [bullet points of main points]
SUGGESTED_ACTION: [what should be done]"""

        response = self.client.chat(
            message=prompt,
            temperature=0.2,
            max_tokens=400
        )
        
        return {
            "email_id": email["id"],
            "from": email["from"],
            "subject": email["subject"],
            "analysis": response
        }
    
    def draft_response(self, email: Dict, category: str) -> str:
        """Generate a draft response based on email and category."""
        
        prompt = f"""Draft a professional response to this email.

CATEGORY: {category}
FROM: {email['from']}
SUBJECT: {email['subject']}
BODY: {email['body']}

Guidelines:
- Be professional and empathetic
- Address the specific concern
- Provide clear next steps
- Keep it concise (under 150 words)
- Sign as "SAP Support Team"

Draft the response:"""

        response = self.client.chat(
            message=prompt,
            temperature=0.5,
            max_tokens=300
        )
        
        return response


def run_demo():
    """Run email classifier demo."""
    print("=" * 60)
    print(" EMAIL CLASSIFIER - MEGA LAB Part 4")
    print("=" * 60)
    
    classifier = EmailClassifier()
    
    print("\n[INFO] Processing sample emails...\n")
    
    for email in SAMPLE_EMAILS:
        print("-" * 60)
        print(f"[EMAIL] From: {email['from']}")
        print(f"        Subject: {email['subject']}")
        print("-" * 60)
        
        # Step 1: Classify
        print("[CLASSIFY] Analyzing email...")
        category = classifier.classify(email)
        print(f"[OK] Category: {category}")
        
        # Step 2: Full analysis
        print("[ANALYZE] Extracting details...")
        analysis = classifier.analyze(email)
        print(f"\n{analysis['analysis']}")
        
        # Step 3: Draft response
        print("\n[DRAFT] Generating response...")
        response = classifier.draft_response(email, category)
        print(f"\n--- DRAFT RESPONSE ---")
        print(response)
        print("--- END DRAFT ---")
        
        input("\nPress Enter for next email...")
        print("\n")
    
    print("=" * 60)
    print("[DONE] Email classification demo complete!")
    print("=" * 60)
    
    # Summary
    print("\n[SUMMARY] Classification Results:")
    print("-" * 40)
    for email in SAMPLE_EMAILS:
        category = classifier.classify(email)
        print(f"  {email['id']}: {category}")


if __name__ == "__main__":
    run_demo()