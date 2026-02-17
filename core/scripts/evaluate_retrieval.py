"""Evaluate retrieval quality against a small deterministic dataset."""
from __future__ import annotations

import json
from pathlib import Path

from src.core.exceptions import ConfigurationError
from src.services.vector_store import VectorStoreService


def evaluate(dataset_path: Path) -> int:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    service = VectorStoreService()

    total = len(dataset)
    if total == 0:
        print("No evaluation records found.")
        return 1

    hits = 0
    for case in dataset:
        person_id = case["person_id"]
        source = case["source"]
        documents = case["documents"]
        query = case["query"]
        expected_terms = [term.lower() for term in case["expected_terms"]]

        service.replace_source_documents(
            person_id=person_id,
            source=source,
            documents=documents,
            extra_metadata={"dataset": "retrieval_eval"},
        )

        results = service.search(
            person_id=person_id,
            query=query,
            top_k=5,
            min_score=0.1,
            enable_hybrid_fallback=True,
        )

        text_blob = " ".join(result.get("text", "") for result in results).lower()
        passed = all(term in text_blob for term in expected_terms)
        hits += int(passed)
        print(
            f"- source={source} query={query!r} result_count={len(results)} "
            f"status={'PASS' if passed else 'FAIL'}"
        )

    hit_rate = hits / total
    print(f"retrieval_hit_rate={hit_rate:.2%} ({hits}/{total})")
    return 0 if hit_rate >= 0.66 else 1


if __name__ == "__main__":
    default_dataset = Path("data/evaluation/retrieval_eval_dataset.json")
    try:
        raise_code = evaluate(default_dataset)
    except ConfigurationError as exc:
        print(f"Retrieval evaluation skipped: {exc.message}")
        raise_code = 1
    raise SystemExit(raise_code)
