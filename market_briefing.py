import json
import os
import sys
import textwrap
import urllib.error
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


SESSIONS = {
    "Sydney": {
        "timezone": "Australia/Sydney",
        "focus": "Asia-Pacific risk sentiment, Australia/New Zealand, China, commodities, AUD/NZD, crypto, and global overnight developments.",
    },
    "Tokyo": {
        "timezone": "Asia/Tokyo",
        "focus": "Japan and Asia equities, JPY, rates, China/Asia macro, semiconductors/technology, crypto, and global overnight developments.",
    },
    "London": {
        "timezone": "Europe/London",
        "focus": "UK/Europe equities and macro, GBP/EUR, rates, energy/metals, global FX, crypto, and major corporate/technology developments.",
    },
    "New York": {
        "timezone": "America/New_York",
        "focus": "US equities/futures, USD and rates, macro data, commodities, crypto, major companies, AI/technology, and global risk sentiment.",
    },
}


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 90) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request_headers = {
        "Content-Type": "application/json",
        "User-Agent": "market-session-briefing/1.0",
    }
    if headers:
        request_headers.update(headers)

    req = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {details[:1000]}") from exc


def extract_response_text(response: dict) -> tuple[str, list[tuple[str, str]]]:
    text_parts: list[str] = []
    sources: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                text = part.get("text", "")
                if text:
                    text_parts.append(text.strip())

                for ann in part.get("annotations", []):
                    if ann.get("type") != "url_citation":
                        continue
                    url = ann.get("url", "")
                    title = ann.get("title", "Source")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        sources.append((title, url))

    return "\n\n".join(text_parts).strip(), sources


def build_prompt(session: str) -> str:
    cfg = SESSIONS[session]
    now_utc = datetime.now(timezone.utc)
    local_now = now_utc.astimezone(ZoneInfo(cfg["timezone"]))

    return f"""
You are producing a GLOBAL MARKET SESSION OPEN BRIEFING for Discord.

Session: {session}
Session local time: {local_now.strftime("%Y-%m-%d %H:%M %Z")}
UTC time: {now_utc.strftime("%Y-%m-%d %H:%M UTC")}
Special session focus: {cfg["focus"]}

Use web search and prioritize information that is current as of the timestamp above.
Research developments from roughly the last 6-12 hours, plus scheduled events and known catalysts relevant to this session.

The user's priority topics are:
- Trading, financial markets, and crypto
- Business and the global economy
- AI and technology
Coverage: global

Return exactly 5 numbered items. For each item include:
1. A short headline.
2. What happened (2-3 concise sentences).
3. Why it matters for THIS market session.
4. Key numbers/data only when supported by a reliable current source.
5. "Watch:" with the concrete catalyst, level, event, or follow-up worth monitoring.

Also include at the top:
- "Market pulse:" one compact paragraph describing the current risk tone.
- "Session:" {session}.

Rules:
- Prefer primary sources and major reputable financial/news organizations.
- Verify time-sensitive claims with fresh sources.
- Distinguish facts from interpretation.
- Do not invent prices, percentages, quotes, or scheduled events.
- Do not give personalized buy/sell instructions or claim certainty about future prices.
- Mention meaningful uncertainty or conflicting signals.
- Keep the total answer concise enough for Discord, ideally under 4,500 characters.
- Write in Indonesian, but keep standard ticker symbols and market terms in English where useful.
""".strip()


def call_openai(api_key: str, session: str) -> tuple[str, list[tuple[str, str]]]:
    model = os.getenv("OPENAI_MODEL", "").strip() or "gpt-5.6-luna"
    payload = {
        "model": model,
        "tools": [{"type": "web_search"}],
        "input": build_prompt(session),
        "max_output_tokens": 1800,
    }
    response = post_json(
        "https://api.openai.com/v1/responses",
        payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=180,
    )
    text, sources = extract_response_text(response)
    if not text:
        raise RuntimeError("OpenAI returned no output text.")
    return text, sources


def split_discord(text: str, limit: int = 1900) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""

    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        candidate = paragraph if not current else current + "\n\n" + paragraph
        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(paragraph) <= limit:
            current = paragraph
        else:
            wrapped = textwrap.wrap(
                paragraph,
                width=limit,
                break_long_words=False,
                break_on_hyphens=False,
            )
            chunks.extend(wrapped[:-1])
            current = wrapped[-1] if wrapped else ""

    if current:
        chunks.append(current)
    return chunks


def send_discord(webhook_url: str, session: str, briefing: str, sources: list[tuple[str, str]]) -> None:
    now_wib = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Jakarta"))
    header = (
        f"📊 **{session} Session Open — Global Market Briefing**\n"
        f"🕒 {now_wib.strftime('%d %b %Y, %H:%M WIB')}\n"
    )

    source_lines = []
    for title, url in sources[:8]:
        safe_title = title.replace("\n", " ").strip()
        if len(safe_title) > 90:
            safe_title = safe_title[:87] + "..."
        source_lines.append(f"• <{url}> — {safe_title}")

    full_text = header + "\n" + briefing
    if source_lines:
        full_text += "\n\n**Sources used by web search:**\n" + "\n".join(source_lines)

    chunks = split_discord(full_text)
    for index, chunk in enumerate(chunks, start=1):
        content = chunk
        if len(chunks) > 1:
            content = f"**Part {index}/{len(chunks)}**\n" + content

        payload = {
            "username": "Global Market Briefing",
            "content": content,
            "allowed_mentions": {"parse": []},
        }
        post_json(webhook_url, payload, timeout=30)


def main() -> int:
    session = os.getenv("SESSION", "").strip()
    if session not in SESSIONS:
        print(f"SESSION must be one of: {', '.join(SESSIONS)}", file=sys.stderr)
        return 2

    api_key = require_env("OPENAI_API_KEY")
    webhook_url = require_env("DISCORD_WEBHOOK_URL")

    briefing, sources = call_openai(api_key, session)
    send_discord(webhook_url, session, briefing, sources)

    print(f"Sent {session} market briefing successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
