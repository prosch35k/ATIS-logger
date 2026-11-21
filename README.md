# ATIS logger (ESSA + ESGG)

Every 5 minutes, GitHub Actions fetches the D-ATIS for ESSA and ESGG from atis.guru.
It saves an ATIS only when it differs from the last one saved.

Logs are in `atis_logs/`:
- `ESSA.log`, `ESGG.log`: human-readable, one block per new ATIS
- `atis.jsonl`: one JSON record per new ATIS
- `.state.json`: what was saved last (used to skip duplicates)

## Setup
1. Create a new GitHub repository and upload these files, including the `.github` folder.
2. Open the **Actions** tab. Enable workflows if GitHub asks.
3. Choose **Log ATIS → Run workflow** to test it right away. After that, it runs by itself.

To change how often it checks, edit `CHECK_EVERY` (seconds) in `.github/workflows/atis.yml`. Each run loops for about 5¾ hours and then starts the next run itself, because GitHub's own schedule often skips runs.

## Running locally instead
`python atis_logger.py` checks every 20 minutes until you stop it with Ctrl+C.
