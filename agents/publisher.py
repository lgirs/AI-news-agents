"""Publisher agent that builds a daily HTML page."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .logger import logger
from .models import Digest
from .theme_engine import ThemeEngine

TEMPLATES_DIR = Path("templates")
OUTPUT_DIR = Path("dist")


def load_digest(target_date: str | None = None) -> Digest:
    if target_date:
        digest_path = Path("digests") / f"digest_{target_date}.json"
    else:
        digests = sorted(Path("digests").glob("digest_*.json"))
        if not digests:
            raise FileNotFoundError("No digests available")
        digest_path = digests[-1]
    logger.info("Loading digest from %s", digest_path)
    payload = json.loads(digest_path.read_text())
    return Digest(**payload)


def build_html(digest: Digest) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(["html", "xml"]))
    template = env.get_template("daily_digest.html.j2")
    theme = ThemeEngine().get_theme()
    html = template.render(digest=digest.dict(), theme=theme.dict())
    return html


def publish(digest: Digest) -> Path:
    html = build_html(digest)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "index.html"
    path.write_text(html, encoding="utf-8")
    logger.success("Published %s", path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Publisher agent")
    parser.add_argument("--date", type=str, help="Digest date YYYY-MM-DD", default=None)
    args = parser.parse_args()
    digest = load_digest(args.date)
    publish(digest)


if __name__ == "__main__":
    main()
