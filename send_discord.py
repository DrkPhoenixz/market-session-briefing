import json
import os
import urllib.error
import urllib.request
from pathlib import Path

PURPLE = 0x7C3AED
ORANGE = 0xF59E0B
GRAY = 0x64748B

def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def post_json(url: str, payload: dict, timeout: int = 30) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "pirates-harbor-hourly/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord HTTP {exc.code}: {details[:1000]}") from exc

def trim(text, limit):
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

def make_embed(item, impactful=False, generated=""):
    title = trim(item.get("title", "Berita"), 240)
    summary = trim(item.get("summary", ""), 2600)
    impact = trim(item.get("impact", ""), 900)
    url = str(item.get("url", "")).strip()
    points = [p.strip(" •-\\n\\t") for p in summary.splitlines() if p.strip()]
    if len(points) == 1:
        points = [points[0]]
    description = "**Summary by AI**\\n\\n" + "\\n".join("• " + p for p in points[:3])
    if impactful and impact:
        description += "\\n\\n**Market Impact**\\n• " + impact
    embed = {
        "author": {"name": "The Pirates Harbor • Crypto & Forex"},
        "title": ("🚨 " if impactful else "") + title,
        "description": trim(description, 3900),
        "color": ORANGE if impactful else PURPLE,
        "footer": {"text": "🏴‍☠️ The Pirates Harbor • " + trim(generated, 80)},
    }
    if url.startswith(("https://", "http://")):
        embed["url"] = url
    return embed

def main():
    webhook = require_env("DISCORD_WEBHOOK_URL")
    path = Path("briefings/hourly.json")
    if not path.exists():
        raise RuntimeError("briefings/hourly.json not found")

    data = json.loads(path.read_text(encoding="utf-8"))
    generated = data.get("generated_at", "")
    missed = trim(data.get("missed_summary", "Tidak ada ringkasan."), 1500)
    market = trim(data.get("market_take", ""), 800)

    content = (
        "🏴‍☠️ **The Pirates Harbor — Hourly Market News**\n"
        + "🕐 " + generated + "\n\n"
        + "**Apa yang dilewatkan:**\n" + missed
    )
    if market:
        content += "\n\n**Market take:**\n" + market

    embeds = []
    for item in data.get("impactful", [])[:3]:
        embeds.append(make_embed(item, impactful=True, generated=generated))
    for item in data.get("other_news", [])[:7]:
        embeds.append(make_embed(item, impactful=False, generated=generated))

    if not embeds:
        embeds = [{
            "title": "Tidak ada berita material baru",
            "description": "Belum ada headline baru yang cukup material untuk Crypto/Forex pada jendela pemantauan ini.",
            "color": GRAY,
        }]

    post_json(webhook, {
        "username": "The Pirates Harbor News",
        "content": trim(content, 1900),
        "embeds": embeds[:10],
        "allowed_mentions": {"parse": []},
    })
    print("Sent hourly briefing with", len(embeds[:10]), "embeds.")

if __name__ == "__main__":
    main()
