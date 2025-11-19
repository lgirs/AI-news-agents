"""Pydantic models for the AI news agent workflow."""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Literal, Optional

from .pydantic_compat import BaseModel, Field, HttpUrl


class SourceMetadata(BaseModel):
    """Normalized metadata for a news source."""

    source_id: str
    name: str
    url: HttpUrl
    ingestion_type: Literal["rss", "html"]
    credibility_score: float = Field(ge=0, le=1)
    topics: List[str]
    cadence: str
    visitor_score: float = Field(ge=0, le=1)
    business_alignment: float = Field(ge=0, le=1)
    last_checked: Optional[datetime] = None


class Story(BaseModel):
    """Individual story after parsing and scoring."""

    title: str
    summary: str
    url: HttpUrl
    source_id: str
    source_name: str
    published_at: datetime
    relevance: float = Field(ge=0, le=1)
    topics: List[str]


class DigestQuote(BaseModel):
    text: str
    author: str


class Digest(BaseModel):
    date: date
    generated_at: datetime
    stories: List[Story]
    topics: Dict[str, List[Story]]
    timeline: List[Story]
    quote: DigestQuote
    signal_score: int = Field(ge=0, le=5)


class ThemeContext(BaseModel):
    title: str
    subtitle: str
    palette: Dict[str, str]
    weather: Dict[str, str]


class FeedbackRequest(BaseModel):
    requested_at: datetime
    notes: str


class FeedbackResponse(BaseModel):
    submitted_at: datetime
    source_id: Optional[str]
    action: Literal["add", "remove", "adjust"]
    payload: Dict[str, str]


class WeatherPayload(BaseModel):
    location: str
    season: str
    condition: str
    temperature_c: float
