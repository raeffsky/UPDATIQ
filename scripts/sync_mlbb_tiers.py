#!/usr/bin/env python3
"""Fetch current MLBB ranked hero statistics and prepare offline tier-list data."""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASES = [
    "https://arena.fastapicloud.dev/api",
    "https://arena.rone.dev/api",
]
OUT = Path("mlbbnexus-tiers.json")
LANES = {"exp": "exp", "jungle": "jungle", "mid": "mid", "gold": "gold", "roam": "roam"}
LANE_ALIASES = {
    "exp": "exp", "exp lane": "exp", "experience": "exp",
    "jungle": "jungle", "jungler": "jungle",
    "mid": "mid", "mid lane": "mid",
    "gold": "gold", "gold lane": "gold",
    "roam": "roam", "roamer": "roam",
}

def get_json(path, params):
    query = urllib.parse.urlencode(params, doseq=True)
    last_error = None
    for base in BASES:
        url = f"{base}{path}?{query}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "UPDATIQ/0.1 (MLBB stats sync)", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as response:
                raw = response.read().decode("utf-8")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"API returned invalid JSON from {base}{path}: {raw[:180]!r}") from exc

            # Some API gateways wrap the payload as a JSON string instead of an object.
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    raise RuntimeError(f"API returned a text payload from {base}{path}: {data[:180]!r}")

            if not isinstance(data, dict):
                raise RuntimeError(f"API returned {type(data).__name__}, expected an object, from {base}{path}")

            code = data.get("code", 0)
            if str(code) not in ("0", "200", "None"):
                raise RuntimeError(f"API returned code {code}: {data.get('message', data.get('msg', 'no message'))}")

            payload = data.get("data", data)
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    raise RuntimeError(f"API data field is text, not JSON, from {base}{path}: {payload[:180]!r}")
            if not isinstance(payload, dict):
                raise RuntimeError(f"API data field is {type(payload).__name__}, expected an object, from {base}{path}")
            return payload
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Could not fetch {path} from either API host: {last_error}")

def records(payload):
    if not isinstance(payload, dict):
        return []
    value = payload.get("records", [])
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []

def slugify(value):
    value = str(value or "").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")

def lane_names(hero_record):
    if not isinstance(hero_record, dict):
        return set()
    record_data = hero_record.get("data") or {}
    if not isinstance(record_data, dict):
        return set()
    hero_obj = record_data.get("hero") or {}
    if not isinstance(hero_obj, dict):
        return set()
    hero = hero_obj.get("data") or {}
    if not isinstance(hero, dict):
        return set()
    result = set()
    roadsort = hero.get("roadsort") or []
    if not isinstance(roadsort, list):
        roadsort = [roadsort]
    for entry in roadsort:
        if isinstance(entry, dict):
            lane_data = entry.get("data") or {}
            if not isinstance(lane_data, dict):
                lane_data = {}
            title = str(lane_data.get("road_sort_title") or entry.get("caption") or "").strip().lower()
        else:
            title = str(entry or "").strip().lower()
        key = LANE_ALIASES.get(title)
        if key:
            result.add(key)
    return result

def main():
    stats = get_json("/heroes/rank", {"days": "7", "rank": "all", "sort_field": "win_rate", "sort_order": "desc", "size": 200, "index": 1, "lang": "en"})
    position_data = get_json("/heroes/positions", {"size": 200, "index": 1, "order": "asc", "lang": "en"})
    stats_rows = records(stats)
    position_rows = records(position_data)
    if not stats_rows:
        raise RuntimeError("Rank endpoint returned zero heroes; refusing to ship an empty tier list.")

    positions = {}
    for row in position_rows:
        data = row.get("data") or {}
        hero = ((data.get("hero") or {}).get("data") or {})
        name = hero.get("name")
        if name:
            positions[str(name).casefold()] = lane_names(row)

    heroes = []
    for row in stats_rows:
        data = row.get("data") or {}
        hero = ((data.get("main_hero") or {}).get("data") or {})
        name = hero.get("name")
        if not name:
            continue
        win = data.get("main_hero_win_rate")
        pick = data.get("main_hero_appearance_rate")
        ban = data.get("main_hero_ban_rate")
        hero_obj = {
            "name": str(name),
            "slug": slugify(name),
            "image": hero.get("head") or "",
            "winRate": round(float(win) * 100, 2) if win is not None else None,
            "pickRate": round(float(pick) * 100, 3) if pick is not None else None,
            "banRate": round(float(ban) * 100, 2) if ban is not None else None,
            "tier": "B",
            "lanes": sorted(positions.get(str(name).casefold(), set())),
        }
        heroes.append(hero_obj)

    if not heroes:
        raise RuntimeError("Rank endpoint returned records but none had hero names.")

    lanes = {"all": {"heroes": heroes}}
    for lane in LANES:
        lane_heroes = [dict(h) for h in heroes if lane in h["lanes"]]
        lanes[lane] = {"heroes": lane_heroes}

    for lane_data in lanes.values():
        ranked = sorted(lane_data["heroes"], key=lambda h: h["winRate"] if h["winRate"] is not None else -1, reverse=True)
        n = len(ranked)
        for i, hero in enumerate(ranked):
            ratio = i / max(n, 1)
            hero["tier"] = "S" if ratio < .10 else "A" if ratio < .30 else "B" if ratio < .70 else "C" if ratio < .90 else "D"

    output = {"source": "Rone Arena API", "updatedAt": int(time.time() * 1000), "days": 7, "rank": "all", "lanes": lanes}
    OUT.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print("Synced MLBB stats:", len(heroes), "heroes;", {k: len(v["heroes"]) for k, v in lanes.items()})

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
