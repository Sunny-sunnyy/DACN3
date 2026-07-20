"""Frontier Price Adapter — lazy-loading wrapper for ChromaDB RAG + OpenAI estimator.

Module-level imports are stdlib only. Heavy dependencies (chromadb,
sentence_transformers, openai) are imported lazily inside _load() on
first try_estimate() call. This keeps the mock path free of frontier deps.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("shopping_assistant_v3.frontier")

# Collection name used by segment4 ChromaDB vectorstore.
COLLECTION_NAME = "products"
# Number of similar products retrieved for RAG context.
N_SIMILARS = 5


@dataclass
class FrontierEstimateResult:
    """Result of a frontier price estimation attempt.

    When available=False, error_code describes the failure mode using a
    bounded grammar. error_detail is capped at 200 chars and must never
    contain raw exceptions, stack traces, or secrets.
    """

    value_usd: float | None = None
    available: bool = False
    error_code: str | None = None
    error_detail: str | None = None


def _sanitize_detail(raw: str) -> str:
    """Return a bounded, safe detail string (max 200 chars, single line)."""
    cleaned = str(raw).replace("\n", " ").replace("\r", "").strip()
    if len(cleaned) > 200:
        cleaned = cleaned[:197] + "..."
    return cleaned


def _extract_price(text: str) -> float | None:
    """Extract the first USD price from a model response string.

    Returns None if no numeric price is found — caller should treat this
    as a parse_error, not silently return 0.0.
    """
    s = text.replace("$", "").replace(",", "")
    match = re.search(r"[-+]?\d*\.\d+|\d+", s)
    if match:
        return float(match.group())
    return None


class FrontierPriceAdapter:
    """Lazy-loading adapter for the Frontier (GPT + ChromaDB RAG) estimator.

    Heavy dependencies (chromadb, sentence_transformers, openai) are
    imported only when try_estimate() is first called — never at
    module import time.

    Usage:
        adapter = FrontierPriceAdapter(
            chromadb_path="/path/to/products_vectorstore",
            model_id="gpt-5.1",
        )
        result = adapter.try_estimate("Title: Laptop ...")
        if result.available:
            print(result.value_usd)
    """

    def __init__(self, chromadb_path: str, model_id: str) -> None:
        """Store config. No heavy imports, no file I/O at init."""
        self._chromadb_path = chromadb_path
        self._model_id = model_id
        self._collection = None          # chromadb Collection or None
        self._embed_model = None         # SentenceTransformer or None
        self._openai_client = None       # OpenAI client or None
        self._init_error: FrontierEstimateResult | None = None
        self._init_attempted = False

    def try_estimate(self, text: str) -> FrontierEstimateResult:
        """Run frontier inference. Lazy-loads deps + model on first call.

        Never raises — failures become FrontierEstimateResult metadata.
        """
        if not self._init_attempted:
            self._init_attempted = True
            self._load()

        if self._init_error is not None:
            return self._init_error

        try:
            # Step 1: embed query
            vector = self._embed_model.encode([text])

            # Step 2: query ChromaDB for similar products
            results = self._collection.query(
                query_embeddings=vector.astype(float).tolist(),
                n_results=N_SIMILARS,
            )
            documents = results["documents"][0][:]
            prices = [m["price"] for m in results["metadatas"][0][:]]

            # Step 3: build prompt with RAG context
            message = self._build_prompt(text, documents, prices)

            # Step 4: call OpenAI
            response = self._openai_client.chat.completions.create(
                model=self._model_id,
                messages=[{"role": "user", "content": message}],
                seed=42,
            )
            reply = response.choices[0].message.content

            # Step 5: parse price from response
            value = _extract_price(reply)
            if value is None:
                return FrontierEstimateResult(
                    available=False,
                    error_code="parse_error",
                    error_detail="Model response contained no numeric price",
                )

            value = float(max(0, value))
            return FrontierEstimateResult(
                value_usd=round(value, 2),
                available=True,
            )

        except Exception as exc:
            logger.warning(
                "Frontier inference failed: %s", _sanitize_detail(str(exc))
            )
            return FrontierEstimateResult(
                available=False,
                error_code="model_error",
                error_detail=_sanitize_detail(str(exc)),
            )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Lazy init: validate config, import heavy deps, connect services.

        Sets self._init_error on any failure. Called once by try_estimate().
        """
        # Step 1: validate chromadb path
        if not self._chromadb_path:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="missing_chromadb_path",
                error_detail="PRICER_CHROMADB_PATH is not set",
            )
            return

        db_path = Path(self._chromadb_path)
        if not db_path.exists():
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="missing_chromadb_path",
                error_detail="ChromaDB path does not exist",
            )
            return

        # Step 2: validate model_id
        if not self._model_id:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="model_config_missing",
                error_detail="PRICER_FRONTIER_MODEL_ID is not set",
            )
            return

        # Step 3: lazy-import heavy dependencies
        try:
            import chromadb  # noqa: F401
            from sentence_transformers import SentenceTransformer
            from openai import OpenAI
        except ImportError as exc:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="missing_dependency",
                error_detail=_sanitize_detail(str(exc)),
            )
            return

        # Step 4: connect ChromaDB
        try:
            client = chromadb.PersistentClient(path=str(db_path))
            self._collection = client.get_collection(COLLECTION_NAME)
        except Exception as exc:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="collection_not_found",
                error_detail=_sanitize_detail(str(exc)),
            )
            return

        # Step 5: load embedding model
        try:
            self._embed_model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
        except Exception as exc:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="missing_dependency",
                error_detail=_sanitize_detail(str(exc)),
            )
            return

        # Step 6: init OpenAI client
        try:
            self._openai_client = OpenAI()
        except Exception as exc:
            self._init_error = FrontierEstimateResult(
                available=False,
                error_code="model_config_missing",
                error_detail=_sanitize_detail(str(exc)),
            )
            return

    def _build_prompt(
        self,
        description: str,
        documents: list[str],
        prices: list[float],
    ) -> str:
        """Build the RAG-augmented prompt with similar products as context.

        Adapted from segment4 FrontierAgent.messages_for() and make_context().
        """
        message = (
            "Estimate the price of this product. "
            "Respond with the price, no explanation\n\n"
            f"{description}\n\n"
        )
        message += (
            "To provide some context, here are some other items that might be "
            "similar to the item you need to estimate.\n\n"
        )
        for doc, price in zip(documents, prices):
            message += (
                f"Potentially related product:\n{doc}\n"
                f"Price is ${price:.2f}\n\n"
            )
        return message
