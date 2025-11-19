from datetime import datetime, timezone

from agents.models import FeedbackResponse, SourceMetadata
from agents.researcher import ResearcherAgent


def sample_source(source_id: str = "base") -> SourceMetadata:
    return SourceMetadata(
        source_id=source_id,
        name="Base Source",
        url="https://example.com/rss",
        ingestion_type="rss",
        credibility_score=0.8,
        topics=["business"],
        cadence="daily",
        visitor_score=0.75,
        business_alignment=0.78,
        last_checked=datetime.now(timezone.utc),
    )


def test_apply_feedback_adds_sources():
    agent = ResearcherAgent()
    responses = [
        FeedbackResponse(
            submitted_at=datetime.now(timezone.utc),
            source_id="new_source",
            action="add",
            payload={
                "name": "New Source",
                "url": "https://news.example.com/ai",
                "ingestion_type": "html",
                "credibility_score": 0.9,
                "topics": ["policy"],
                "cadence": "weekly",
                "visitor_score": 0.7,
                "business_alignment": 0.8,
            },
        )
    ]
    expanded = agent.apply_feedback([sample_source()], responses)
    ids = {src.source_id for src in expanded}
    assert ids == {"base", "new_source"}


def test_apply_feedback_adjusts_sources():
    agent = ResearcherAgent()
    responses = [
        FeedbackResponse(
            submitted_at=datetime.now(timezone.utc),
            source_id="base",
            action="adjust",
            payload={"credibility_score": 0.95, "topics": ["business", "markets"]},
        )
    ]
    expanded = agent.apply_feedback([sample_source()], responses)
    target = next(src for src in expanded if src.source_id == "base")
    assert target.credibility_score == 0.95
    assert target.topics == ["business", "markets"]
