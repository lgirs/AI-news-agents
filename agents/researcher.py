"""Researcher agent that evaluates AI news sources weekly."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

from .logger import logger
from .models import FeedbackRequest, FeedbackResponse, SourceMetadata
from .storage import consume_feedback_responses, load_feedback, save_feedback, upsert_sources

DEFAULT_SOURCES = [
    {
        "source_id": "ft_ai",
        "name": "Financial Times • AI",
        "url": "https://www.ft.com/stream/5285b972-7c50-4e4a-b833-1b7eea195df3",
        "ingestion_type": "html",
        "credibility_score": 0.92,
        "visitor_score": 0.9,
        "business_alignment": 0.95,
        "topics": ["business", "markets", "policy"],
        "cadence": "daily",
    },
    {
        "source_id": "reuters_ai",
        "name": "Reuters • AI",
        "url": "https://www.reuters.com/technology/artificial-intelligence/",
        "ingestion_type": "html",
        "credibility_score": 0.95,
        "visitor_score": 0.94,
        "business_alignment": 0.9,
        "topics": ["markets", "policy"],
        "cadence": "daily",
    },
    {
        "source_id": "a16z_ai",
        "name": "a16z • AI + business",
        "url": "https://feeds.simplecast.com/tOjNXec5",
        "ingestion_type": "rss",
        "credibility_score": 0.7,
        "visitor_score": 0.7,
        "business_alignment": 0.85,
        "topics": ["business", "society"],
        "cadence": "weekly",
    },
    {
        "source_id": "mit_techreview_ai",
        "name": "MIT Tech Review • AI",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
        "ingestion_type": "rss",
        "credibility_score": 0.88,
        "visitor_score": 0.83,
        "business_alignment": 0.82,
        "topics": ["policy", "society"],
        "cadence": "daily",
    },
]

FEEDBACK_NOTES = Path("docs/FEEDBACK.md")


def load_feedback_file(path: Path) -> List[FeedbackResponse]:
    """Load feedback responses from a standalone JSON payload."""

    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if isinstance(payload, dict):
        responses = payload.get("responses", [])
    elif isinstance(payload, list):
        responses = payload
    else:  # pragma: no cover - defensive guard
        raise ValueError("Unsupported feedback format; expected list or {responses: []}")
    return [FeedbackResponse(**item) for item in responses]


class ResearcherAgent:
    """Evaluates sources and handles feedback."""

    def __init__(self, minimum_score: float = 0.6) -> None:
        self.minimum_score = minimum_score

    def normalize_sources(self) -> List[SourceMetadata]:
        logger.info("Normalizing %d baseline sources", len(DEFAULT_SOURCES))
        normalized = []
        for payload in DEFAULT_SOURCES:
            relevance = (payload["credibility_score"] + payload["visitor_score"] + payload["business_alignment"]) / 3
            if relevance < self.minimum_score:
                logger.warning("Skipping %s due to low aggregate score", payload["name"])
                continue
            normalized.append(SourceMetadata(**payload))
        return normalized

    def apply_feedback(self, sources: Sequence[SourceMetadata], responses: Sequence[FeedbackResponse]) -> List[SourceMetadata]:
        if not responses:
            return list(sources)
        catalog = {src.source_id: src for src in sources}
        for response in responses:
            logger.info("Applying feedback action=%s source_id=%s", response.action, response.source_id)
            if response.action == "remove" and response.source_id in catalog:
                catalog.pop(response.source_id)
                continue
            if response.action == "adjust" and response.source_id in catalog:
                updated = catalog[response.source_id].dict()
                updated.update(response.payload)
                catalog[response.source_id] = SourceMetadata(**updated)
                continue
            if response.action == "add":
                new_payload = dict(response.payload)
                new_payload["source_id"] = new_payload.get("source_id") or response.source_id or self._slugify_name(
                    new_payload.get("name", "source")
                )
                catalog[new_payload["source_id"]] = SourceMetadata(**new_payload)
        return list(catalog.values())

    @staticmethod
    def _slugify_name(name: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_") or "source"

    def request_feedback(self) -> None:
        data = load_feedback()
        now = datetime.now(timezone.utc)
        last_request = data.get("last_request_iso")
        if last_request:
            last_dt = datetime.fromisoformat(last_request)
            if (now - last_dt).days < 7:
                logger.info("Feedback already requested within the last week")
                return
        note = FeedbackRequest(
            requested_at=now,
            notes="Please review AI source coverage and suggest business policy additions.",
        )
        requests = data.get("requests", [])
        requests.append({"requested_at": note.requested_at.isoformat(), "notes": note.notes})
        data["requests"] = requests
        data["last_request_iso"] = now.isoformat()
        save_feedback(data)
        FEEDBACK_NOTES.parent.mkdir(parents=True, exist_ok=True)
        FEEDBACK_NOTES.write_text(
            """# Researcher feedback loop\n\n- Update `data/feedback.json` > `responses` with entries like:\n```json\n{\n  \"submitted_at\": \"2024-05-10T08:00:00+00:00\",\n  \"source_id\": \"new_source\",\n  \"action\": \"add\",\n  \"payload\": {\n    \"name\": \"Example AI\",\n    \"url\": \"https://example.com/rss\",\n    \"ingestion_type\": \"rss\",\n    \"credibility_score\": 0.7,\n    \"visitor_score\": 0.6,\n    \"business_alignment\": 0.8,\n    \"topics\": [\"business\"],\n    \"cadence\": \"weekly\"\n  }\n}\n```\n"""
        )

    def run(self, injected_feedback: Sequence[FeedbackResponse] | None = None) -> None:
        logger.info("Starting Researcher agent")
        sources = self.normalize_sources()
        responses = consume_feedback_responses()
        if injected_feedback:
            responses = list(responses) + list(injected_feedback)
        expanded = self.apply_feedback(sources, responses)
        upsert_sources(expanded)
        self.request_feedback()
        logger.success("Researcher completed %d sources (including feedback)", len(expanded))


def main() -> None:
    parser = argparse.ArgumentParser(description="Researcher agent")
    parser.add_argument("--min-score", type=float, default=0.6, help="Minimum aggregate score")
    parser.add_argument(
        "--extra-feedback",
        type=Path,
        help="Optional path to a JSON file with one-off responses to ingest",
        default=None,
    )
    args = parser.parse_args()
    agent = ResearcherAgent(minimum_score=args.min_score)
    injected = load_feedback_file(args.extra_feedback) if args.extra_feedback else None
    agent.run(injected_feedback=injected)


if __name__ == "__main__":
    main()
