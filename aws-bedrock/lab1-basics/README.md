# AWS Bedrock Lab 1: Fundamentals

This lab covers AWS Bedrock fundamentals - setup, API calls, model comparison, and tool use (function calling).

## Overview

| Topic | Description |
|-------|-------------|
| Setup | AWS CLI, IAM user, Bedrock access |
| Basic API | invoke_model for simple completions |
| Converse API | Multi-turn chat with tool support |
| Tool Use | Define tools, execute, return results |

## Prerequisites

1. AWS Account with billing enabled
2. AWS CLI installed and configured
3. Python 3.11+ with boto3
4. IAM user with AmazonBedrockFullAccess policy

## Setup

### Install AWS CLI

```powershell
# Windows
winget install Amazon.AWSCLI

# macOS
brew install awscli

# Verify
aws --version
```

### Configure AWS CLI

```bash
aws configure
# Enter: Access Key ID, Secret Key, us-east-1, json
```

### Verify Bedrock Access

```bash
aws bedrock list-inference-profiles --region us-east-1 \
  --query "inferenceProfileSummaries[?contains(inferenceProfileId, 'claude')].inferenceProfileId"
```

## Model IDs (Inference Profiles)

AWS Bedrock requires inference profile IDs:

| Model | Inference Profile ID |
|-------|---------------------|
| Claude Sonnet 4 | `us.anthropic.claude-sonnet-4-20250514-v1:0` |
| Claude Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| Claude Opus 4 | `us.anthropic.claude-opus-4-20250514-v1:0` |

## Files

| File | Purpose |
|------|---------|
| `test_bedrock.py` | Basic API call test |
| `bedrock_basics.py` | Model comparison (Sonnet vs Haiku) |
| `bedrock_agent_tools.py` | Tool use (function calling) demonstration |

## Key Concepts

### Two APIs

| API | Use Case |
|-----|----------|
| `invoke_model` | Simple completions, raw request/response |
| `converse` | Multi-turn chat, tool use, streaming |

### Tool Use Pattern

1. Define tools with JSON schema
2. Call model with toolConfig
3. Model returns `stopReason: tool_use`
4. Execute tool and return result
5. Model generates final response

## Model Comparison

| Model | Response Time | Best For |
|-------|---------------|----------|
| Claude Sonnet 4 | ~3.5s | Complex reasoning, detailed analysis |
| Claude Haiku 4.5 | ~1.7s | Fast responses, agents, cost-efficient |

## Common Issues

| Issue | Resolution |
|-------|------------|
| Model ID format error | Use inference profile: `us.anthropic.claude-*` |
| Anthropic access denied | Submit use case form in Bedrock console |
| ThrottlingException | Add retry logic with exponential backoff |

## Documentation

See `docs/AWS_Bedrock_Complete_Technical_Guide.docx` for comprehensive documentation including architecture diagrams and detailed setup instructions.

## Next Labs

- **Lab 2:** Bedrock Managed Agents (action groups, Lambda)
- **Lab 3:** Knowledge Bases (RAG with S3 + OpenSearch)
- **Lab 4:** LangGraph on Bedrock

## Reference Links

- [Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Converse API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
- [Model IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html)
- [boto3 Bedrock](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html)
