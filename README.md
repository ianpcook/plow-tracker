# 🚛 Plow Tracker

**Track them snow plows, n'at!**

Yinz ever sit there wonderin' if the city's gonna plow your street or if you're just gonna be stuck in the house all day? Well, quit your jaggerin' around and use this here skill to see where them plows are at!

An [Agent Skill](https://skills.sh) — works with Claude Code, Clawdbot, Cursor, Windsurf, Cline, and any agent that supports the open skills format.

This skill pulls live data from the City of Pittsburgh's Snow Response Dashboard so you can see:

- 🚛 Where all the plows are right now
- 🟢 Which ones are actually movin' (not just sittin' dahntahn)
- 📍 If they've been anywhere near your street
- 🕐 When they last came through your nebby neighbor's block

## What's It Do?

| Command | What Yinz Get |
|---------|---------------|
| `status` | List all the plows and where they're at |
| `status --active` | Just show the ones that are actually workin' |
| `near "Squirrel Hill"` | Find plows near wherever yinz live |
| `check "123 Main St"` | See if your street's been plowed yet, jagoff |
| `history PW-110` | Stalk a specific plow's route |

## Installation

```bash
npx skills add ianpcook/plow-tracker
```

### Standalone

You can run it directly too:

```bash
python3 plow-tracker.py status
python3 plow-tracker.py near "Aspinwall, PA"
python3 plow-tracker.py check "Forbes Ave and Murray Ave"
```

## Requirements

- Python 3.8+
- `requests` library (`pip install requests`)
- A desire to know when yinz can finally leave the house

## Pro Tips

- The plows update about every minute, so don't be refreshin' like a jagoff
- "Stopped" usually means they're at a depot or on break — not stuck in Shadyside
- Works best during declared snow events (obvi)
- If yinz see 30 plows all parked together, that's probably the garage

## Data Source

All data comes from the City of Pittsburgh's ArcGIS services. We're just makin' it easier to see without goin' dahntahn to check yourself.

## Links

- [City of Pittsburgh Snow Response](https://pittsburghpa.gov/dpw/snow-plow-tracker)
- [skills.sh](https://skills.sh) — The open agent skills ecosystem

---

*Made with ❤️ in Pittsburgh. Go Stillers!*
