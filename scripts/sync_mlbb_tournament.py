#!/usr/bin/env python3
"""Sync professional MLBB tournament hero stats from MLBBDex."""
import html
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

URL = "https://mlbbdex.com/en/esports"
RANKED = Path("mlbbnexus-tiers.json")
OUT = Path("mlbb-tournament-tiers.json")
HEADERS = {"User-Agent": "Mozilla/5.0 UPDATIQ/1.0"}

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading = ""
        self.in_h3 = False
        self.li_depth = 0
        self.item = None
        self.items = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h3":
            self.in_h3 = True
        if tag == "li":
            self.li_depth += 1
            if self.li_depth == 1:
                self.item = {"heading": self.heading, "href": "", "text": ""}
        if tag == "a" and self.item is not None:
            href = attrs.get("href", "")
            if "/en/heroes/" in href and not self.item["href"]:
                self.item["href"] = href
        if tag == "tr":
            self.item = {"heading": self.heading, "href": "", "text": "", "table": True}

    def handle_endtag(self, tag):
        if tag == "h3":
            self.in_h3 = False
        if tag == "li":
            if self.li_depth == 1 and self.item and self.item.get("href"):
                self.items.append(self.item)
                self.item = None
            self.li_depth = max(0, self.li_depth - 1)
        if tag == "tr":
            if self.item and self.item.get("href"):
                self.items.append(self.item)
            self.item = None

    def handle_data(self, data):
        text = " ".join(data.split())
        if not text:
            return
        if self.in_h3:
            self.heading = text
        if self.item is not None:
            self.item["text"] += " " + text

def number(pattern, text, default=0.0):
    match = re.search(pattern, text, re.I)
    return float(match.group(1)) if match else default

def main():
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=35) as response:
        page = response.read().decode("utf-8", "replace")
    parser = Parser()
    parser.feed(page)

    records = {}
    games_match = re.search(r"(\d+) games from MSC 2026", page)
    games = int(games_match.group(1)) if games_match else 0
    for item in parser.items:
        heading = item["heading"].strip().lower()
        if heading not in ("most picked", "most banned", "best win rate", "valued far more in pro", "ranked favorites pros pass on"):
            continue
        slug_match = re.search(r"/en/heroes/([^/?#]+)", item["href"])
        if not slug_match:
            continue
        slug = slug_match.group(1).lower()
        text = html.unescape(item["text"])
        name = re.sub(r"\s+", " ", text).strip()
        # The first visible label in each hero row is the hero name.
        name_match = re.search(r"([A-Za-z][A-Za-z .'-]+?)\s+(?:Presence|\d+\s*W)", text)
        if name_match:
            name = name_match.group(1).strip()
        row = records.setdefault(slug, {"slug": slug, "name": name, "proPresence": 0.0, "picks": 0, "bans": 0, "winRate": None})
        if heading == "most picked":
            row["proPresence"] = max(row["proPresence"], number(r"Presence\s+([\d.]+)%", text))
            row["picks"] = int(number(r"(\d+)\s+picks", text))
        elif heading == "most banned":
            row["proPresence"] = max(row["proPresence"], number(r"Presence\s+([\d.]+)%", text))
            row["bans"] = int(number(r"(\d+)\s+bans", text))
        elif heading == "best win rate":
            match = re.search(r"(\d+)\s*W\s*[–-]\s*(\d+)\s*L\s*([\d.]+)%", text)
            if match:
                row["wins"], row["losses"], row["winRate"] = int(match.group(1)), int(match.group(2)), float(match.group(3))
        else:
            # The comparison tables list a hero's pro presence before the ranked comparison.
            presence = number(r"([\d.]+)%\s*[·•]\s*#\s*\d+", text)
            row["proPresence"] = max(row["proPresence"], presence)

    if len(records) < 10 or games < 100:
        raise RuntimeError(f"Unexpected MLBBDex response: parsed {len(records)} heroes and {games} games")

    # Use the live ranked sync only for hero portraits and lane labels; tournament grades are calculated solely from pro data.
    ranked = json.loads(RANKED.read_text(encoding="utf-8")) if RANKED.exists() else {}
    ranked_by_slug = {}
    for lane in (ranked.get("lanes") or {}).values():
        for hero in lane.get("heroes", []):
            if hero.get("slug"):
                ranked_by_slug[hero["slug"].lower()] = hero
    for slug, hero in records.items():
        reference = ranked_by_slug.get(slug, {})
        hero["name"] = reference.get("name") or hero["name"] or slug.replace("-", " ").title()
        hero["image"] = reference.get("image", "")
        hero["lanes"] = reference.get("lanes", [])
        hero["rankedSlug"] = reference.get("slug", slug)\n        hero["slug"] = reference.get("slug", slug)
        if not hero["proPresence"]:
            # Keep win-rate-only heroes, but make their lack of reliable presence explicit.
            hero["proPresence"] = 0.0
        hero["score"] = round(hero["proPresence"] * 0.72 + (hero["winRate"] if hero["winRate"] is not None else 50.0) * 0.28, 2)

    ordered = sorted(records.values(), key=lambda h: (h["score"], h["proPresence"]), reverse=True)
    count = len(ordered)
    for i, hero in enumerate(ordered):
        pct = (i + 1) / count
        hero["tier"] = "S" if pct <= .10 else "A" if pct <= .30 else "B" if pct <= .70 else "C" if pct <= .90 else "D"
    payload = {
        "source": "MLBBDex / Liquipedia",
        "sourceUrl": URL,
        "updatedAt": __import__("time").time_ns() // 1_000_000,
        "games": games,
        "windowDays": 120,
        "heroCount": len(ordered),
        "method": "Tier score weights professional draft presence (72%) and tournament win rate (28%) when available. Ranked statistics are not used for grading.",
        "heroes": ordered,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Synced tournament stats: {games} pro games, {len(ordered)} heroes, tiers: " + str({t: sum(1 for h in ordered if h["tier"] == t) for t in "SABCD"}))

if __name__ == "__main__":
    main()
