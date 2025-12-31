import pytest
from src.gateway.adapters.gemini import GeminiAdapter
from src.gateway.adapters.openai import OpenAIAdapter
from src.gateway.adapters.claude import ClaudeAdapter

def test_gemini_adapter_init():
    adapter = GeminiAdapter("fake-key")
    assert adapter.supports_model("gemini-2.0-flash-exp")
    limits = adapter.get_rate_limits()
    assert limits.requests_per_minute > 0

def test_openai_adapter_init():
    adapter = OpenAIAdapter("fake-key")
    assert adapter.supports_model("gpt-4")
    assert adapter.supports_model("o1-preview")
    limits = adapter.get_rate_limits()
    assert limits.requests_per_minute > 0

def test_claude_adapter_init():
    adapter = ClaudeAdapter("fake-key")
    assert adapter.supports_model("claude-3-5-sonnet")
    limits = adapter.get_rate_limits()
    assert limits.requests_per_minute > 0
