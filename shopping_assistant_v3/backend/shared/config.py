"""Application configuration loaded from environment variables.

Never logs or prints secret values. Uses python-dotenv to load .env files.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in ("1", "true", "yes", "on")


# Safety flags: default mock mode, no network, no paid model calls.
ENABLE_REAL_SEARCH: bool = _get_bool("ENABLE_REAL_SEARCH", False)
ENABLE_REAL_MODEL_CALLS: bool = _get_bool("ENABLE_REAL_MODEL_CALLS", False)

# Persistence
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{Path(__file__).resolve().parent.parent / 'database' / 'app.db'}",
)

# Model config (unused in Phase 2 but declared for completeness)
MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "openai")
MODEL_ID_ROUTER: str = os.getenv("MODEL_ID_ROUTER", "")
MODEL_ID_SYNTHESIZER: str = os.getenv("MODEL_ID_SYNTHESIZER", "")

# Neural pricing (Phase 4C): path to deep_neural_network.pth weights file.
# No default — real neural pricing requires explicit path via env.
PRICER_NEURAL_WEIGHTS_PATH: str = os.getenv("PRICER_NEURAL_WEIGHTS_PATH", "")

# Frontier pricing (Phase 4C.2): path to ChromaDB vectorstore directory.
# No default — real frontier requires explicit path via env.
PRICER_CHROMADB_PATH: str = os.getenv("PRICER_CHROMADB_PATH", "")

# Frontier pricing (Phase 4C.2): model ID for OpenAI-compatible API call.
# No default — real frontier requires explicit model via env.
PRICER_FRONTIER_MODEL_ID: str = os.getenv("PRICER_FRONTIER_MODEL_ID", "")

# Specialist pricing (Phase 4C.3): Modal service and class names.
# No default — real specialist requires explicit Modal config via env.
PRICER_SPECIALIST_SERVICE: str = os.getenv("PRICER_SPECIALIST_SERVICE", "")
PRICER_SPECIALIST_CLASS: str = os.getenv("PRICER_SPECIALIST_CLASS", "")

# Demo identity for MVP
DEMO_USER_ID: str = "demo_user"
