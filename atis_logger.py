#!/usr/bin/env python3
"""
ATIS logger for atis.guru

Polls the D-ATIS pages for ESSA and ESGG on atis.guru and appends every
*new* ATIS (arrival / departure / combined) to a log file per airport.

No third-party packages needed - Python 3.8+ standard library only.

Usage:
    python atis_logger.py                    # poll ESSA + ESGG every 30 min, logs in ./atis_logs
    python atis_logger.py --interval 600     # poll every 10 minutes
    python atis_logger.py --airports ESSA ESGG EKCH
    python atis_logger.py --logdir C:\\ATIS   # choose where logs go
    python atis_logger.py --once             # check once and exit (for cron / Task Scheduler)

Output (in the log dir):
    ESSA.log        human-readable log, one block per new ATIS
    ESGG.log
    atis.jsonl      every new ATIS as one JSON line (easy to parse later)
    .state.json     remembers the last ATIS seen, so restarts don't duplicate
"""

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://atis.guru/atis/{icao}"
USER_AGENT = "Mozilla/5.0 (ATIS logger; personal use)"

# One card on the page: <h5 class="card-title">Arrival ATIS</h5>
#                       <h6 class="card-subtitle ...">2026-11-20 20:50 UTC</h6>
#                       <div class="atis">ESSA ARR ATIS Y ...</div>
CARD_RE = re.compile(
    r'<h5 class="card-title"[^>]*>\s*(?P<title>.*?)\s*</h5>'
    r'(?:\s*<h6 class="card-subtitle[^"]*"[^>]*>\s*(?P<time>.*?)\s*</h6>)?'
    r'\s*<div class="atis">(?P<text>.*?)</div>',
    re.S,
)

# First line of an ATIS, e.g. "ESSA ARR ATIS Y" / "ESGG ATIS K"
LETTER_RE = re.compile(r"\bATIS\s+([A-Z])\b")


def fetch(icao: str, timeout: int = 20) -> str:
    req = urllib.request.Request(BASE_URL.format(icao=icao), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_atis(page: str):
    """Return {title: {"time":..., "text":..., "letter":...}} for ATIS cards (skips METAR/TAF)."""
    found = {}
    for m in CARD_RE.finditer(page):
        title = html.unescape(m.group("title")).strip()
        if "ATIS" not in title.upper():
            continue  # METAR / TAF cards
        text = html.unescape(m.group("text")).replace("\r\n", "\n").replace("\r", "\n").strip()
        letter = LETTER_RE.search(text.split("\n", 1)[0])
        # The page can contain the same card more than once (streamed render); keep the last.
        found[title] = {
            "time": html.unescape(m.group("time") or "").strip(),
            "text": text,
            "letter": letter.group(1) if letter else "?",
        }
    return found


def load_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def check(icao, logdir, state):
    """Fetch one airport, write any new ATIS to the logs. Returns number of new entries."""
    page = fetch(icao)
    atises = parse_atis(page)
    if not atises:
        log(f"{icao}: no ATIS on page")
        return 0

    new = 0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    for title, a in atises.items():
        key = f"{icao}|{title}"
        digest = hashlib.sha1(a["text"].encode()).hexdigest()
        if state.get(key) == digest:
            continue  # already logged
        state[key] = digest
        new += 1

        header = f"===== {icao} {title} {a['letter']}  |  issued {a['time'] or '?'}  |  logged {now} ====="
        with open(os.path.join(logdir, f"{icao}.log"), "a", encoding="utf-8") as f:
            f.write(header + "\n" + a["text"] + "\n\n")

        record = {"logged": now, "airport": icao, "type": title, **a}
        with open(os.path.join(logdir, "atis.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        log(f"{icao}: NEW {title} {a['letter']} ({a['time']})")
    return new


def main():
    p = argparse.ArgumentParser(description="Log new ATIS from atis.guru")
    p.add_argument("--airports", nargs="+", default=["ESSA", "ESGG"], help="ICAO codes (default: ESSA ESGG)")
    p.add_argument("--interval", type=int, default=1200, help="seconds between checks (default 1200 = 20 min)")
    p.add_argument("--logdir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "atis_logs"))
    p.add_argument("--once", action="store_true", help="check once and exit")
    args = p.parse_args()

    interval = max(30, args.interval)  # be nice to the site
    airports = [a.upper() for a in args.airports]
    os.makedirs(args.logdir, exist_ok=True)
    state_path = os.path.join(args.logdir, ".state.json")
    state = load_state(state_path)

    log(f"Watching {', '.join(airports)} every {interval}s -> {args.logdir}")
    while True:
        for icao in airports:
            try:
                if check(icao, args.logdir, state):
                    save_state(state_path, state)
            except Exception as e:  # network hiccup etc. - keep running
                log(f"{icao}: error: {e}")
        if args.once:
            break
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            break
    log("Stopped.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
