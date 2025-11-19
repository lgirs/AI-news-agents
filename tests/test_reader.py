from datetime import date

from agents.reader import ReaderAgent


def test_summarize_prefers_newspaper(monkeypatch):
    agent = ReaderAgent(target_date=date.today())

    def fake_newspaper(self, url):
        return "newspaper summary"

    def fake_readability(self, url):
        return "readability summary"

    monkeypatch.setattr(ReaderAgent, "_try_newspaper_summary", fake_newspaper)
    monkeypatch.setattr(ReaderAgent, "_try_readability_summary", fake_readability)

    summary = agent._summarize_article("https://example.com", "fallback")
    assert summary == "newspaper summary"


def test_summarize_falls_back_to_input(monkeypatch):
    agent = ReaderAgent(target_date=date.today())

    monkeypatch.setattr(ReaderAgent, "_try_newspaper_summary", lambda self, url: None)
    monkeypatch.setattr(ReaderAgent, "_try_readability_summary", lambda self, url: None)

    fallback = "fallback text" * 30
    summary = agent._summarize_article("https://example.com", fallback)
    assert summary.startswith("fallback text")
    assert len(summary) <= 280


def test_summarize_handles_missing_optional_dependencies(monkeypatch):
    agent = ReaderAgent(target_date=date.today())

    # Simulate optional wheels not being installed
    monkeypatch.setattr("agents.reader.Article", None, raising=False)
    monkeypatch.setattr("agents.reader.Document", None, raising=False)
    monkeypatch.setattr(ReaderAgent, "_try_newspaper_summary", lambda self, url: None)
    monkeypatch.setattr(ReaderAgent, "_try_readability_summary", lambda self, url: None)

    summary = agent._summarize_article("https://example.com", "fallback summary")
    assert summary.startswith("fallback summary")
