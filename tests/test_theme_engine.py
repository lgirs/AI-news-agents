from agents.theme_engine import ThemeEngine


def test_theme_engine_uses_stub_when_unavailable(monkeypatch, tmp_path):
    engine = ThemeEngine()

    class DummyResponse:
        def raise_for_status(self):
            raise RuntimeError("network down")

    monkeypatch.setattr("agents.theme_engine.http_get", lambda *_, **__: DummyResponse())
    theme = engine.get_theme()
    assert "Helsinki" in theme.weather["summary"]
    assert theme.palette
