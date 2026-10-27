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
        patches.append({
            "id": f"mlbb-patch-{version}",
            "title": title,
            "titleRu": f"Патчноуты MLBB {version}",
            "publishedAt": date,
            "summary": f"Original-server patch notes {version}. Detailed hero, equipment, and battlefield changes; see source for the complete article.",
            "summaryRu": f"Патчноуты основного сервера {version}: подробные изменения героев, экипировки и поля боя.",
            "fullText": body,
            "url": url,
            "source": "MLBBHub (patch-note archive)",
            "language": "en",
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
