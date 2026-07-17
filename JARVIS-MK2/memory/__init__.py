"""
Memory package for JARVIS-MK2.
"""

from .short_term import ShortTermMemory
from .long_term import LongTermMemory
from .episodic import EpisodicMemory
from .memory_manager import MemoryManager

__all__ = [
    "ShortTermMemory",
    "LongTermMemory",
    "EpisodicMemory",
    "MemoryManager",
]

# Global memory manager instance
memory_manager = MemoryManager()