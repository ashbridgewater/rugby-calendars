#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv, hashlib

CSV_IN = Path("data/autumn_internationals_2025.csv")
ICS_OUT = Path("calendar/autumn_internationals_2025.ics")
CAL_NAME = "Autumn Internationals 2025"
SOURCE_URL = "https://www.autumn-internationals.co.uk/2025/"

def dtstamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def to_utc_str(date_str, time_str):
    # Times provided are GMT; in November GMT == UTC
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")

def main():
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"PRODID:-//Rugby Calendars//{CAL_NAME}//EN",
        f"X-WR-CALNAME:{CAL_NAME}",
        "X-WR-TIMEZONE:UTC",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]

    with CSV_IN.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            date = row["date"].strip()
            time_gmt = row["time_gmt"].strip()
            summary = row["summary"].strip()
            venue = row["venue"].strip()

            start = to_utc_str(date, time_gmt)
            dt_start = datetime.strptime(start, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            end = (dt_start + timedelta(hours=2)).strftime("%Y%m%dT%H%M%SZ")

            uid_src = f"{date}-{time_gmt}-{summary}-{venue}"
            uid = hashlib.md5(uid_src.encode("utf-8")).hexdigest() + "@rugby-cal"
            desc = f"{summary}\\nVenue: {venue}"

            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{dtstamp()}",
                f"DTSTART:{start}",
                f"DTEND:{end}",
                f"SUMMARY:{summary}",
                f"LOCATION:{venue}",
                f"URL:{SOURCE_URL}",
                f"DESCRIPTION:{desc}",
                "END:VEVENT",
            ]

    lines.append("END:VCALENDAR")
    ICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    ICS_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {ICS_OUT}")

if __name__ == "__main__":
    main()
