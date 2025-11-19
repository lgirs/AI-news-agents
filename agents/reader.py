"""News reader agent that builds daily digests."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.parse import urljoin

try:  # pragma: no cover - optional dependency
    import feedparser  # type: ignore
except Exception:  # pragma: no cover
    feedparser = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from dateutil import parser as dateparser  # type: ignore
except Exception:  # pragma: no cover
    dateparser = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from readability import Document  # type: ignore
except Exception:  # pragma: no cover
    Document = None

try:  # pragma: no cover - optional dependency
    from newspaper import Article  # type: ignore
except Exception:  # pragma: no cover
    Article = None

from .http_client import http_get
from .logger import logger
from .models import Digest, DigestQuote, SourceMetadata, Story
from .storage import fetch_sources

DIGESTS_DIR = Path("digests")
DEFAULT_QUOTE = DigestQuote(text="AI shifts economic power when paired with viable business models.", author="Editorial Team")


class ReaderAgent:
    def __init__(self, target_date: date | None = None) -> None:
        self.target_date = target_date or datetime.now(timezone.utc).date()
        DIGESTS_DIR.mkdir(parents=True, exist_ok=True)

    def run(self) -> Path:
        logger.info("Starting reader for %s", self.target_date)
        sources = fetch_sources()
        stories = self._collect_stories(sources)
        digest = self._build_digest(stories)
        output_path = DIGESTS_DIR / f"digest_{self.target_date.isoformat()}.json"
        output_path.write_text(digest.json(indent=2, default=str))
        logger.success("Digest written to %s", output_path)
        return output_path

    def _collect_stories(self, sources: Iterable[SourceMetadata]) -> List[Story]:
        collected: List[Story] = []
        for source in sources:
            try:
                if source.ingestion_type == "rss":
                    collected.extend(self._parse_rss(source))
                else:
                    collected.extend(self._scrape_html(source))
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to read %s: %s", source.name, exc)
        return self._dedupe(collected)

    def _parse_rss(self, source: SourceMetadata) -> List[Story]:
        if feedparser is None:
            raise RuntimeError("feedparser is required to parse RSS sources")
        logger.debug("Parsing RSS for %s", source.name)
        feed = feedparser.parse(source.url)
        stories = []
        for entry in feed.entries[:10]:
            published = self._parse_date(entry.get("published") or entry.get("updated"))
            summary_html = entry.get("summary", "")
            summary = (
                BeautifulSoup(summary_html, "html.parser").get_text()
                if BeautifulSoup
                else summary_html
            )
            stories.append(
                self._build_story(
                    title=entry.get("title", "Untitled"),
                    summary=summary,
                    url=entry.get("link"),
                    published=published,
                    source=source,
                )
            )
        return stories

    def _scrape_html(self, source: SourceMetadata) -> List[Story]:
        logger.debug("Scraping HTML for %s", source.name)
        if BeautifulSoup is None:
            raise RuntimeError("beautifulsoup4 is required to scrape HTML sources")
        response = http_get(source.url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        anchors = soup.select("a")
        stories = []
        seen = set()
        for anchor in anchors:
            href = anchor.get("href")
            title = anchor.get_text(strip=True)
            if not href or not title or len(title) < 40:
                continue
            if href in seen:
                continue
            seen.add(href)
            absolute_url = self._resolve_url(source.url, href)
            story_summary = self._summarize_article(absolute_url, title)
            stories.append(
                self._build_story(
                    title=title,
                    summary=story_summary,
                    url=absolute_url,
                    published=datetime.now(timezone.utc),
                    source=source,
                )
            )
            if len(stories) >= 5:
                break
        return stories

    def _build_story(self, title: str, summary: str, url: str, published: datetime, source: SourceMetadata) -> Story:
        relevance = min(1.0, (source.credibility_score + source.business_alignment) / 2)
        topics = source.topics
        return Story(
            title=title,
            summary=summary[:280],
            url=url,
            source_id=source.source_id,
            source_name=source.name,
            published_at=published,
            relevance=relevance,
            topics=topics,
        )

    def _dedupe(self, stories: Iterable[Story]) -> List[Story]:
        seen: Dict[str, Story] = {}
        for story in stories:
            key = story.url.split("?")[0]
            if key not in seen or story.relevance > seen[key].relevance:
                seen[key] = story
        return list(seen.values())

    def _build_digest(self, stories: List[Story]) -> Digest:
        topics_map: Dict[str, List[Story]] = defaultdict(list)
        for story in stories:
            for topic in story.topics:
                topics_map[topic].append(story)
        timeline = sorted(stories, key=lambda s: s.published_at, reverse=True)[:8]
        signal_score = min(5, max(1, round(sum(story.relevance for story in stories) / max(len(stories), 1) * 5)))
        digest = Digest(
            date=self.target_date,
            generated_at=datetime.now(timezone.utc),
            stories=stories,
            topics=topics_map,
            timeline=timeline,
            quote=DEFAULT_QUOTE,
            signal_score=signal_score,
        )
        return digest

    @staticmethod
    def _parse_date(value: str | None) -> datetime:
        if not value or dateparser is None:
            return datetime.now(timezone.utc)
        return dateparser.parse(value).astimezone(timezone.utc)

    @staticmethod
    def _resolve_url(base: str, href: str) -> str:
        return href if href.startswith("http") else urljoin(base, href)

    def _summarize_article(self, url: str, fallback: str) -> str:
        summary = self._try_newspaper_summary(url)
        if not summary:
            summary = self._try_readability_summary(url)
        if not summary:
            summary = fallback
        return summary[:280]

    def _try_newspaper_summary(self, url: str) -> str | None:
        if Article is None:
            return None
        try:
            article = Article(url)
            article.download()
            article.parse()
            summary = article.summary
            if not summary:
                try:
                    article.nlp()  # type: ignore[attr-defined]
                    summary = article.summary
                except Exception:  # pragma: no cover - optional
                    summary = None
            if not summary:
                summary = article.text
            return summary.strip() if summary else None
        except Exception as exc:  # noqa: BLE001
            logger.debug("newspaper3k summary failed for %s: %s", url, exc)
            return None

    def _try_readability_summary(self, url: str) -> str | None:
        if Document is None:
            return None
        try:
            response = http_get(url, timeout=20)
            response.raise_for_status()
            document = Document(response.text)
            summary_html = document.summary(html_partial=True)
            if BeautifulSoup:
                summary_text = BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True)
            else:
                summary_text = summary_html
            return summary_text or None
        except Exception as exc:  # noqa: BLE001
            logger.debug("Readability summary failed for %s: %s", url, exc)
            return None


def main() -> None:
    parser = argparse.ArgumentParser(description="News reader agent")
    parser.add_argument("--date", type=str, help="Override date YYYY-MM-DD", default=None)
    args = parser.parse_args()
    target_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else None
    ReaderAgent(target_date=target_date).run()


if __name__ == "__main__":
    main()
