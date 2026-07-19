"""Runtime configuration for optional LangSmith tracing."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LANGSMITH_PROJECT = "deep-research"


def configure_langsmith() -> bool:
    """Load local tracing settings and enable LangSmith when a key is present.

    Environment variables supplied by the deployment take precedence over values
    in ``.env``. Set ``LANGSMITH_TRACING=false`` to explicitly disable tracing.
    """
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    if not os.getenv("LANGSMITH_API_KEY"):
        return False

    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", DEFAULT_LANGSMITH_PROJECT)
    return os.getenv("LANGSMITH_TRACING", "").lower() == "true"
