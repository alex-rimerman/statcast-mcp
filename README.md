# Statcast MCP Server

A [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that lets you query **MLB Statcast data using plain English**. Ask your AI assistant about players, games, stats, leaderboards, and more — no coding required.

Built on [pybaseball](https://github.com/jldbc/pybaseball), this server gives AI assistants direct access to data from **Baseball Savant**, **FanGraphs**, and **Baseball Reference**.

## What Can You Ask?

Once connected, just talk to your AI assistant naturally:

- *"How did Aaron Judge hit in July 2024?"*
- *"Show me Gerrit Cole's pitch arsenal this season"*
- *"Who had the highest exit velocity in 2024?"*
- *"What were the NL standings at the end of 2023?"*
- *"Find me the most undervalued hitters — compare xBA to actual BA"*
- *"Expected stats for the whole Yankees lineup and their five starters"* (use `expected_stats_batch` with comma-separated names)
- *"Who are the fastest players in baseball right now?"*
- *"Show me every pitch from the Yankees-Red Sox game on July 4, 2024"*

The AI translates your questions into the right data queries automatically.

## Example: Prompt & Response

Here's what a typical exchange looks like when you use the Statcast MCP:

**Prompt**

> "What were Gerrit Cole's arsenal statistics in 2023?"

**Response**

| Pitch Type        | Usage | Pitches | PA  | BA   | SLG   | Whiff% | K%   | Run Val/100 |
|-------------------|-------|---------|-----|------|-------|--------|------|-------------|
| 4-Seam Fastball   | 52.9% | 1,737   | 427 | .202 | .333  | 23.0%  | 28.3% | +1.7        |
| Slider            | 20.8% | 683     | 175 | .186 | .251  | 32.7%  | 29.1% | +1.4        |
| Curveball         | 12.1% | 396     | 97  | .215 | .269  | 24.4%  | 27.8% | +1.4        |
| Cutter            | 7.0%  | 231     | 65  | .262 | .377  | 31.1%  | 23.1% | +1.6        |
| Changeup          | 7.1%  | 233     | 54  | .235 | .510  | 28.6%  | 13.0% | −1.3        |

*His 4-seam fastball was his primary weapon (52.9% usage) with a .202 BA against and +1.7 run value per 100 pitches. The changeup was his only negative pitch (−1.3 run value).*

---

**Another prompt**

> "Who had the highest exit velocity in 2024?"

**Response**

*The AI calls `statcast_batter_exitvelo_barrels(year=2024)` and returns the leaderboard — Aaron Judge led with a 97.0 mph average exit velocity and 21.8% barrel rate, followed by [other top hitters]...*

---

## Available Tools

| Tool | What It Does |
|------|-------------|
| `player_lookup` | Find any player's ID, years active, and database links |
| `statcast_search` | Pitch-by-pitch data for a date range (optionally filtered by team) |
| `statcast_batter` | Every pitch a specific batter saw in a date range |
| `statcast_batter_pitch_arsenal` | Batting stats by pitch type (BA, SLG, wOBA vs fastballs, sliders, etc.) |
| `statcast_pitcher` | Every pitch a specific pitcher threw in a date range |
| `season_batting_stats` | Full-season batting stats from FanGraphs (AVG, OPS, WAR, wRC+, etc.) |
| `season_pitching_stats` | Full-season pitching stats from FanGraphs (ERA, FIP, K/9, WAR, etc.) |
| `team_season_batting_stats` | **Team** batting — full roster actual stats (FG, or BRef fallback) |
| `team_season_pitching_stats` | **Team** pitching — rotation + bullpen actual stats (FG, or BRef fallback) |
| `statcast_batter_expected_stats` | xBA, xSLG, xwOBA leaderboard — who *deserves* better stats? |
| `statcast_pitcher_expected_stats` | Expected stats allowed by pitchers |
| `expected_stats_batch` | Expected stats for **many** batters and/or pitchers in **one** call (lineups, rotations) |
| `statcast_batter_exitvelo_barrels` | Exit velocity and barrel rate leaders |
| `statcast_pitcher_exitvelo_barrels` | Exit velocity and barrel rate allowed by pitchers |
| `statcast_pitcher_pitch_arsenal` | Pitch mix breakdown (% fastball, slider, curve, etc.) |
| `statcast_pitcher_arsenal_stats` | Performance stats per pitch type (whiff rate, BA against, etc.) |
| `sprint_speed_leaderboard` | Fastest players in baseball by sprint speed |
| `team_standings` | Division standings for any season |
| `batter_percentile_ranks` | Statcast percentile ranks for hitters (exit velo, barrel%, xwOBA, etc.) |
| `pitcher_percentile_ranks` | Statcast percentile ranks for pitchers (stuff, spin, whiff%, etc.) |
| `outs_above_average` | Defensive OAA leaderboard by position (SS, CF, `ALL`, etc.) |
| `outfield_directional_oaa` | Outfield OAA by direction (back/in, L/R) |
| `batting_stats_date_range` | Batting stats over any date range (Baseball Reference) |
| `pitching_stats_date_range` | Pitching stats over any date range (Baseball Reference) |

**46 tools total.** Core table above; **extended** tools add schedules, splits, Lahman history, draft/prospects, WAR files, extra Statcast defense/movement, league team totals, single-game pitch logs, and batter–pitcher matchup summaries. Call **`statcast_tool_directory`** for the full list, or see [TOOLS_SUMMARY.md](TOOLS_SUMMARY.md) and [REFERENCE.md](REFERENCE.md).

### Extended tools (high level)

| Tool | What it does |
|------|----------------|
| `statcast_tool_directory` | Markdown catalog of **all** tools |
| `team_schedule` | Team schedule & scores (Baseball Reference) |
| `player_stat_splits` | BRef splits (platoon, home/away, …) |
| `statcast_game_pitches` | Every pitch in one game (`game_pk`) |
| `batter_vs_pitcher_statcast` | Statcast summary for one batter vs one pitcher |
| `lahman_season_batting` / `lahman_season_pitching` / `lahman_season_teams` | Lahman / Baseball Data Bank slices |
| `top_prospects_mlb` | MLB Pipeline–style prospect list |
| `amateur_draft_round` | Amateur draft by year + round |
| `war_daily_batting` / `war_daily_pitching` | BRef WAR component files |
| `season_fielding_stats` | FanGraphs fielding leaderboard |
| `league_team_batting_totals` / `league_team_pitching_totals` | FG team lines (league-wide) |
| `statcast_running_splits_detail` | 90 ft sprint splits |
| `statcast_outfield_catch_probability` | OF catch prob / stars |
| `statcast_outfield_jump` | OF jump metric |
| `statcast_catcher_framing` / `statcast_catcher_poptime` | Catcher framing & pop time |
| `statcast_pitcher_pitch_movement` / `statcast_pitcher_active_spin_leaderboard` | Pitch movement & active spin (Statcast) |

**Team seasons:** Use **`team_season_batting_stats`** / **`team_season_pitching_stats`** with a 3-letter code (`PHI`, `NYY`, …) for a full roster’s **actual** stats (lineup + staff). FanGraphs is tried first; Baseball Reference is used if FG fails or returns nothing.

**Player search:** Nearly every leaderboard/stat tool accepts optional **`player_name`** (e.g. `"Aaron Judge"`) so you get that player’s full rows instead of only the first 50 in the table. For **groups** (full lineup + rotation, “all starters”), use **`expected_stats_batch`** with comma-separated names — the server does **not** pull MLB rosters automatically; list names explicitly or resolve them first (e.g. web / `player_lookup`). Pitch-level tools already take a name via `statcast_batter` / `statcast_pitcher`. `team_standings` is team-only.

## Quick Start

### Prerequisites

- **Python 3.10+** — [download here](https://www.python.org/downloads/) if you don't have it
- **An MCP-compatible client** — such as [Claude Desktop](https://claude.ai/download), [Cursor](https://cursor.com), or VS Code with Copilot

### Option 1: Install from PyPI (Recommended)

```bash
# Using uv (fastest)
uv pip install statcast-mcp

# Or using pip
pip install statcast-mcp
```

### Option 2: Install from Source

```bash
git clone https://github.com/YOUR_USERNAME/statcast-mcp.git
cd statcast-mcp
uv pip install .
```

## Setup

### Claude Desktop

Add this to your Claude Desktop configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "statcast": {
      "command": "statcast-mcp"
    }
  }
}
```

If you installed from source and want to run it directly:

```json
{
  "mcpServers": {
    "statcast": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/statcast-mcp", "statcast-mcp"]
    }
  }
}
```

### Cursor

Open **Cursor Settings → MCP** and add a new server:

- **Name**: `statcast`
- **Type**: `command`
- **Command**: `statcast-mcp`

Or add to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "statcast": {
      "command": "statcast-mcp"
    }
  }
}
```

### VS Code (Copilot)

Add to your VS Code `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "statcast": {
        "command": "statcast-mcp"
      }
    }
  }
}
```

## Example Queries

### Looking Up a Player

> "Look up Shohei Ohtani"

Returns the player's MLBAM ID, FanGraphs ID, Baseball Reference ID, and years active.

### Pitch-Level Data

> "Show me all the pitches from the Dodgers game on October 15, 2024"

```
statcast_search(start_date="2024-10-15", team="LAD")
```

### Batter Analysis

> "What pitches did Juan Soto see from July 1 to July 31, 2024?"

```
statcast_batter(player_name="Juan Soto", start_date="2024-07-01", end_date="2024-07-31")
```

> "How does Aaron Judge hit against different pitch types?" (e.g. 2023, 106 games)

```
statcast_batter_pitch_arsenal(year=2023, player_name="Aaron Judge")
```

### Season Leaderboards

> "Who were the top hitters in 2024 by wRC+?"

```
season_batting_stats(start_season=2024)
```

### Expected Stats (Find Undervalued Players)

> "Show me batters whose expected stats were way higher than their actual stats in 2024"

```
statcast_batter_expected_stats(year=2024)
```

> "What are Aaron Judge's expected stats vs actual in 2025?"

```
statcast_batter_expected_stats(year=2025, player_name="Aaron Judge")
```

### Exit Velocity Leaders

> "Who hit the ball hardest in 2024?"

```
statcast_batter_exitvelo_barrels(year=2024)
```

### Pitcher Arsenal

> "What pitches does Spencer Strider throw and how effective are they?"

```
statcast_pitcher_pitch_arsenal(year=2024)
statcast_pitcher_arsenal_stats(year=2024)
```

### Sprint Speed

> "Who are the fastest players in baseball?"

```
sprint_speed_leaderboard(year=2024)
```

### Standings

> "Show me the 2024 MLB standings"

```
team_standings(season=2024)
```

### Percentile ranks & defense

> "What are Aaron Judge's Statcast percentile ranks in 2024?"

```
batter_percentile_ranks(year=2024, player_name="Aaron Judge")
```

> "Who were the best defensive shortstops by OAA in 2024?"

```
outs_above_average(year=2024, position="SS")
```

### Hot streaks (date ranges)

> "Who hit the best from July 1 to July 31, 2024?"

```
batting_stats_date_range(start_date="2024-07-01", end_date="2024-07-31")
```

## Data Sources

All data is sourced from:

- [**Baseball Savant**](https://baseballsavant.mlb.com/) — Statcast pitch-level and leaderboard data (2008+)
- [**FanGraphs**](https://www.fangraphs.com/) — Season-level batting and pitching statistics
- [**Baseball Reference**](https://www.baseball-reference.com/) — Player identification, daily stat ranges, and cross-references

## Reference Guide

For detailed tool-by-tool documentation, row limits, parameters, and usage patterns, see [REFERENCE.md](REFERENCE.md).

**Social / sharing:** Short descriptions and hashtag ideas for posts are in [TOOLS_SUMMARY.md](TOOLS_SUMMARY.md).

## Notes

- **Date ranges**: Statcast data is available from 2008 onward. Some metrics (exit velocity, launch angle) are only available from 2015+.
- **Query speed**: Shorter date ranges return faster. For pitch-level data, keep ranges to 1-5 days when possible.
- **Rate limits**: Baseball Savant limits individual requests to ~30,000 rows. The server handles splitting larger queries automatically.
- **Player names**: Tools accept names like "Mike Trout", "Trout, Mike", or "Shohei Ohtani". The server resolves names to MLB IDs automatically.

## Development

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/statcast-mcp.git
cd statcast-mcp

# Create a virtual environment and install in editable mode
uv venv
uv pip install -e ".[dev]"

# Run the server locally
statcast-mcp

# Test with the MCP Inspector
npx @modelcontextprotocol/inspector statcast-mcp

# Smoke-test all 24 tools (needs network; ~2024 fixtures)
PYTHONPATH=src python scripts/verify_tools.py
```

## Contributing

Contributions are welcome! Some ideas:

- Add more tools (game scores, team batting/pitching, historical data)
- Improve player name resolution
- Add data caching for faster repeated queries
- Create prompt templates for common analyses

## License

MIT
