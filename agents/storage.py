"""SQLite helpers for persisting sources and feedback."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

from .models import FeedbackResponse, SourceMetadata

DB_PATH = Path("data/sources.db")
FEEDBACK_PATH = Path("data/feedback.json")
CATALOG_PATH = Path("data/source_catalog.json")


def ensure_schema() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                ingestion_type TEXT NOT NULL,
                credibility_score REAL,
                topics TEXT,
                cadence TEXT,
                visitor_score REAL,
                business_alignment REAL,
                last_checked TEXT
            )
            """
        )
        conn.commit()


def upsert_sources(sources: Iterable[SourceMetadata]) -> None:
    ensure_schema()
    with sqlite3.connect(DB_PATH) as conn:
        for src in sources:
            last_checked = src.last_checked
            if isinstance(last_checked, str):  # pragma: no cover - defensive for raw payloads
                last_checked = datetime.fromisoformat(last_checked)
            conn.execute(
                """
                INSERT INTO sources (
                    source_id, name, url, ingestion_type, credibility_score, topics,
                    cadence, visitor_score, business_alignment, last_checked
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    name=excluded.name,
                    url=excluded.url,
                    ingestion_type=excluded.ingestion_type,
                    credibility_score=excluded.credibility_score,
                    topics=excluded.topics,
                    cadence=excluded.cadence,
                    visitor_score=excluded.visitor_score,
                    business_alignment=excluded.business_alignment,
                    last_checked=excluded.last_checked
                """,
                (
                    src.source_id,
                    src.name,
                    src.url,
                    src.ingestion_type,
                    src.credibility_score,
                    json.dumps(src.topics),
                    src.cadence,
                    src.visitor_score,
                    src.business_alignment,
                    last_checked.isoformat() if last_checked else None,
                ),
            )
        conn.commit()
    save_catalog(list(sources))


def _serialize_sources(payload: Sequence[dict]) -> List[SourceMetadata]:
    sources: List[SourceMetadata] = []
    for entry in payload:
        sources.append(SourceMetadata(**entry))
    return sources


def fetch_sources() -> List[SourceMetadata]:
    ensure_schema()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT source_id, name, url, ingestion_type, credibility_score, topics, cadence, visitor_score, business_alignment, last_checked FROM sources"
        ).fetchall()
    sources: List[SourceMetadata] = []
    for row in rows:
        sources.append(
            SourceMetadata(
                source_id=row[0],
                name=row[1],
                url=row[2],
                ingestion_type=row[3],
                credibility_score=row[4],
                topics=json.loads(row[5] or "[]"),
                cadence=row[6],
                visitor_score=row[7],
                business_alignment=row[8],
                last_checked=datetime.fromisoformat(row[9]) if row[9] else None,
            )
        )
    if not sources and CATALOG_PATH.exists():
        with CATALOG_PATH.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        return _serialize_sources(data)
    return sources


def save_catalog(sources: List[SourceMetadata]) -> None:
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = [src.dict() for src in sources]
    with CATALOG_PATH.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, default=str)


def seed_db_from_catalog(catalog_path: Path | None = None) -> List[SourceMetadata]:
    """Load a JSON catalog and persist it to SQLite."""

    path = catalog_path or CATALOG_PATH
    if not path.exists():  # pragma: no cover - sanity guard
        raise FileNotFoundError(f"Catalog file {path} is missing")
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    sources = _serialize_sources(payload)
    upsert_sources(sources)
    return sources


def export_catalog_from_db(target_path: Path | None = None) -> List[SourceMetadata]:
    """Persist the current SQLite snapshot back to JSON."""

    sources = fetch_sources()
    path = target_path or CATALOG_PATH
    payload = [src.dict() for src in sources]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, default=str)
    return sources


def load_feedback() -> dict:
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not FEEDBACK_PATH.exists():
        FEEDBACK_PATH.write_text(json.dumps({"last_request_iso": None, "requests": [], "responses": []}, indent=2))
    with FEEDBACK_PATH.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def save_feedback(payload: dict) -> None:
    with FEEDBACK_PATH.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2, default=str)


def consume_feedback_responses() -> List[FeedbackResponse]:
    data = load_feedback()
    responses = [FeedbackResponse(**resp) for resp in data.get("responses", [])]
    data["responses"] = []
    save_feedback(data)
    return responses


def main() -> None:
    parser = argparse.ArgumentParser(description="Storage utilities for catalogs and feedback")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser(
        "seed", help="Populate the SQLite database from a JSON catalog"
    )
    seed_parser.add_argument(
        "--catalog",
        type=Path,
        default=CATALOG_PATH,
        help="Path to the JSON catalog (defaults to data/source_catalog.json)",
    )

    dump_parser = subparsers.add_parser(
        "dump", help="Export the SQLite catalog back to JSON"
    )
    dump_parser.add_argument(
        "--catalog",
        type=Path,
        default=CATALOG_PATH,
        help="Path to the JSON file that will receive the export",
    )

    args = parser.parse_args()
    if args.command == "seed":
        sources = seed_db_from_catalog(args.catalog)
        print(f"Seeded {len(sources)} sources into {DB_PATH}")
    elif args.command == "dump":
        sources = export_catalog_from_db(args.catalog)
        print(f"Exported {len(sources)} sources to {args.catalog}")


if __name__ == "__main__":
    main()
