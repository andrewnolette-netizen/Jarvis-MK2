"""
AI Provider interface for JARVIS-MK2.
Defines a common interface for different AI backends.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from core.logger import get_logger

logger = get_logger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AI provider.

        Args:
            config: Configuration dictionary for the provider
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = config or {}

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate text based on a prompt.

        Args:
            prompt: The input prompt
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text string
        """
        pass

    @abstractmethod
    async def classify(
        self,
        text: str,
        categories: List[str],
        **kwargs
    ) -> Dict[str, float]:
        """
        Classify text into one or more categories.

        Args:
            text: The text to classify
            categories: List of possible categories
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary mapping categories to confidence scores (0.0 to 1.0)
        """
        pass

    @abstractmethod
    async def summarize(
        self,
        text: str,
        max_length: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Summarize text.

        Args:
            text: The text to summarize
            max_length: Maximum length of the summary
            **kwargs: Additional provider-specific parameters

        Returns:
            Summarized text
        """
        pass

    @abstractmethod
    async def reason(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> str:
        """
        Perform reasoning or chain-of-thought based on a prompt.

        Args:
            prompt: The reasoning prompt or question
            context: Optional context information (e.g., previous steps, facts)
            **kwargs: Additional provider-specific parameters

        Returns:
            Reasoned response or conclusion
        """
        pass

    def is_available(self) -> bool:
        """
        Check if the AI provider is available and ready to serve requests.

        Returns:
            True if the provider is ready, False otherwise
        """
        return True

    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the provider.

        Returns:
            Dictionary with provider information (name, version, capabilities, etc.)
        """
        return {
            "name": self.__class__.__name__,
            "type": "abstract",
        }