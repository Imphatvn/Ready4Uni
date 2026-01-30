"""
Ready4Uni Test Suite

Comprehensive unit and integration tests for all modules.
Run tests with: pytest tests/
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_DATA_DIR = Path(__file__).parent / "fixtures"
SAMPLE_TRANSCRIPT_PATH = TEST_DATA_DIR / "sample_transcript.pdf"

__all__ = [
    "TEST_DATA_DIR",
    "SAMPLE_TRANSCRIPT_PATH",
]
