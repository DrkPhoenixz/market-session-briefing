# Market Session Briefing → Discord

Architecture:

**ChatGPT Scheduled Task → GitHub → GitHub Actions → Discord**

No OpenAI API key is required in this repository.

## How it works

1. A ChatGPT Scheduled Task checks every hour whether a major market session has just opened.
2. If Sydney, Tokyo, London, or New York has opened, ChatGPT researches the latest global market news and updates `briefings/latest.md`.
3. That GitHub push triggers the workflow currently stored at `.github/workflows/new-york.yml` (display name: **Send Briefing to Discord**).
4. GitHub Actions runs `send_discord.py` and posts the briefing to Discord.

## Required GitHub Actions secret

Repository → Settings → Secrets and variables → Actions:

- `DISCORD_WEBHOOK_URL`

`OPENAI_API_KEY` is not required for this architecture.

## Sessions monitored

- Sydney
- Tokyo
- London
- New York

The ChatGPT task checks each session's own local timezone so DST changes can be handled without hard-coded UTC offsets.

## Manual relay test

Edit `briefings/latest.md` and commit the change. That push should automatically send the file contents to Discord.

You can also use **Actions → Send Briefing to Discord → Run workflow** to resend the current file.
