#!/usr/bin/env python3
"""Fetch current original-server MLBB patch-note entries into official-news.json.

The app receives structured, detailed patch data at build time. Keep source URLs
attached to every entry; never synthesize missing numeric values.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "official-news.json"
INDEX_URL = "https://mlbbhub.com/patch-notes"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UPDATIQ/1.0; +https://github.com/raeffsky/UPDATIQ)"}

def clean_text(node):
    for tag in node.select("script,style,nav,footer,header,button,form,svg"):
        tag.decompose()
    lines = []
    for el in node.select("h1,h2,h3,h4,p,li,tr,blockquote"):
        text = " ".join(el.get_text(" ", strip=True).split())
        if text and (not lines or lines[-1] != text):
            lines.append(text)
    return "\n\n".join(lines)

def translate_to_russian(text, session):
    """Translate complete article text in bounded chunks while preserving all figures."""
    chunks = []
    current = ""
    # Split on paragraph boundaries so each request remains comfortably below URL limits.
    for paragraph in text.split("\\n\\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(current) + len(paragraph) + 2 > 3000 and current:
            chunks.append(current)
            current = ""
        current = (current + "\\n\\n" + paragraph).strip()
    if current:
        chunks.append(current)

    translated = []
    endpoint = "https://translate.googleapis.com/translate_a/single"
    for chunk in chunks:
        response = session.get(endpoint, params={
            "client": "gtx", "sl": "en", "tl": "ru", "dt": "t", "q": chunk
        }, timeout=45)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
            raise RuntimeError("Translation service returned an unexpected response.")
        translated_chunk = "".join(
            part[0] for part in payload[0]
            if isinstance(part, list) and part and isinstance(part[0], str)
        )
        if not translated_chunk.strip():
            raise RuntimeError("Translation service returned an empty translation.")
        translated.append(translated_chunk)
    return "\\n\\n".join(translated)

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    response = session.get(INDEX_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for a in soup.select('a[href*="/patch-notes/original/"]'):
        href = urljoin(INDEX_URL, a.get("href", ""))
        match = re.search(r"/patch-notes/original/([0-9.]+[a-z]?)", href, re.I)
        if match and href not in [x[1] for x in links]:
            label = " ".join(a.get_text(" ", strip=True).split())
            links.append((match.group(1), href, label))
    if not links:
        raise RuntimeError("Patch index returned no original-server patch links; leaving existing data unchanged.")

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    existing = data.get("articles", [])
    retained = [a for a in existing if not str(a.get("id", "")).startswith("mlbb-patch-")]
    patches = []
    for version, url, label in links[:12]:
        page = session.get(url, timeout=30)
        page.raise_for_status()
        article_soup = BeautifulSoup(page.text, "html.parser")
        candidates = article_soup.select("main, article, [class*='patch'], [class*='content']")
        candidates.sort(key=lambda n: len(n.get_text(" ", strip=True)), reverse=True)
        if not candidates:
            print(f"Skipping {version}: no article body detected", file=sys.stderr)
            continue
        body = clean_text(candidates[0])
        if len(body) < 700:
            print(f"Skipping {version}: article body too short ({len(body)} chars)", file=sys.stderr)
            continue
        title = f"MLBB Patch Notes {version}"
        date_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+20\d{2}", page.text, re.I)
        date = date_match.group(0) if date_match else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            body_ru = translate_to_russian(body, session)
        except Exception as exc:
            raise RuntimeError(f"Russian translation failed for patch {version}; refusing to publish English-only patch notes: {exc}") from exc
        patches.append({
            "id": f"mlbb-patch-{version}",
            "title": title,
            "titleRu": f"Патчноуты MLBB {version}",
            "publishedAt": date,
            "summary": f"Original-server patch notes {version}.",
            "summaryRu": f"Полные патчноуты основного сервера MLBB {version}: изменения героев, экипировки и поля боя.",
            "fullText": body,
            "fullTextRu": body_ru,
            "url": url,
            "source": "MLBBHub (подробный архив патчноутов)",
            "language": "ru",
            "originalLanguage": "en",
            "category": "update",
            "patchVersion": version
        })
    if not patches:
        raise RuntimeError("No usable patch articles were fetched; leaving existing data unchanged.")
    # Newest entries first, with all non-patch official news preserved.
    data["articles"] = patches + retained
    data.setdefault("source", {})["patchNotesUrl"] = INDEX_URL
    data["source"]["patchNotesCheckedAt"] = datetime.now(timezone.utc).isoformat()
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Synced {len(patches)} detailed patch-note entries: " + ", ".join(p["patchVersion"] for p in patches))

if __name__ == "__main__":
    main()
