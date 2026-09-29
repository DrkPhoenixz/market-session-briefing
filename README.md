# Market Session Briefing → Discord

Automatically generates a global market briefing with OpenAI web search and sends it to Discord when each major FX session opens.

## Schedule

The workflows use GitHub Actions timezone-aware schedules so DST is handled by the session's own timezone.

| Session | Local open used | Timezone |
|---|---:|---|
| Sydney | 08:00 Mon-Fri | Australia/Sydney |
| Tokyo | 09:00 Mon-Fri | Asia/Tokyo |
| London | 08:00 Mon-Fri | Europe/London |
| New York | 08:00 Mon-Fri | America/New_York |

> These are conventional FX session-open times used by this project. If you prefer another definition, edit the corresponding workflow.

## Required GitHub Actions secrets

Repository → Settings → Secrets and variables → Actions:

- `DISCORD_WEBHOOK_URL`
- `OPENAI_API_KEY`

Never commit either secret to the repository.

## Optional model setting

Repository → Settings → Secrets and variables → Actions → Variables:

- Name: `OPENAI_MODEL`
- Example: `gpt-5.6-luna`

If this variable is empty, the script defaults to `gpt-5.6-luna`.

## Manual test

Open the repository's **Actions** tab, choose any session workflow, then click **Run workflow**.

The briefing covers:
- trading / financial markets / crypto
- global business and economics
- AI and technology
- breaking developments, impact, key data, context, and things to watch

The OpenAI Responses API uses web search, so API usage and web-search tool usage may incur charges.

## Notes

GitHub scheduled workflows can occasionally start a few minutes late during periods of high Actions load. The schedule runs from the default branch.
