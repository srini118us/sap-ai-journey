"""
AWS Bedrock Lab 1: Bedrock Basics
- Test multiple models
- Compare API patterns
- Understand response structure
"""
import boto3
import json
import time

# Create Bedrock client
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

def call_claude(prompt, model_id='us.anthropic.claude-sonnet-4-20250514-v1:0'):
    """Call Claude model via Bedrock"""
    start = time.time()
    
    response = bedrock.invoke_model(
        modelId=model_id,
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
    )
    
    result = json.loads(response['body'].read())
    elapsed = time.time() - start
    
    return {
        'text': result['content'][0]['text'],
        'model': result.get('model', model_id),
        'input_tokens': result['usage']['input_tokens'],
        'output_tokens': result['usage']['output_tokens'],
        'time_seconds': round(elapsed, 2)
    }

def call_titan(prompt):
    """Call Amazon Titan model via Bedrock"""
    start = time.time()
    
    response = bedrock.invoke_model(
        modelId='amazon.titan-text-lite-v1',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 500,
                "temperature": 0.7
            }
        })
    )
    
    result = json.loads(response['body'].read())
    elapsed = time.time() - start
    
    return {
        'text': result['results'][0]['outputText'],
        'model': 'amazon.titan-text-lite-v1',
        'time_seconds': round(elapsed, 2)
    }

# =============================================================================
# TEST DIFFERENT MODELS
# =============================================================================
if __name__ == "__main__":
    prompt = "What are the three main benefits of serverless computing? Be brief."
    
    print("=" * 60)
    print("AWS BEDROCK - MODEL COMPARISON")
    print("=" * 60)
    
    # Test Claude Sonnet 4
    print("\n[1] Claude Sonnet 4:")
    print("-" * 40)
    result = call_claude(prompt)
    print(f"Response: {result['text'][:300]}...")
    print(f"\nTokens: {result['input_tokens']} in / {result['output_tokens']} out")
    print(f"Time: {result['time_seconds']}s")
    
    # Test Claude Haiku (faster, cheaper)
    print("\n[2] Claude Haiku 4.5:")
    print("-" * 40)
    result = call_claude(prompt, 'us.anthropic.claude-haiku-4-5-20251001-v1:0')
    print(f"Response: {result['text'][:300]}...")
    print(f"\nTokens: {result['input_tokens']} in / {result['output_tokens']} out")
    print(f"Time: {result['time_seconds']}s")
    
    print("\n" + "=" * 60)
    print("✅ Bedrock basics complete!")