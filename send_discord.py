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
    fields = []
    for item in data.get("impactful", [])[:3]:
        title = trim(item.get("title", "Berita"), 170)
        url = str(item.get("url", "")).strip()
        name = "🚨 " + title
        if url.startswith(("https://", "http://")):
            name = "[🚨 " + title + "](" + url + ")"
        value = "**Summary by AI**\n" + trim(item.get("summary", ""), 390)
        if item.get("impact"):
            value += "\n**Market Impact:** " + trim(item["impact"], 200)
        fields.append({"name": trim(name, 256), "value": trim(value, 1024), "inline": False})
    for item in data.get("other_news", [])[:7]:
        title = trim(item.get("title", "Berita"), 170)
        url = str(item.get("url", "")).strip()
        name = "📰 " + title
        if url.startswith(("https://", "http://")):
            name = "[📰 " + title + "](" + url + ")"
        fields.append({"name": trim(name, 256),
                       "value": "**Summary by AI**\n" + trim(item.get("summary", ""), 400),
                       "inline": False})
    overview["title"] = "🏴‍☠️ The Pirates Harbor | Hourly Market Briefing"
    overview["description"] = "**Apa yang dilewatkan**\n" + trim(missed, 1000)
    overview["footer"] = {"text": "The Pirates Harbor • " + formatted_time(generated)}
    overview["fields"] = ([{"name": "📊 Market Take — Crypto & Forex",
                            "value": trim(market, 700), "inline": False}] if market else [])
    overview["fields"].extend(fields)
    while (len(overview["title"]) + len(overview["description"]) +
           sum(len(f["name"]) + len(f["value"]) for f in overview["fields"])) > 5500:
        if not overview["fields"]:
            break
        overview["fields"].pop()
    post_json(webhook, {
        "username": "The Pirates Harbor News",
        "embeds": [overview],
        "allowed_mentions": {"parse": []},
    })
    print("Sent one consolidated hourly embed.")

if __name__ == "__main__":
    main()
