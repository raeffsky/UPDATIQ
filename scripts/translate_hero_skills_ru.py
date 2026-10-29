#!/usr/bin/env python3
"""Translate every scraped MLBB hero skill name and description to Russian."""
import concurrent.futures
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

TARGET = Path("app/src/main/assets/hero-skills.js")
CACHE = Path("app/src/main/assets/hero-skills-ru-cache.json")
URL = "https://translate.googleapis.com/translate_a/single"
HEADERS = {"User-Agent": "Mozilla/5.0 UPDATIQ/1.0"}

# Known official/common localized names avoid awkward machine translations.
NAME_OVERRIDES = {
    "Stick, Stick": "Липкость",
    "Slam, Slam": "Шлёпок",
    "Spread, Spread": "Разделение",
    "Grab, Grab": "Захват",
}

def load_data():
    text = TARGET.read_text(encoding="utf-8").strip()
    prefix = "window.heroSkillData = "
    if not text.startswith(prefix):
        raise RuntimeError("Unexpected hero skill data format")
    return json.loads(text[len(prefix):].rstrip(";"))

def is_english(value):
    return bool(re.search(r"[A-Za-z]{3}", value or "")) and not bool(re.search(r"[А-Яа-яЁё]{4}", value or ""))

def translate_one(value, cache):
    value = str(value or "").strip()
    if not value or not is_english(value):
        return value
    if value in cache:
        return cache[value]
    params = urllib.parse.urlencode([
        ("client", "gtx"), ("sl", "en"), ("tl", "ru"), ("dt", "t"), ("q", value)
    ])
    last_error = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL + "?" + params, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            translated = "".join(part[0] for part in payload[0] if part and part[0])
            if translated.strip():
                return translated.strip()
            raise RuntimeError("empty translation")
        except Exception as exc:
            last_error = exc
            time.sleep(0.5 * (attempt + 1))
    print("WARN: translation failed, keeping original:", value[:80], str(last_error), file=sys.stderr)
    return value

def main():
    data = load_data()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    texts = set()
    for skills in data.values():
        for skill in skills:
            for field in ("name", "description"):
                value = str(skill.get(field) or "").strip()
                if value and is_english(value) and value not in cache and value not in NAME_OVERRIDES:
                    texts.add(value)
    print("Unique skill strings to translate:", len(texts))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(translate_one, value, cache): value for value in texts}
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            original = futures[future]
            cache[original] = future.result()
            completed += 1
            if completed % 50 == 0:
                print("Translated", completed, "/", len(texts))
                CACHE.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for hero_name, skills in data.items():
        for index, skill in enumerate(skills, start=1):
            name = str(skill.get("name") or "")
            if name in NAME_OVERRIDES:
                skill["name"] = NAME_OVERRIDES[name]
            elif name in cache:
                translated_name = cache[name]
                # Machine translation occasionally returns short labels unchanged.
                skill["name"] = f"Навык {index}" if is_english(translated_name) else translated_name
            elif is_english(name):
                skill["name"] = f"Навык {index}"
            description = str(skill.get("description") or "")
            if description in cache:
                skill["description"] = cache[description]
            elif is_english(description):
                raise RuntimeError(f"Missing Russian description translation for {hero_name} / {name}")
    TARGET.write_text("window.heroSkillData = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    count = sum(len(skills) for skills in data.values())
    english_names = sum(1 for skills in data.values() for skill in skills if is_english(skill.get("name", "")))
    english_descriptions = sum(1 for skills in data.values() for skill in skills if is_english(skill.get("description", "")))
    print("Russian skill data written:", len(data), "heroes,", count, "skills; English names remaining:", english_names, "; English descriptions remaining:", english_descriptions)
    if english_names or english_descriptions:
        raise RuntimeError(f"Russian localization incomplete: {english_names} skill names and {english_descriptions} descriptions remain in English")

if __name__ == "__main__":
    main()
