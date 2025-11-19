"""Weather-aware theming utilities."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from .http_client import http_get
from .logger import logger
from .models import ThemeContext

PALETTES_PATH = Path("themes/palettes.json")
WEATHER_STUB = Path("data/weather_stub.json")
WTTR_URL = "https://wttr.in/Helsinki?format=j1"


class ThemeEngine:
    def __init__(self) -> None:
        self.palettes = json.loads(PALETTES_PATH.read_text())

    def get_theme(self) -> ThemeContext:
        weather = self._fetch_weather()
        palette = self._select_palette(weather)
        title = self._compose_title(weather)
        subtitle = f"Signals tuned for Helsinki • {weather['season'].title()} {int(weather['temperature_c'])}°C"
        return ThemeContext(title=title, subtitle=subtitle, palette=palette, weather={"summary": self._format_weather(weather)})

    def _fetch_weather(self) -> Dict[str, str]:
        try:
            response = http_get(WTTR_URL, timeout=10)
            response.raise_for_status()
            payload = response.json()
            condition = payload["current_condition"][0]["weatherDesc"][0]["value"].lower()
            temp = float(payload["current_condition"][0]["temp_C"])
            season = self._season_from_month(datetime.utcnow().month)
            return {
                "location": "Helsinki",
                "season": season,
                "condition": "snow" if "snow" in condition else ("rain" if "rain" in condition else "cloudy"),
                "temperature_c": temp,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Weather fetch failed, using stub: %s", exc)
            return json.loads(WEATHER_STUB.read_text())

    def _select_palette(self, weather: Dict[str, str]) -> Dict[str, str]:
        season_palettes = self.palettes.get(weather["season"], {})
        palette = season_palettes.get(weather["condition"]) or next(iter(season_palettes.values()))
        return palette

    def _compose_title(self, weather: Dict[str, str]) -> str:
        descriptors = {
            "sunny": "Bright Signals",
            "cloudy": "Steady Signals",
            "snow": "Crystal Signals",
            "rain": "Resilient Signals",
            "wind": "Shifting Signals",
        }
        return descriptors.get(weather["condition"], "Daily Signals")

    def _format_weather(self, weather: Dict[str, str]) -> str:
        return f"{weather['location']} • {weather['condition'].title()} • {weather['temperature_c']}°C"

    @staticmethod
    def _season_from_month(month: int) -> str:
        if month in (12, 1, 2):
            return "winter"
        if month in (3, 4, 5):
            return "spring"
        if month in (6, 7, 8):
            return "summer"
        return "autumn"
