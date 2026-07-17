"""
Ollama AI provider implementation.
"""

import json
import asyncio
from typing import Any, Dict, List, Optional, Union

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None  # type: ignore

from .provider import AIProvider


class OllamaProvider(AIProvider):
    """AI provider that uses Ollama running locally or on a remote host."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        timeout: int = 30,
    ):
        """
        Initialize the Ollama provider.

        Args:
            base_url: Base URL of the Ollama API (default: http://localhost:11434)
            model: Model name to use (default: llama2)
            timeout: Request timeout in seconds
        """
        super().__init__()
        if not AIOHTTP_AVAILABLE:
            raise ImportError(
                "aiohttp is required for OllamaProvider. "
                "Install it with: pip install aiohttp"
            )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an active aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self.session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate text using the Ollama API."""
        session = await self._ensure_session()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if max_tokens is not None:
            payload["num_predict"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        # Add any additional parameters from kwargs
        payload.update(kwargs)

        try:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Ollama API error {response.status}: {error_text}"
                    )
                result = await response.json()
                return result.get("response", "")
        except Exception as e:
            # If we get a connection error, it might be that Ollama is not running
            raise ConnectionError(
                f"Failed to connect to Ollama at {self.base_url}. "
                f"Please ensure Ollama is running and accessible. Error: {e}"
            ) from e

    async def classify(
        self,
        text: str,
        categories: List[str],
        **kwargs
    ) -> Dict[str, float]:
        """
        Classify text using the Ollama API.
        We'll use a prompt that asks the model to classify the text.
        """
        # Construct a classification prompt
        categories_str = ", ".join(categories)
        prompt = f"""Classify the following text into exactly one of these categories: {categories_st}.
Text: "{text}"
Respond with only the category name, nothing else."""

        try:
            response = await self.generate(prompt, temperature=0.1, **kwargs)
            # Clean up the response
            predicted = response.strip()
            # Find which category matches the prediction (case-insensitive)
            for category in categories:
                if category.lower() == predicted.lower():
                    # Return high confidence for the matched category, low for others
                    return {
                        cat: 0.9 if cat == category else 0.1 / (len(categories) - 1)
                        for cat in categories
                    }
            # If no match, return uniform distribution
            return {cat: 1.0 / len(categories) for cat in categories}
        except Exception as e:
            # Fallback to uniform distribution on error
            return {cat: 1.0 / len(categories) for cat in categories}

    async def summarize(
        self,
        text: str,
        max_length: Optional[int] = None,
        **kwargs
    ) -> str:
        """Summarize text using the Ollama API."""
        if not text.strip():
            return ""
        prompt = f"""Please provide a concise summary of the following text:
{text}
"""
        if max_length is not None:
            prompt += f"Keep the summary under {max_length} characters."
        try:
            summary = await self.generate(prompt, temperature=0.3, **kwargs)
            if max_length is not None and len(summary) > max_length:
                # Truncate to max_length, trying to break at a space
                if len(summary) > max_length:
                    truncated = summary[:max_length]
                    last_space = truncated.rfind(' ')
                    if last_space > max_length * 0.8:
                        return truncated[:last_space] + "..."
                    else:
                        return truncated + "..."
            return summary
        except Exception as e:
            # Fallback to a simple truncation
            if max_length is None:
                return text[:200] + "..." if len(text) > 200 else text
            return text[:max_length] + ("..." if len(text) > max_length else "")

    async def reason(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> str:
        """Perform reasoning using the Ollama API."""
        # Build a prompt that includes context if provided
        full_prompt = prompt
        if context:
            context_str = "\n".join(str(c) for c in context)
            full_prompt = f"Context:\n{context_str}\n\nQuestion: {prompt}"
        try:
            return await self.generate(
                f"{full_prompt}\nPlease reason step by step and provide your conclusion.",
                temperature=0.5,
                **kwargs
            )
        except Exception as e:
            return f"Error during reasoning: {e}"

    def is_available(self) -> bool:
        """Check if the Ollama server is reachable."""
        # This is a synchronous check; for a proper async check, we'd need to make a request.
        # For simplicity, we'll return True and let individual calls handle connection errors.
        return True

    def get_info(self) -> Dict[str, Any]:
        """Get information about the Ollama provider."""
        return {
            "name": "OllamaProvider",
            "version": "0.1.0",
            "type": "ollama",
            "model": self.model,
            "base_url": self.base_url,
        }