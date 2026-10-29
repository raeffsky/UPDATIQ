#!/usr/bin/env python3
"""Sync measured hero counter matchups from MLBBHub for the full MLBB roster."""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://mlbbhub.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UPDATIQ/1.0; matchup-sync)"}


def slug_from_href(href):
    match = re.search(r"/counter/([^/?#]+)", href or "")
    return match.group(1).lower() if match else ""


def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    catalog_response = session.get(BASE + "/counter", timeout=30)
    catalog_response.raise_for_status()
    catalog_soup = BeautifulSoup(catalog_response.text, "html.parser")
    roster = {}
    for link in catalog_soup.select('a[href*="/counter/"]'):
        slug = slug_from_href(link.get("href", ""))
        name = link.get_text(" ", strip=True)
        if slug and name and slug not in {"", "counter"} and len(name) < 50:
            roster.setdefault(slug, {"slug": slug, "name": name})
    if len(roster) < 120:
        raise RuntimeError(f"Only {len(roster)} heroes discovered on MLBBHub counter catalog; refusing partial roster")

    output = {
        "source": "MLBBHub ranked matchup data",
        "sourceUrl": BASE + "/counter",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "patch": "See source page for current patch",
        "heroes": {}
    }
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def fetch_one(hero):
        url = f"{BASE}/counter/{hero['slug']}"
        try:
            page_session = requests.Session()
            page_session.headers.update(HEADERS)
            response = page_session.get(url, timeout=12)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            heading = next((h for h in soup.find_all(["h2", "h3"]) if "proven counters" in h.get_text(" ", strip=True).lower()), None)
            hero_section = soup.find("h1")
            hero_section = hero_section.find_parent("section") if hero_section else None
            hero_role = ""
            if hero_section:
                role_img = next((img for img in hero_section.find_all("img") if (img.get("alt") or "").lower().endswith(" icon") and "hero icon" not in (img.get("alt") or "").lower()), None)
                if role_img:
                    hero_role = role_img.get("alt", "").replace(" icon", "").strip()
            counters = []
            if heading:
                ul = heading.find_next("ul")
                if ul:
                    for li in ul.find_all("li", recursive=False):
                        link = li.select_one('a[href*="/counter/"]')
                        if not link:
                            continue
                        counter_slug = slug_from_href(link.get("href", ""))
                        if not counter_slug or counter_slug == hero["slug"]:
                            continue
                        img = link.find("img")
                        name = (img.get("alt", "").replace(" hero icon", "").strip() if img else "")
                        if not name:
                            name = re.sub(r"^\d+\s*", "", link.get_text(" ", strip=True)).strip()
                        text_value = li.get_text(" ", strip=True)
                        edge_match = re.search(r"([+−-]?\d+(?:\.\d+)?)\s*pp", text_value, re.I)
                        edge = float(edge_match.group(1).replace("−", "-")) if edge_match else None
                        counters.append({"slug": counter_slug, "name": name, "edge": edge, "sourceUrl": url})
            return hero["slug"], {"name": hero["name"], "role": hero_role, "sourceUrl": url, "counters": counters}, None
        except Exception as exc:
            return hero["slug"], None, f"{hero['name']}: {exc}"

    errors = []
    completed = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(fetch_one, hero) for hero in roster.values()]
        for future in as_completed(futures):
            slug, record, error = future.result()
            completed += 1
            if record is not None:
                output["heroes"][slug] = record
                print(f"OK {record['name']}: {len(record['counters'])} measured counters ({completed}/{len(roster)})")
            else:
                errors.append(error)
                print(f"WARNING {error} ({completed}/{len(roster)})", file=sys.stderr)

    if len(output["heroes"]) < 120:
        raise RuntimeError(f"Only {len(output['heroes'])}/{len(roster)} counter pages parsed; refusing partial update. " + "; ".join(errors[:8]))
    measured = sum(len(v["counters"]) for v in output["heroes"].values())
    if measured < 300:
        raise RuntimeError(f"Only {measured} measured counter edges parsed; refusing likely broken extraction.")
    Path("mlbb-hero-counters.json").write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Saved {len(output['heroes'])} hero counter profiles and {measured} measured edges; page errors {len(errors)}")


if __name__ == "__main__":
    main()
