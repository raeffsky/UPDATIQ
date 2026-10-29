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
HERO_PAGE = "https://mlbbhub.com/heroes"
EXTRA_HEROES = {"marcel": {"slug": "marcel", "name": "Marcel"}}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UPDATIQ/1.0; +https://github.com/raeffsky/UPDATIQ)"}
ITEM_PATH = re.compile(r"/images/items/([^/?#]+)\.(?:png|webp|jpe?g)", re.I)


def parse_build_page(session, hero):
    url = f"{SOURCE}/{hero['slug']}"
    urls = [url, f"{HERO_PAGE}/{hero['slug']}"]
    soup = None
    page_url = url
    for candidate_url in urls:
        try:
            response = session.get(candidate_url, timeout=30)
            response.raise_for_status()
            candidate_soup = BeautifulSoup(response.text, "html.parser")
            if candidate_soup.select('img[src*="/images/items/"]'):
                soup = candidate_soup
                page_url = candidate_url
                break
        except Exception as exc:
            print(f"INFO {hero['slug']}: source page unavailable at {candidate_url}: {exc}", file=sys.stderr)
    if soup is None:
        raise RuntimeError(f"No MLBBHub build page found for {hero['slug']}")
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
    return {"title": "Рекомендуемая сборка", "items": candidates[0], "sourceUrl": page_url, "updatedAt": datetime.now(timezone.utc).isoformat()}


def fetch_catalog_heroes(session):
    """Read the full hero catalog, not just the subset appearing in the current ranked tier list."""
    response = session.get(HERO_PAGE, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    catalog = {}
    for link in soup.select('a[href*="/heroes/"]'):
        href = link.get("href", "").split("?", 1)[0].rstrip("/")
        match = re.search(r"/heroes/([^/]+)$", href, re.I)
        if not match:
            continue
        slug = match.group(1).lower()
        name = link.get_text(" ", strip=True)
        if not name or slug in {"", "heroes"}:
            continue
        # Ignore navigation links that do not represent a named hero.
        if len(name) > 80 or name.lower() in {"heroes", "all heroes", "browse all heroes"}:
            continue
        img = link.find("img")
        image = img.get("src", "") if img else ""
        catalog.setdefault(slug, {"slug": slug, "name": name, "image": urljoin("https://mlbbhub.com", image) if image else ""})
    if len(catalog) < 120:
        raise RuntimeError(f"Only {len(catalog)} heroes found in MLBBHub catalog; refusing to treat a partial roster as complete")
    return catalog


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
    for slug, hero in EXTRA_HEROES.items():
        heroes.setdefault(slug, hero)
    if len(heroes) < 50:
        raise SystemExit(f"Only {len(heroes)} unique heroes in tier data; refusing to sync builds")
    session = requests.Session()
    session.headers.update(HEADERS)
    catalog = fetch_catalog_heroes(session)
    # Merge the full 133-hero catalog with lane-tier data; tier lists omit heroes
    # that are not currently represented in ranked stats.
    for slug, hero in catalog.items():
        heroes.setdefault(slug, hero)
    print(f"Full hero catalog: {len(catalog)} heroes; build attempts: {len(heroes)}")
    if len(heroes) < 120:
        raise SystemExit(f"Only {len(heroes)} heroes available after catalog merge; refusing partial sync")
    result = {"source": "MLBBHub", "sourceUrl": SOURCE, "updatedAt": datetime.now(timezone.utc).isoformat(), "heroes": sorted(catalog.values(), key=lambda h: h["name"].casefold()), "builds": {}}
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
