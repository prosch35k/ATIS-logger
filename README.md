# ATIS logger (ESSA + ESGG)

Every 5 minutes (started by cron-job.org), GitHub Actions fetches the D-ATIS for ESSA and ESGG from atis.guru.
It saves an ATIS only when it differs from the last one saved.

Logs are in `atis_logs/`:
- `ESSA.log`, `ESGG.log`: human-readable, one block per new ATIS
- `atis.jsonl`: one JSON record per new ATIS
- `.state.json`: what was saved last (used to skip duplicates)

## Setup
1. Create a new GitHub repository and upload these files, including the `.github` folder.
2. Open the **Actions** tab. Enable workflows if GitHub asks.
3. Choose **Log ATIS → Run workflow** to test it right away. After that, it runs by itself.

## How it's triggered
GitHub's own schedule often skips runs, so a cron-job.org job starts the workflow every 5 minutes:

- URL: `https://api.github.com/repos/prosch35k/ATIS-logger/actions/workflows/atis.yml/dispatches`
- Method: `POST`
- Headers: `Accept: application/vnd.github+json`, `Authorization: Bearer <token>`, `X-GitHub-Api-Version: 2022-11-28`
- Body: `{"ref":"main"}`
- Token: a fine-grained personal access token limited to this repo, with **Actions: Read and write**

GitHub answers `204 No Content` when it works. An hourly GitHub schedule stays in the workflow as a backup.

## Running locally instead
`python atis_logger.py` checks every 20 minutes until you stop it with Ctrl+C.
