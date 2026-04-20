import os
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from app.config import get_settings


def fetch_page(url: str, css_selector: str | None = None) -> tuple[str, str]:
    s = get_settings()
    resp = requests.get(url, timeout=s.request_timeout)
    resp.raise_for_status()
    html = resp.text

    soup = BeautifulSoup(html, "html.parser")
    if css_selector:
        blocks = soup.select(css_selector)
        text = "\n".join([b.get_text(" ", strip=True) for b in blocks])
    else:
        text = soup.get_text(" ", strip=True)

    return html, text


def save_html_snapshot(source_id: int, html: str) -> str:
    out_dir = os.path.join(get_settings().output_dir, "snapshots")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"source_{source_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
