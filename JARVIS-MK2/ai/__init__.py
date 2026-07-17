"""
AI Providers package for JARVIS-MK2.
"""

from .provider import AIProvider
from .mock_provider import MockProvider

try:
    from .ollama_provider import OllamaProvider
    _has_ollama = True
except ImportError:
    OllamaProvider = None  # type: ignore
    _has_ollama = False

__all__ = [
    "AIProvider",
    "MockProvider",
]

if _has_ollama:
    __all__.append("OllamaProvider")