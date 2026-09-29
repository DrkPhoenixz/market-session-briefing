import json
import os
import textwrap
import urllib.error
import urllib.request
from pathlib import Path


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def post_json(url: str, payload: dict, timeout: int = 30) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "market-session-briefing/2.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord HTTP {exc.code}: {details[:1000]}") from exc


def split_message(text: str, limit: int = 1900) -> list[str]:
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
            if wrapped:
                chunks.extend(wrapped[:-1])
                current = wrapped[-1]

    if current:
        chunks.append(current)

    return chunks


def main() -> None:
    webhook = require_env("DISCORD_WEBHOOK_URL")
    briefing_path = Path("briefings/latest.md")

    if not briefing_path.exists():
        raise RuntimeError("briefings/latest.md does not exist")

    text = briefing_path.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError("briefings/latest.md is empty")

    chunks = split_message(text)
    for i, chunk in enumerate(chunks, start=1):
        prefix = f"**Part {i}/{len(chunks)}**\n" if len(chunks) > 1 else ""
        post_json(
            webhook,
            {
                "username": "Global Market Briefing",
                "content": prefix + chunk,
                "allowed_mentions": {"parse": []},
            },
        )

    print(f"Sent briefing to Discord in {len(chunks)} message(s).")


if __name__ == "__main__":
    main()
