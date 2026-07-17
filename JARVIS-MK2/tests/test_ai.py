"""
Tests for the AI provider modules.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai.mock_provider import MockProvider
from ai.provider import AIProvider


async def test_mock_provider():
    """Test the mock AI provider."""
    print("Testing MockProvider...")

    provider = MockProvider(response_delay=0.01)  # Small delay for faster tests

    # Test that it's an AIProvider
    assert isinstance(provider, AIProvider)

    # Test generate
    prompt = "What is the meaning of life?"
    response = await provider.generate(prompt)
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"Generate response: {response[:50]}...")

    # Test classify
    text = "This is a test document."
    categories = ["positive", "negative", "neutral"]
    result = await provider.classify(text, categories)
    assert isinstance(result, dict)
    assert set(result.keys()) == set(categories)
    # Probabilities should sum to approximately 1
    total = sum(result.values())
    assert abs(total - 1.0) < 0.001
    print(f"Classification: {result}")

    # Test summarize
    long_text = "This is a very long text that should be summarized. " * 10
    summary = await provider.summarize(long_text, max_length=50)
    assert isinstance(summary, str)
    assert len(summary) <= 55  # Allow a bit over for ellipsis
    print(f"Summary: {summary}")

    # Test reason
    question = "Why is the sky blue?"
    reasoning = await provider.reason(question)
    assert isinstance(reasoning, str)
    assert len(reasoning) > 0
    print(f"Reasoning: {reasoning}")

    # Test info
    info = provider.get_info()
    assert isinstance(info, dict)
    assert "name" in info
    assert info["name"] == "MockProvider"
    print(f"Provider info: {info}")

    print("✓ MockProvider test passed")


async def main():
    """Run all tests."""
    await test_mock_provider()
    print("\n🎉 All AI provider tests passed!")


if __name__ == "__main__":
    asyncio.run(main())