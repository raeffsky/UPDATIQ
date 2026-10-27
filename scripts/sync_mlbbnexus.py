#!/usr/bin/env python3
"""Sync lane-specific live tier data from MLBB Nexus into a stable local JSON file."""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://mlbbnexus.com/tier-list"
LANES = {
    "all": ("Все роли", ""),
    "exp": ("EXP", "exp"),
    "jungle": ("Лес", "jungle"),
    "mid": ("Мид", "mid"),
    "gold": ("Золото", "gold"),
    "roam": ("Роум", "roam"),
}
HEADERS = {"User-Agent": "UPDATIQ-Community-Client/1.0 (+https://github.com/raeffsky/UPDATIQ)"}
TIER_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4, "F": 5}


def number(pattern, text):
    match = re.search(pattern, text, re.I)
    return float(match.group(1)) if match else None


def fetch_lane(session, lane):
    url = BASE if not lane else f"{BASE}?lane={lane}"
    response = session.get(url, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select('[vt-name^="tier-"]')
    heroes = []
    seen = set()
    for row in rows:
        link = row.select_one('a[href*="/heroes/"]')
        if not link:
            continue
        name = link.get_text(" ", strip=True)
        slug = link.get("href", "").rstrip("/").split("/")[-1]
        if not name or not slug or slug in seen:
            continue
        text = row.get_text(" ", strip=True)
        tier_match = re.search(r"\b([SABCD])\s+tier\b", text, re.I)
        if not tier_match:
            continue
        tier = tier_match.group(1).upper()
        win = number(r"(\d{1,2}(?:\.\d+)?)%\s*[SABCD]\s+tier", text)
        pick = number(r"Pick\s*(\d{1,2}(?:\.\d+)?)%", text)
        ban = number(r"Ban\s*(\d{1,2}(?:\.\d+)?)%", text)
        img = row.select_one("img")
        image = img.get("src", "") if img else ""
        if image.startswith("/"):
            image = urljoin("https://mlbbnexus.com", image)
        heroes.append({
            "name": name, "slug": slug, "tier": tier,
            "winRate": win, "pickRate": pick, "banRate": ban,
            "image": image,
            "sourceUrl": f"https://mlbbnexus.com/heroes/{slug}",
        })
        seen.add(slug)
    if len(heroes) < 5:
        raise RuntimeError(f"Only {len(heroes)} heroes parsed from {url}; refusing to replace valid data")
    return sorted(heroes, key=lambda h: (TIER_ORDER.get(h["tier"], 9), -(h["winRate"] or 0)))


def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    result = {
        "source": "MLBB Nexus",
        "sourceUrl": "https://mlbbnexus.com/tier-list",
        "attributionUrl": "https://mlbbnexus.com/attribution/",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "rank": "All Ranks",
        "period": "7d",
        "lanes": {},
    }
    errors = []
    for key, (label, slug) in LANES.items():
        try:
            heroes = fetch_lane(session, slug)
            result["lanes"][key] = {"label": label, "heroes": heroes, "count": len(heroes)}
            print(f"{label}: {len(heroes)} heroes")
        except Exception as exc:
            errors.append(f"{label}: {exc}")
            print(f"WARNING {label}: {exc}", file=sys.stderr)
        time.sleep(1)
    if len(result["lanes"]) < 5 or any(k not in result["lanes"] for k in ("exp", "jungle", "mid", "gold", "roam")):
        raise SystemExit("Not all five lane lists were retrieved; keeping previous tier data. " + "; ".join(errors))
    out = Path("mlbbnexus-tiers.json")
    out.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Saved {out}; {sum(v['count'] for v in result['lanes'].values())} lane entries")


if __name__ == "__main__":
    main()
