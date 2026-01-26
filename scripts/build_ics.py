#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os, csv, hashlib, sys, json

# --- tiny YAML reader (no external deps) --------------------
def load_yaml(path: Path) -> dict:
    # Minimal YAML subset loader for our simple config; will also accept JSON.
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("{"):
        return json.loads(text)  # allow JSON as a fallback
    data: dict = {}
    ctx = data
    stack = []
    current_dict = {}
    lines = [l.rstrip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    def assign(target, key, val): target[key] = val
    root = {}
    last_indent = 0
    dict_stack = [(0, root)]
    for line in lines:
        indent = len(line) - len(line.lstrip())
        while dict_stack and indent < dict_stack[-1][0]:
            dict_stack.pop()
        if ": " in line:
            key, val = line.lstrip().split(": ", 1)
            if val == "":
                # start of nested mapping
                newd = {}
                dict_stack[-1][1][key] = newd
                dict_stack.append((indent + 2, newd))
            else:
                # scalar
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

# --- config resolution --------------------------------------
def get_cfg():
    cal_id = os.environ.get("CALENDAR_ID", "autumn_2025")
    cfg_path = Path("config/calendars.yml")
    if not cfg_path.exists():
        raise SystemExit("Missing config/calendars.yml")
    allcfg = load_yaml(cfg_path)
    calcfg = (allcfg.get("calendars") or {}).get(cal_id)
    if not calcfg:
        raise SystemExit(f"Calendar id '{cal_id}' not found in config/calendars.yml")
    # allow env overrides
    calcfg["source_url"] = os.environ.get("SOURCE_URL", calcfg.get("source_url", ""))
    calcfg["cal_name"] = os.environ.get("CAL_NAME", calcfg.get("cal_name", "Rugby Calendar"))
    calcfg["csv_path"] = os.environ.get("CSV_PATH", calcfg.get("csv_path", "data/fixtures.csv"))
    calcfg["ics_path"] = os.environ.get("ICS_PATH", calcfg.get("ics_path", "calendar/fixtures.ics"))
    calcfg["default_duration_minutes"] = int(os.environ.get(
        "DEFAULT_DURATION_MINUTES", str(calcfg.get("default_duration_minutes", 120))
    ))
    calcfg["timezone"] = os.environ.get("TIMEZONE", calcfg.get("timezone", "UTC"))
    return cal_id, calcfg

def dtstamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def to_utc_str(date_str, time_str):
    # Times provided are GMT/UTC
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")

def fold(lines):
    # RFC5545 line folding at ~75 octets
    out = []
    for raw in lines:
        b = raw.encode("utf-8")
        if len(b) <= 73:
            out.append(raw)
            continue
        cur = ""
        for ch in raw:
            if len(cur.encode("utf-8")) >= 73:
                out.append(cur)
                cur = " " + ch
            else:
                cur += ch
        out.append(cur)
    return "\r\n".join(out) + "\r\n"

def main():
    cal_id, cfg = get_cfg()
    CSV_IN = Path(cfg["csv_path"])
    ICS_OUT = Path(cfg["ics_path"])
    CAL_NAME = cfg["cal_name"]
    SOURCE_URL = cfg.get("source_url", "")
    DEFAULT_DUR = int(cfg["default_duration_minutes"])
    TZLABEL = cfg.get("timezone", "UTC")

    if not CSV_IN.exists():
        raise SystemExit(f"CSV not found: {CSV_IN}")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"PRODID:-//Rugby Calendars//{CAL_NAME}//EN",
        f"X-WR-CALNAME:{CAL_NAME}",
        f"X-WR-TIMEZONE:{TZLABEL}",
        "X-WR-CALDESC:Fixtures auto-generated from CSV.",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]

    with CSV_IN.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = (row.get("date") or "").strip()
            time_gmt = (row.get("time_gmt") or "").strip()
            summary = (row.get("summary") or "").strip()
            venue = (row.get("venue") or "").strip()
            dur = int((row.get("duration_minutes") or "").strip() or DEFAULT_DUR)

            start = to_utc_str(date, time_gmt)
            dt_start = datetime.strptime(start, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            end = (dt_start + timedelta(minutes=dur)).strftime("%Y%m%dT%H%M%SZ")

            uid_src = f"{date}-{time_gmt}-{summary}-{venue}-{cal_id}"
            uid = hashlib.md5(uid_src.encode("utf-8")).hexdigest() + "@rugby-cal"
            desc = f"{summary}\\nVenue: {venue}"

            event = [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{dtstamp()}",
                f"DTSTART:{start}",
                f"DTEND:{end}",
                f"SUMMARY:{summary}",
                f"LOCATION:{venue}",
                *( [f"URL:{SOURCE_URL}"] if SOURCE_URL else [] ),
                f"DESCRIPTION:{desc}",
                "STATUS:CONFIRMED",
                "TRANSP:OPAQUE",
                "END:VEVENT",
            ]
            lines.extend(event)

    lines.append("END:VCALENDAR")
    ICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    ICS_OUT.write_text(fold(lines), encoding="utf-8")
    print(f"Wrote {ICS_OUT}")

if __name__ == "__main__":
    main()
