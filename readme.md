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

### Add a new season or tournament

New years are **not** auto-discovered (the system never guesses at URLs that may
not be published yet) — but adding one is a ~30-second edit. Append a block under
`sources:` in [`config/calendars.yml`](config/calendars.yml). For example, once the
2028 Six Nations fixtures are out:

```yaml
  six_nations_2028:
    enabled: true
    provider: aggregator
    source_url: "https://www.six-nations-guide.co.uk/2028/"
    tournament: six_nations
    season: 2028
    cal_name: "Six Nations 2028"
```

**Easiest way — edit straight on GitHub:** open `config/calendars.yml`, click the
✏️ pencil, paste the block, **Commit changes**. That commit triggers the workflow,
which builds `calendar/six_nations_2028.ics` within a couple of minutes and then
keeps it fresh daily. No local setup, no command line.

Any team in the new tournament also flows automatically into its per-nation feed
(`england.ics`, …) and into `all.ics` — no extra step.

Source URL patterns:

- Six Nations → `https://www.six-nations-guide.co.uk/<year>/`
- Autumn / Summer / RWC → `https://www.autumn-internationals.co.uk/<path>/`
  (e.g. `/2027/`, `/summer-2027/`, `/RWC-2031/`)

### Recipes: common calendars

| I want… | Do this |
|---|---|
| **Every England match, all competitions** | Subscribe to `…/calendar/england.ics`. It already merges England's fixtures from every configured tournament and picks up new ones automatically. |
| One other home nation | Subscribe to `scotland.ics`, `wales.ics`, or `ireland.ics`. |
| **A nation not yet listed** (e.g. France) | Add it to `derived.nations.teams` in the config (a new `- France` line). A `france.ics` feed appears on the next run. |
| **Just a couple of tournaments** (e.g. Six Nations + RWC) | Subscribe to `six_nations_2027.ics` *and* `rwc_2027.ics` — add each URL separately in your calendar app. |
| Absolutely everything | Subscribe to `all.ics`. |
| Stop generating a feed | Set `enabled: false` on that source (or on the `nations` / `all` block) in the config. |

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
- **Event length.** Each fixture is scheduled for **1 h 50 m** (kick-off + 110
  minutes). The sources don't publish end times, so this is a uniform estimate
  (≈ 80 minutes play + half-time + stoppages). Change `event_duration_minutes` in
  [`config/calendars.yml`](config/calendars.yml) to resize every event at once.
  Finished matches with no recoverable kick-off time appear as all-day entries.
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
