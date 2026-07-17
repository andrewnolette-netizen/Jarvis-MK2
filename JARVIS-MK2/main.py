#!/usr/bin/env python3
"""
Main entry point for JARVIS-MK2.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.controller import controller

print("About to run controller")
controller.run()
print("After controller")