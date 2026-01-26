#!/usr/bin/env python3
"""
Optional scraper:
- If SOURCE_URL is set (env or config), scrape it to refresh the CSV.
- If not set, skip scraping and just rebuild the ICS from the CSV.

Respects CALENDAR_ID and calendars.yml.
"""

from __future__ import annotations
import os, re, csv, sys, subprocess, json
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# --- minimal YAML reader (same as builder) ------------------
def load_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("{"):  # accept JSON
        return json.loads(text)
    data: dict = {}
    lines = [l.rstrip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    root = {}
    dict_stack = [(0, root)]
    for line in lines:
        indent = len(line) - len(line.lstrip())
        while dict_stack and indent < dict_stack[-1][0]:
            dict_stack.pop()
        if ": " in line:
            key, val = line.lstrip().split(": ", 1)
            if val == "":
                newd = {}
                dict_stack[-1][1][key] = newd
                dict_stack.append((indent + 2, newd))
            else:
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                if val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                dict_stack[-1][1][key] = val
        elif line.strip().endswith(":"):
            key = line.strip()[:-1]
            newd = {}
            dict_stack[-1][1][key] = newd
            dict_stack.append((indent + 2, newd))
    return root

def get_cfg():
    cal_id = os.environ.get("CALENDAR_ID", "autumn_2025")
    cfg_path = Path("config/calendars.yml")
    if not cfg_path.exists():
        print("Missing config/calendars.yml", file=sys.stderr)
        sys.exit(2)
    allcfg = load_yaml(cfg_path)
    c = (allcfg.get("calendars") or {}).get(cal_id)
    if not c:
        print(f"Calendar id '{cal_id}' not found in config.", file=sys.stderr)
        sys.exit(2)
    # env overrides
    c["source_url"] = os.environ.get("SOURCE_URL", c.get("source_url", ""))
    c["csv_path"]   = os.environ.get("CSV_PATH", c.get("csv_path", "data/fixtures.csv"))
    return cal_id, c

HEADERS = {"User-Agent": "rugby-calendars-bot/1.0"}

DATE_RE = re.compile(
    r"\b(?P<d>\d{1,2})(?:st|nd|rd|th)?\s+(?P<m>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(?P<y>20\d{2})\b",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"\b(?P<h>\d{1,2}):(?P<m>\d{2})\b")
MATCH_RE = re.compile(r"\b(?P<home>[A-Z][A-Za-z .&'-]+)\s+v\s+(?P<away>[A-Z][A-Za-z .&'-]+)\b")

MONTHS = {
    "jan":1,"january":1,"feb":2,"february":2,"mar":3,"march":3,"apr":4,"april":4,"may":5,
    "jun":6,"june":6,"jul":7,"july":7,"aug":8,"august":8,"sep":9,"sept":9,"september":9,
    "oct":10,"october":10,"nov":11,"november":11,"dec":12,"december":12,
}

def normalise_date(d: str, m: str, y: str) -> str:
    mm = MONTHS[m.lower()[:3] if len(m) > 3 else m.lower()]
    return f"{int(y):04d}-{mm:02d}-{int(d):02d}"

def extract_fixtures_from_text(text: str):
    out = []
    date_m = DATE_RE.search(text)
    time_m = TIME_RE.search(text)
    match_m = MATCH_RE.search(text)
    if not (date_m and time_m and match_m):
        return out
    date_iso = normalise_date(date_m.group("d"), date_m.group("m"), date_m.group("y"))
    time_gmt = f"{int(time_m.group('h')):02d}:{int(time_m.group('m')):02d}"
    summary = f"{match_m.group('home').strip()} v {match_m.group('away').strip()}"
    # venue heuristics
    after = text[match_m.end():].strip()
    after = re.sub(r"^[\s,:–-]*\s*", "", after)
    venue = ""
    at_split = re.split(r"\bat\b", after, flags=re.IGNORECASE)
    if len(at_split) > 1 and len(at_split[-1].strip()) > 3:
        venue = at_split[-1].strip()
    else:
        for sep in [" – ", " — ", " - ", ", "]:
            if sep in after:
                venue = after.split(sep, 1)[-1].strip()
                break
        if not venue:
            venue = after
    venue = re.split(r"\b(Tickets?|Kick[- ]?off|KO|TV|Live)\b", venue, flags=re.IGNORECASE)[0].strip()
    venue = " ".join(venue.split())
    if summary and venue:
        out.append((date_iso, time_gmt, summary, venue))
    return out

def scrape(source_url: str):
    import bs4
    r = requests.get(source_url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    candidates = []

    # tables first
    for tr in soup.find_all("tr"):
        t = " ".join(tr.get_text(" ", strip=True).split())
        candidates.extend(extract_fixtures_from_text(t))

    # then lists/paragraphs
    for sel in ["li", "p", "div"]:
        for el in soup.select(sel):
            t = " ".join(el.get_text(" ", strip=True).split())
            if len(t) >= 10:
                candidates.extend(extract_fixtures_from_text(t))

    # de-dup + filter 2025
    seen, uniq = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    uniq = [x for x in uniq if x[0].startswith("2025-")]
    uniq.sort(key=lambda x: (x[0], x[1], x[2]))
    return uniq

def write_csv(csv_path: Path, rows):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "time_gmt", "summary", "venue"])
        for r in rows: w.writerow(r)

def main():
    cal_id, cfg = get_cfg()
    source_url = cfg.get("source_url", "")
    csv_path = Path(cfg["csv_path"])

    if source_url:
        print(f"Scraping fixtures from: {source_url}")
        rows = scrape(source_url)
        if not rows:
            print("WARNING: No fixtures detected. Leaving CSV as-is.", file=sys.stderr)
        else:
            print(f"Found {len(rows)} fixtures → writing CSV: {csv_path}")
            write_csv(csv_path, rows)
    else:
        print("SOURCE_URL not set — skipping scrape and using existing CSV.")

    # always build ICS afterwards
    print("Building ICS…")
    res = subprocess.run([sys.executable, "scripts/build_ics.py"], check=False)
    return res.returncode

if __name__ == "__main__":
    sys.exit(main())
