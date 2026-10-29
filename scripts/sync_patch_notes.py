#!/usr/bin/env python3
"""Fetch current original-server MLBB patch-note entries into official-news.json.

The app receives structured, detailed patch data at build time. Keep source URLs
attached to every entry; never synthesize missing numeric values.
"""
import json
import re
import sys
import time
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
    """Extract the patch body only; exclude site navigation, ads, FAQ and promos."""
    for tag in node.select("script,style,nav,footer,header,button,form,svg,iframe,aside"):
        tag.decompose()
    lines = []
    seen = set()
    stop_patterns = (
        r"^frequently asked questions",
        r"^faq\b",
        r"^additional resources",
        r"^related articles",
        r"^you may also like",
        r"^advertisement$",
        r"^advert$",
    )
    junk_patterns = (
        r"^advertisement$",
        r"^advert$",
        r"^read more$",
        r"^click here$",
    )
    for el in node.select("h1,h2,h3,h4,p,li,tr,blockquote"):
        text = " ".join(el.get_text(" ", strip=True).split())
        if not text:
            continue
        low = text.casefold()
        if any(re.search(pattern, low, re.I) for pattern in stop_patterns):
            break
        if any(re.search(pattern, low, re.I) for pattern in junk_patterns):
            continue
        # Drop FAQ-style teaser copy that points readers back to the webpage.
        if ("most common questions" in low and "patch" in low) or (
            "full list" in low and "on this page" in low
        ):
            continue
        if text not in seen:
            lines.append(text)
            seen.add(text)
    return "\n\n".join(lines)

def find_structured_patch(value):
    if isinstance(value, dict):
        if isinstance(value.get("heroChanges"), list) and value["heroChanges"]:
            return value
        for child in value.values():
            found = find_structured_patch(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_structured_patch(child)
            if found:
                return found
    elif isinstance(value, str) and len(value) > 100:
        try:
            return find_structured_patch(json.loads(value))
        except (ValueError, TypeError):
            return None
    return None

def extract_structured_patch(soup):
    for script in soup.select("script"):
        raw = script.string or script.get_text()
        if not raw or "heroName" not in raw:
            continue
        # MLBBHub embeds its full patch model in a Next.js Flight payload.
        for match in re.finditer(r'"heroChanges"\s*:', raw):
            start = raw.rfind("{", 0, match.start())
            if start < 0:
                continue
            depth = 0
            quoted = escaped = False
            for pos in range(start, len(raw)):
                ch = raw[pos]
                if quoted:
                    if escaped: escaped = False
                    elif ch == "\\": escaped = True
                    elif ch == '"': quoted = False
                else:
                    if ch == '"': quoted = True
                    elif ch == "{": depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            candidate = raw[start:pos + 1]
                            try:
                                obj = json.loads(candidate)
                                found = find_structured_patch(obj)
                                if found:
                                    return found
                            except (ValueError, TypeError):
                                pass
                            break
        # Also try script contents that are pure JSON.
        try:
            found = find_structured_patch(json.loads(raw))
            if found:
                return found
        except (ValueError, TypeError):
            pass
    return None

def render_structured_patch(patch):
    sections = []
    for hero in patch.get("heroChanges", []):
        name = str(hero.get("heroName") or hero.get("name") or "Герой")
        kind = str(hero.get("changeType") or "").upper()
        lines = [f"{name} · {kind}" if kind else name]
        summary = str(hero.get("summary") or "").strip()
        if summary:
            lines.append(summary)
        for detail in hero.get("details", []):
            label = " · ".join(str(detail.get(k) or "").strip() for k in ("skill", "attribute") if detail.get(k))
            before, after = detail.get("from"), detail.get("to")
            note = str(detail.get("note") or "").strip()
            if before is not None or after is not None:
                lines.append(f"{label}: {before if before is not None else '—'} → {after if after is not None else '—'}")
            elif note:
                lines.append(f"{label}: {note}" if label else note)
        sections.append("\n\n".join(lines))
    for group in patch.get("systemChanges", []):
        if group.get("category"):
            sections.append(str(group["category"]))
        for item in group.get("items", []):
            text = "\n".join(str(item.get(k) or "").strip() for k in ("title", "description") if item.get(k))
            if text:
                sections.append(text)
    return "\n\n".join(sections)

def split_translation_chunks(text, limit=1800):
    """Split at paragraph boundaries, then split oversized paragraphs safely."""
    chunks = []
    current = ""
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        pieces = [paragraph[i:i + limit] for i in range(0, len(paragraph), limit)]
        for piece in pieces:
            if current and len(current) + len(piece) + 2 > limit:
                chunks.append(current)
                current = piece
            else:
                current = (current + "\n\n" + piece).strip()
    if current:
        chunks.append(current)
    return chunks

def translate_to_russian(text, session):
    """Translate the entire article with retry/backoff for Google Translate rate limits."""
    endpoint = "https://translate.googleapis.com/translate_a/single"
    translated = []
    chunks = split_translation_chunks(text)
    for index, chunk in enumerate(chunks):
        last_error = None
        for attempt in range(6):
            try:
                response = session.post("https://translate.google.com/translate_a/single", data={
                    "client": "gtx", "sl": "en", "tl": "ru", "dt": "t", "q": chunk
                }, timeout=45)
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = RuntimeError(f"Translation service HTTP {response.status_code}")
                    time.sleep(min(20 * (attempt + 1), 120))
                    continue
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
                last_error = None
                break
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                last_error = exc
                if attempt < 5:
                    time.sleep(min(8 * (attempt + 1), 40))
        if last_error:
            raise last_error
        # Avoid hammering a public translation endpoint across long articles.
        if index < len(chunks) - 1:
            time.sleep(3)
    return "\n\n".join(translated)

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
        # Extract real stat changes from the structured model embedded by MLBBHub.
        structured = extract_structured_patch(article_soup)
        card_lines = []
        if structured:
            body = render_structured_patch(structured)
        else:
            roots = article_soup.select("main, article, [class*='patch'], [class*='content']")
            card_seen = set()
            card_selector = (
                "[class*='hero-card'], [class*='change-card'], [class*='patch-card'], "
                "[class*='stat-card'], [class*='skill-card'], [class*='hero-change'], "
                "[class*='balance-card'], [class*='change-item'], [class*='patch-item']"
            )
            for root in roots:
                for card in root.select(card_selector):
                    if card.find_parent(class_=re.compile(r"(hero-card|change-card|patch-card|stat-card|skill-card|hero-change|balance-card|change-item|patch-item)")):
                        continue
                    text = " ".join(card.get_text(" ", strip=True).split())
                    if len(text) >= 35 and text not in card_seen:
                        card_lines.append(text)
                        card_seen.add(text)
            body = "\n\n".join(card_lines) if card_lines else clean_text(candidates[0])
        if structured and not re.search(r"\b\d+\s*(?:→|->|to)\s*\d+", body):
            raise RuntimeError(f"Structured patch data found for {version}, but numeric before/after changes were not rendered.")
        if len(body) < 700:
            print(f"Skipping {version}: article body too short ({len(body)} chars)", file=sys.stderr)
            continue
        if card_lines and not re.search(r"\b\d+\s*(?:→|->|to)\s*\d+", body):
            print(f"Warning: detected change cards for {version}, but no numeric before/after values; verify source markup.", file=sys.stderr)
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
