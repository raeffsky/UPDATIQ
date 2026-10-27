#!/usr/bin/env python3
"""Sync current curated MLBB item builds from MLBBHub hero build pages."""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

SOURCE = "https://mlbbhub.com/builds"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UPDATIQ/1.0; +https://github.com/raeffsky/UPDATIQ)"}
ITEM_PATH = re.compile(r"/images/items/([^/?#]+)\.(?:png|webp|jpe?g)", re.I)


def parse_build_page(session, hero):
    url = f"{SOURCE}/{hero['slug']}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    # MLBBHub renders curated loadouts as groups of item icons. Keep the first complete
    # six-item loadout and its source image URLs; avoid inventing items when markup changes.
    candidates = []
    for container in soup.select("main section, main article, main [class*='build'], main [class*='loadout'], main [class*='gallery']"):
        items = []
        seen = set()
        for img in container.select('img[src*="/images/items/"]'):
            src = img.get("src", "")
            match = ITEM_PATH.search(src)
            if not match:
                continue
            name = (img.get("alt") or img.get("title") or match.group(1)).strip()
            key = match.group(1).lower()
            if key not in seen:
                items.append({"name": name, "image": urljoin("https://mlbbhub.com", src)})
                seen.add(key)
        if len(items) >= 6:
            candidates.append(items[:6])
    if not candidates:
        # Fallback for pages where item icons are not nested under main.
        items, seen = [], set()
        for img in soup.select('img[src*="/images/items/"]'):
            match = ITEM_PATH.search(img.get("src", ""))
            if not match:
                continue
            key = match.group(1).lower()
            if key not in seen:
                items.append({"name": (img.get("alt") or match.group(1)).strip(), "image": urljoin("https://mlbbhub.com", img["src"])})
                seen.add(key)
        if len(items) >= 6:
            candidates = [items[:6]]
    if not candidates:
        raise RuntimeError(f"No complete six-item build detected for {hero['slug']}")
    return {"title": "Рекомендуемая сборка", "items": candidates[0], "sourceUrl": url, "updatedAt": datetime.now(timezone.utc).isoformat()}


def main():
    tiers_path = Path("mlbbnexus-tiers.json")
    if not tiers_path.exists():
        raise SystemExit("mlbbnexus-tiers.json is missing")
    tiers = json.loads(tiers_path.read_text(encoding="utf-8"))
    heroes = {}
    for lane in tiers.get("lanes", {}).values():
        for hero in lane.get("heroes", []):
            if hero.get("slug"):
                heroes[hero["slug"]] = hero
    if len(heroes) < 50:
        raise SystemExit(f"Only {len(heroes)} unique heroes in tier data; refusing to sync builds")
    session = requests.Session()
    session.headers.update(HEADERS)
    result = {"source": "MLBBHub", "sourceUrl": SOURCE, "updatedAt": datetime.now(timezone.utc).isoformat(), "builds": {}}
    errors = []
    for index, hero in enumerate(heroes.values(), 1):
        try:
            result["builds"][hero["slug"]] = parse_build_page(session, hero)
            print(f"OK {hero['name']}: 6 items")
        except Exception as exc:
            errors.append(f"{hero['name']}: {exc}")
            print(f"WARNING {hero['name']}: {exc}", file=sys.stderr)
        time.sleep(0.3)
    if len(result["builds"]) < max(40, int(len(heroes) * 0.6)):
        raise SystemExit(f"Only {len(result['builds'])}/{len(heroes)} builds parsed; refusing to replace current data. " + "; ".join(errors[:8]))
    Path("mlbb-hero-builds.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Saved {len(result['builds'])} current hero builds; failed {len(errors)}")


if __name__ == "__main__":
    main()
