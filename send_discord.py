import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

PURPLE = 0x6366F1
ORANGE = 0xF59E0B


def trim(value, limit):
    value = str(value or "").strip()
    return value if len(value) <= limit else value[:limit - 1].rstrip() + "…"


def formatted_time(value):
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y %H:%M WIB")
    except (ValueError, TypeError):
        return str(value)


def bullet_summary(value):
    text = str(value or "").strip()
    lines = [line.strip(" •-\t") for line in text.splitlines() if line.strip()]
    if len(lines) <= 1:
        lines = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Ý0-9])", text)
    lines = [trim(line, 550) for line in lines if line.strip()]
    return "\n".join("• " + line for line in lines[:3]) or "• Belum ada ringkasan."


def make_embed(item, impactful, generated):
    title = trim(item.get("title", "Berita"), 250)
    impact = trim(item.get("impact", ""), 850)
    description = "**Summary by AI**\n" + bullet_summary(item.get("summary", ""))
    if impactful and impact:
        description += "\n\n**Market Impact**\n• " + impact
    embed = {
        "author": {"name": "The Pirates Harbor News"},
        "title": ("🚨 " if impactful else "") + title,
        "description": trim(description, 3900),
        "color": ORANGE if impactful else PURPLE,
        "footer": {"text": "📰 | The Pirates Harbor • " + formatted_time(generated)},
    }
    url = str(item.get("url", "")).strip()
    if url.startswith(("https://", "http://")):
        embed["url"] = url
    return embed


def post_json(url, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "pirates-harbor-news/2.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord HTTP {exc.code}: {details[:1000]}") from exc


def main():
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        raise RuntimeError("Missing DISCORD_WEBHOOK_URL")
    data = json.loads(Path("briefings/hourly.json").read_text(encoding="utf-8"))
    generated = data.get("generated_at", "")
    overview = {
        "title": "📋 Apa yang dilewatkan",
        "description": trim(data.get("missed_summary", "Tidak ada perubahan material."), 1800),
        "color": PURPLE,
        "footer": {"text": formatted_time(generated)},
    }
    if data.get("market_take"):
        overview["fields"] = [{
            "name": "📊 Crypto & Forex — Market Take",
            "value": trim(data["market_take"], 1000),
            "inline": False,
        }]
    embeds = [overview]
    embeds.extend(make_embed(item, True, generated) for item in data.get("impactful", [])[:3])
    embeds.extend(make_embed(item, False, generated) for item in data.get("other_news", [])[:7])
    for start in range(0, len(embeds), 10):
        post_json(webhook, {
            "username": "The Pirates Harbor News",
            "content": "🏴‍☠️ **The Pirates Harbor | Hourly Crypto & Forex**" if start == 0 else "",
            "embeds": embeds[start:start + 10],
            "allowed_mentions": {"parse": []},
        })
    print(f"Sent {len(embeds)} embeds in {(len(embeds) + 9) // 10} message(s).")


if __name__ == "__main__":
    main()
