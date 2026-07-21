import os

class AICoreLLMClient:
    """SAP AI Core / Generative AI Hub client"""
    
    def __init__(self, model_name: str = "gpt-4o"):
        try:
            from gen_ai_hub.proxy.langchain import ChatOpenAI
            from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
            self.proxy_client = get_proxy_client("gen-ai-hub")
            self.model = ChatOpenAI(
                proxy_client=self.proxy_client,
                proxy_model_name=model_name,
                temperature=0.1
            )
        except ImportError as e:
            raise ImportError(
                f"SAP GenAI Hub SDK not properly installed. Run:\n"
                f"  pip install generative-ai-hub-sdk langchain-aws langchain-google-genai\n"
                f"Original error: {e}"
            )
    
    def invoke(self, prompt: str) -> str:
        response = self.model.invoke(prompt)
        return response.content


class LocalLLMClient:
    """Direct OpenAI API client (or compatible endpoint)"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None, model_name: str = None):
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=api_key or os.getenv("OPENAI_API_KEY"),
                base_url=base_url
            )
            self.model = model or model_name or "gpt-4o"
        except ImportError:
            raise ImportError("OpenAI SDK not installed. Run: pip install openai")
    
    def invoke(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return response.choices[0].message.content


class MockLLMClient:
    """Mock LLM client for testing - no external dependencies required"""
    
    def invoke(self, prompt: str) -> str:
        if "root cause" in prompt.lower() or "analyze" in prompt.lower():
            return """Root Cause Analysis:
            
1. PRIMARY CAUSE: RFC connection timeout to remote system
   - The job attempted to call RFC destination CLNT100 which failed after 30 seconds
   - Error code: RFC_COMMUNICATION_FAILURE

2. CONTRIBUTING FACTORS:
   - Network latency between application servers
   - Remote system may be under heavy load

3. RECOMMENDATION:
   - Check RFC destination configuration in SM59
   - Verify remote system availability
   - Consider increasing timeout parameters"""
        
        return "Analysis complete. No specific issues identified."


def get_llm_client(mode: str = "mock", **kwargs):
    """
    Factory function to get the appropriate LLM client.
    
    Args:
        mode: "mock" (no deps), "local" (OpenAI), or "aicore" (SAP AI Core)
    """
    if mode == "aicore":
        return AICoreLLMClient(**kwargs)
    elif mode == "local":
        return LocalLLMClient(**kwargs)
    else:
        return MockLLMClient()
