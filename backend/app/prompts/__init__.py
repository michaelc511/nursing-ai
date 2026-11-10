"""Versioned prompt files (CLAUDE.md: prompts are files, not inline strings)."""
from pathlib import Path

_DIR = Path(__file__).parent


def load(name: str) -> str:
    return (_DIR / f"{name}.md").read_text()
