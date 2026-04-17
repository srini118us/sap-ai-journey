"""
AWS Bedrock Lab 1: First API Call
"""
import boto3
import json

# Create Bedrock client
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

# Use Claude Sonnet 4 (latest)
response = bedrock.invoke_model(
    modelId='us.anthropic.claude-sonnet-4-20250514-v1:0',
    contentType='application/json',
    accept='application/json',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "messages": [
            {"role": "user", "content": "Hello! What is AWS Bedrock in 2 sentences and show me architectural flow in AWS Cloud eco system?"}
        ]
    })
)

# Parse response
result = json.loads(response['body'].read())
print("Response:", result['content'][0]['text'])