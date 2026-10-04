import json
import os
import textwrap
import urllib.error
import urllib.request
import uuid
from pathlib import Path

def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def post_json(url: str, payload: dict, timeout: int = 30) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type":"application/json","User-Agent":"pirates-harbor-daily/3.0"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord HTTP {exc.code}: {details[:1000]}") from exc

def post_file(url: str, file_path: Path, caption: str, timeout: int = 60) -> None:
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    payload_json = json.dumps({
        "username": "The Pirates Harbor Daily",
        "content": caption,
        "allowed_mentions": {"parse":[]},
    })
    file_bytes = file_path.read_bytes()

    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"payload_json\"\r\nContent-Type: application/json\r\n\r\n{payload_json}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"files[0]\"; filename=\"{file_path.name}\"\r\nContent-Type: image/png\r\n\r\n".encode())
    parts.append(file_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "pirates-harbor-daily/3.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord upload HTTP {exc.code}: {details[:1000]}") from exc

def split_message(text: str, limit: int = 1900):
    if len(text) <= limit:
        return [text]
    out, cur = [], ""
    for p in text.split("\n\n"):
        c = p if not cur else cur + "\n\n" + p
        if len(c) <= limit:
            cur = c
        else:
            if cur: out.append(cur)
            if len(p) <= limit: cur = p
            else:
                w = textwrap.wrap(p, width=limit, break_long_words=False, break_on_hyphens=False)
                out.extend(w[:-1]); cur = w[-1] if w else ""
    if cur: out.append(cur)
    return out

def main():
    webhook = require_env("DISCORD_WEBHOOK_URL")
    dashboard = Path("dashboard.png")
    briefing = Path("briefings/latest.md")

    if not dashboard.exists():
        raise RuntimeError("dashboard.png not found")
    if not briefing.exists():
        raise RuntimeError("briefings/latest.md not found")

    post_file(webhook, dashboard, "📊 **Morning Gauge Test — Crypto & Forex**")

    text = briefing.read_text(encoding="utf-8").strip()
    for chunk in split_message(text):
        post_json(webhook, {
            "username":"The Pirates Harbor Daily",
            "content":chunk,
            "allowed_mentions":{"parse":[]},
        })

    print("Dashboard image + market summary sent to Discord.")

if __name__ == "__main__":
    main()
