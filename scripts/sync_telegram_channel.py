#!/usr/bin/env python3
"""Fetch the public Telegram web preview for UPDATIQ and embed recent posts."""
import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

CHANNEL = "updatiq"
URL = f"https://t.me/s/{CHANNEL}"
OUT = Path("app/src/main/assets/community-news.js")

def clean_text(node):
    if not node:
        return ""
    for br in node.find_all("br"):
        br.replace_with("\n")
    return re.sub(r"\n{3,}", "\n\n", unescape(node.get_text("\n", strip=True))).strip()

def main():
    articles = []
    try:
        response = requests.get(URL, timeout=25, headers={"User-Agent": "Mozilla/5.0 UPDATIQ/1.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for node in soup.select(".tgme_widget_message_wrap"):
            message = node.select_one(".tgme_widget_message")
            if not message:
                continue
            post_link = message.select_one(".tgme_widget_message_date")
            href = post_link.get("href", "") if post_link else ""
            if not href:
                data_post = message.get("data-post", "")
                if data_post:
                    href = f"https://t.me/{data_post}"
            if not href:
                continue
            text_node = message.select_one(".tgme_widget_message_text")
            body = clean_text(text_node)
            photo = message.select_one(".tgme_widget_message_photo_wrap")
            image = ""
            if photo:
                style = photo.get("style", "")
                match = re.search(r"background-image:\\s*url\\(['\"]?([^'\"\\)]+)", style)
                if match:
                    image = urljoin(URL, match.group(1))
            video = message.select_one(".tgme_widget_message_video_thumb")
            if not image and video:
                match = re.search(r"background-image:\\s*url\\(['\"]?([^'\"\\)]+)", video.get("style", ""))
                if match:
                    image = urljoin(URL, match.group(1))
            time_node = message.select_one("time")
            date = time_node.get("datetime", "") if time_node else ""
            if not body and not image:
                continue
            post_id = href.rstrip("/").split("/")[-1].split("?")[0]
            articles.append({
                "id": post_id,
                "title": (body.split("\n", 1)[0][:120] if body else "Публикация с изображением"),
                "text": body[:5000],
                "date": date,
                "url": href,
                "image": image,
                "source": "Telegram · UPDATIQ",
                "category": "community"
            })
        # Newest first, unique by post ID.
        unique = {item["id"]: item for item in articles}
        articles = list(unique.values())[-30:][::-1]
        status = "ok"
    except Exception as exc:
        print(f"Telegram sync failed: {exc}")
        status = "error"
        # Preserve previously fetched data on transient network errors.
        existing = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        match = re.search(r"window\\.UPDATIQ_COMMUNITY_NEWS\\s*=\\s*(\\{.*\\});?\\s*$", existing, re.S)
        if match:
            try:
                previous = json.loads(match.group(1))
                articles = previous.get("articles", [])
            except Exception:
                articles = []
    data = {"channel": CHANNEL, "channelUrl": f"https://t.me/{CHANNEL}", "updatedAt": datetime.now(timezone.utc).isoformat(), "status": status, "articles": articles}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.UPDATIQ_COMMUNITY_NEWS = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"Telegram channel sync status={status}, posts={len(articles)}")

if __name__ == "__main__":
    main()
