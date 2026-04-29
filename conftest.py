# conftest.py — shared pytest configuration
# Place this at the project root so pytest can find all test modules correctly.
import sys
from pathlib import Path

# Make green_budget_optimizer importable from tests/
sys.path.insert(0, str(Path(__file__).parent / "green_budget_optimizer"))
