import json
from datetime import datetime

from agents.models import SourceMetadata
from agents import storage


def test_upsert_and_fetch_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sources.db")
    monkeypatch.setattr(storage, "CATALOG_PATH", tmp_path / "catalog.json")
    sample = SourceMetadata(
        source_id="test",
        name="Test Source",
        url="https://example.com/rss",
        ingestion_type="rss",
        credibility_score=0.9,
        topics=["business"],
        cadence="daily",
        visitor_score=0.8,
        business_alignment=0.85,
        last_checked=datetime.utcnow(),
    )
    storage.upsert_sources([sample])
    result = storage.fetch_sources()
    assert result[0].source_id == "test"


def test_seed_db_from_catalog(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "sources.db")
    monkeypatch.setattr(storage, "CATALOG_PATH", tmp_path / "catalog.json")
    catalog_payload = [
        {
            "source_id": "seeded",
            "name": "Seeded Outlet",
            "url": "https://seeded.example.com/rss",
            "ingestion_type": "rss",
            "credibility_score": 0.8,
            "topics": ["business"],
            "cadence": "weekly",
            "visitor_score": 0.75,
            "business_alignment": 0.82,
            "last_checked": datetime.utcnow().isoformat(),
        }
    ]
    storage.CATALOG_PATH.write_text(json.dumps(catalog_payload))
    seeded = storage.seed_db_from_catalog()
    assert seeded[0].name == "Seeded Outlet"
    round_trip = storage.fetch_sources()
    assert round_trip[0].source_id == "seeded"
