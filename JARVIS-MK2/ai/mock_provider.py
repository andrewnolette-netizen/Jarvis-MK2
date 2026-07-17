"""
Mock AI provider for testing and development.
"""

import asyncio
import random
import time
from typing import Any, Dict, List, Optional, Union

from .provider import AIProvider


class MockProvider(AIProvider):
    """Mock AI provider that returns deterministic or random responses for testing."""

    def __init__(self, response_delay: float = 0.1, failure_rate: float = 0.0):
        """
        Initialize the mock provider.

        Args:
            response_delay: Simulated delay in seconds for each call
            failure_rate: Probability of returning an error (0.0 to 1.0)
        """
        super().__init__()
        self.response_delay = response_delay
        self.failure_rate = failure_rate
        self.call_count = 0
        self.last_prompt: Optional[str] = None

    async def _maybe_fail(self) -> None:
        """Randomly raise an exception based on failure rate."""
        if self.failure_rate > 0 and random.random() < self.failure_rate:
            raise Exception("Simulated failure from MockProvider")

    async def _delay(self) -> None:
        """Simulate processing delay."""
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate a mock response."""
        await self._maybe_fail()
        await self._delay()
        self.call_count += 1
        self.last_prompt = prompt

        # Generate a deterministic response based on the prompt hash
        # This makes testing easier
        seed = hash(str((prompt, max_tokens, temperature))) % 10000
        random.seed(seed)
        # Generate a response that looks like text
        words = ["the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog",
                 "hello", "world", "this", "is", "a", "test", "response", "from",
                 "mock", "ai", "provider"]
        num_words = min(50, max(10, int(len(prompt) / 5)))
        response = " ".join(random.choices(words, k=num_words))
        # Reset random seed
        random.seed()
        return response

    async def classify(
        self,
        text: str,
        categories: List[str],
        **kwargs
    ) -> Dict[str, float]:
        """Mock classification."""
        await self._maybe_fail()
        await self._delay()
        self.call_count += 1
        self.last_prompt = f"classify: {text}"

        # Return a deterministic distribution based on the text hash
        seed = hash(text) % 10000
        random.seed(seed)
        # Generate random weights that sum to 1
        weights = [random.random() for _ in categories]
        total = sum(weights)
        normalized = [w / total for w in weights]
        random.seed()
        return dict(zip(categories, normalized))

    async def summarize(
        self,
        text: str,
        max_length: Optional[int] = None,
        **kwargs
    ) -> str:
        """Mock summarization."""
        await self._maybe_fail()
        await self._delay()
        self.call_count += 1
        self.last_prompt = f"summarize: {text[:50]}..."

        # Return a shortened version of the text
        if not text.strip():
            return ""
        if len(text) <= 100:
            return text
        # Take first and last parts
        start = text[:50]
        end = text[-50:] if len(text) > 50 else ""
        summary = f"{start} ... {end}" if end else start
        if max_length is not None and len(summary) > max_length:
            summary = summary[:max_length]
        return summary

    async def reason(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> str:
        """Mock reasoning."""
        await self._maybe_fail()
        await self._delay()
        self.call_count += 1
        self.last_prompt = f"reason: {prompt}"

        # Return a canned reasoning response
        if "why" in prompt.lower():
            return "Because of various factors including cause and effect, logical deductions, and empirical evidence."
        elif "how" in prompt.lower():
            return "Through a series of steps involving preparation, execution, and verification."
        else:
            return "Based on the available information, the most logical conclusion is that the statement is true."

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "call_count": self.call_count,
            "last_prompt": self.last_prompt,
            "response_delay": self.response_delay,
            "failure_rate": self.failure_rate,
        }

    def reset_stats(self):
        self.call_count = 0
        self.last_prompt = None

    def get_info(self) -> Dict[str, Any]:
        """Get information about the mock provider."""
        return {
            "name": "MockProvider",
            "version": "0.1.0",
            "type": "mock",
        }