"""Prompt loader utility for external .md prompt files."""

from pathlib import Path
from functools import lru_cache

PROMPTS_DIR = Path(__file__).parent / "prompts"


@lru_cache(maxsize=16)
def load_prompt(name: str) -> str:
    """
    Load a prompt file by name (without .md extension).

    Args:
        name: The prompt name (e.g., "system_base", "casual")

    Returns:
        The prompt content as a string

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    prompt_path = PROMPTS_DIR / f"{name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def build_system_prompt(*prompt_names: str) -> str:
    """
    Combine multiple prompts into one system message.

    Args:
        *prompt_names: Names of prompts to combine (e.g., "system_base", "casual")

    Returns:
        Combined prompt content separated by newlines

    Example:
        >>> system = build_system_prompt("system_base", "casual")
    """
    return "\n\n---\n\n".join(load_prompt(name) for name in prompt_names)


def clear_prompt_cache():
    """Clear the prompt cache. Useful for development/hot-reloading."""
    load_prompt.cache_clear()
