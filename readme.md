# 🏉 Rugby Calendars

Auto-updating `.ics` calendar feeds for international rugby, rebuilt daily from
public fixture guides via GitHub Actions. Subscribe once and your calendar app
keeps itself up to date as kick-off times firm up and tournaments progress.

Covered tournaments:

- **Autumn Internationals / Nations Championship 2026**
- **Summer Internationals / Nations Championship 2026**
- **Six Nations 2027**
- **Rugby World Cup 2027** (knockout fixtures included as *tentative* until teams are confirmed)

---

## 📅 Subscribe

Add any of these URLs in your calendar app (see per-app steps below). Pick one
tournament, follow a single nation, or take the lot.

| Feed | Subscription URL |
|------|------------------|
| **Everything** | `https://raw.githubusercontent.com/ashbridgewater/rugby-calendars/main/calendar/all.ics` |
| Autumn Internationals 2026 | `https://raw.githubusercontent.com/ashbridgewater/rugby-calendars/main/calendar/autumn_2026.ics` |
| Summer Internationals 2026 | `https://raw.githubusercontent.com/ashbridgewater/rugby-calendars/main/calendar/summer_2026.ics` |
| Six Nations 2027 | `https://raw.githubusercontent.com/ashbridgewater/rugby-calendars/main/calendar/six_nations_2027.ics` |
| Rugby World Cup 2027 | `https://raw.githubusercontent.com/ashbridgewater/rugby-calendars/main/calendar/rwc_2027.ics` |
| 🏴 England (all tournaments) | `https://raw.githubusercontent.com/ashbridgewater/rugby-calendars/main/calendar/england.ics` |
| 🏴 Scotland (all tournaments) | `https://raw.githubusercontent.com/ashbridgewater/rugby-calendars/main/calendar/scotland.ics` |
| 🏴 Wales (all tournaments) | `https://raw.githubusercontent.com/ashbridgewater/rugby-calendars/main/calendar/wales.ics` |
| ☘️ Ireland (all tournaments) | `https://raw.githubusercontent.com/ashbridgewater/rugby-calendars/main/calendar/ireland.ics` |

### Apple Calendar (macOS / iOS)
**File → New Calendar Subscription…**, paste the URL, set **Auto-refresh** to *Daily*.

### Google Calendar (web)
**Other calendars → + → From URL**, paste the URL, **Add calendar**.

### Outlook (web / desktop)
**Add calendar → Subscribe from web**, paste the URL, name it, **Subscribe**.

---

## 🎛️ Pick and choose

There are two independent layers of control:

1. **What gets generated** — edit [`config/calendars.yml`](config/calendars.yml) and flip
   `enabled: true` / `false` on any source or on the derived `nations` / `all` feeds.
   Disabled feeds simply stop being rebuilt.
2. **What you follow** — subscribe to whichever `.ics` URL(s) you want above.
   Calendar apps can't filter a single feed, which is why each tournament and
   each nation gets its own file.

### Add another tournament

Append a block under `sources:` in `config/calendars.yml`:

```yaml
  autumn_2028:
    enabled: true
    provider: aggregator
    source_url: "https://www.autumn-internationals.co.uk/2028/"
    tournament: autumn
    season: 2028
    cal_name: "Autumn Internationals 2028"
```

Add nations by editing `derived.nations.teams`. That's it — the next run builds it.

---

## 🔄 How the auto-update works

- A GitHub Actions workflow ([`.github/workflows/build-ics.yml`](.github/workflows/build-ics.yml))
  runs **daily at 06:30 UTC** (and on demand / on config change).
- It scrapes each enabled source, rebuilds every feed, validates the output, and
  commits **only when something actually changed** (event content is hashed, so
  a quiet day produces no commit).
- A monthly `state/heartbeat.txt` update guarantees repo activity so GitHub does
  not auto-disable the scheduled workflow during the off-season.

### Correctness notes

- **Times are DST-correct.** Kick-offs are converted from UK local time to UTC
  with full BST/GMT awareness, so a summer 2:10pm and a winter 2:10pm are both
  right in your local calendar.
- **Stable event IDs.** Updates (e.g. a confirmed kick-off time, or an RWC
  knockout resolving from "Winner Pool A" to a real team) land as in-place edits,
  not duplicate events.
- **Played matches** keep the score in the title (e.g. `England 34-32 Australia`).
- **Fail-safe.** If a source can't be scraped or returns nothing, the run aborts
  and the previously published calendars are left untouched — never overwritten
  with empty or partial data.

---

## 🛠️ Local development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

.venv/bin/python -m pytest                              # run the test suite
.venv/bin/python -m scripts.run_pipeline --config config/calendars.yml   # build all 9 feeds
.venv/bin/python -m scripts.validate_ics calendar/*.ics                   # validate output
```

Pipeline stages (all under [`scripts/`](scripts/)):
`run_pipeline` → `scrape` (via a pluggable `providers/` seam) → `data/*.csv`
(the human-editable override layer) → `build_ics` → `calendar/*.ics`.

*Fixtures are compiled from [autumn-internationals.co.uk](https://www.autumn-internationals.co.uk/)
and [six-nations-guide.co.uk](https://www.six-nations-guide.co.uk/); this project is
unofficial and not affiliated with any rugby union.*
