# Statcast MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that lets you query **MLB Statcast data using plain English**. Ask your AI assistant about players, games, stats, leaderboards, and more — no coding required.

Built on [pybaseball](https://github.com/jldbc/pybaseball), this server gives AI assistants direct access to data from **Baseball Savant**, **FanGraphs**, and **Baseball Reference**.

## What Can You Ask?

Once connected, just talk to your AI assistant naturally:

- *"How did Aaron Judge hit in July 2024?"*
- *"Show me Gerrit Cole's pitch arsenal this season"*
- *"Who had the highest exit velocity in 2024?"*
- *"What were the NL standings at the end of 2023?"*
- *"Find me the most undervalued hitters — compare xBA to actual BA"*
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
| `statcast_batter_expected_stats` | xBA, xSLG, xwOBA leaderboard — who *deserves* better stats? |
| `statcast_pitcher_expected_stats` | Expected stats allowed by pitchers |
| `statcast_batter_exitvelo_barrels` | Exit velocity and barrel rate leaders |
| `statcast_pitcher_exitvelo_barrels` | Exit velocity and barrel rate allowed by pitchers |
| `statcast_pitcher_pitch_arsenal` | Pitch mix breakdown (% fastball, slider, curve, etc.) |
| `statcast_pitcher_arsenal_stats` | Performance stats per pitch type (whiff rate, BA against, etc.) |
| `sprint_speed_leaderboard` | Fastest players in baseball by sprint speed |
| `team_standings` | Division standings for any season |

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

## Data Sources

All data is sourced from:

- [**Baseball Savant**](https://baseballsavant.mlb.com/) — Statcast pitch-level and leaderboard data (2008+)
- [**FanGraphs**](https://www.fangraphs.com/) — Season-level batting and pitching statistics
- [**Baseball Reference**](https://www.baseball-reference.com/) — Player identification and cross-references

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
```

## Contributing

Contributions are welcome! Some ideas:

- Add more tools (game scores, team batting/pitching, historical data)
- Improve player name resolution
- Add data caching for faster repeated queries
- Create prompt templates for common analyses

## License

MIT
