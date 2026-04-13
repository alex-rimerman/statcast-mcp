# StatCast MCP Reference Guide

> Row defaults and **5000-row hard cap** match `src/statcast_mcp/limits.py` and tool docstrings. Older empirical notes below are illustrative.

---

## Key Constraints Summary

Unless noted, tools accept optional **`max_output_rows`**; values are clamped to **`MAX_OUTPUT_ROWS_CAP` (5000)**. Defaults below are when `max_output_rows` is omitted.

| Tool | Default rows shown | Max via `max_output_rows` | Notes |
|------|-------------------|---------------------------|--------|
| `player_lookup` | **10** | 5000 | Fuzzy lookup can return multiple Chadwick rows |
| `statcast_search` | **100** | 5000 | Pitch-level, date range + optional team |
| `statcast_batter` | **100** | 5000 | Pitch-level, named batter |
| `statcast_pitcher` | **100** | 5000 | Pitch-level, named pitcher |
| `season_batting_stats` | **50** | 5000 | FanGraphs; optional **`sort_by`**, **`sort_descending`**. **BRef fallback** (single-season only) if FG fails — response may show `mlbID` / BRef-style columns |
| `season_pitching_stats` | **50** | 5000 | FanGraphs only (no BRef fallback in server) |
| `team_season_batting_stats` | **200** | 5000 | Full team roster, FG or BRef |
| `team_season_pitching_stats` | **200** | 5000 | Full team staff, FG or BRef |
| `statcast_batter_expected_stats` | **50** | 5000 | xBA/xSLG/xwOBA leaderboard |
| `statcast_pitcher_expected_stats` | **50** | 5000 | xBA/xSLG/xwOBA/xERA allowed leaderboard |
| `expected_stats_batch` | All matched rows (capped) | 5000 **per** batters/pitchers section | Still only **2** Savant leaderboard fetches total |
| `statcast_batter_pitch_arsenal` | **50** (full player filter: all pitch-type rows) | 5000 | Per-pitch-type batting stats |
| `statcast_pitcher_pitch_arsenal` | **50** | 5000 | Pitch velocity mix breakdown |
| `statcast_pitcher_arsenal_stats` | **50** | 5000 | Per-pitch-type performance for pitchers |
| `statcast_batter_exitvelo_barrels` | **50** | 5000 | Exit velocity / barrel leaderboard |
| `statcast_pitcher_exitvelo_barrels` | **50** | 5000 | Exit velocity / barrel allowed |
| `sprint_speed_leaderboard` | **50** | 5000 | Sprint speed (ft/sec) |
| `team_standings` | **15 per division** table | 5000 per division | Six division tables (30 teams if each table lists its division) |
| `batter_percentile_ranks` | **50** (1 if `player_name`) | 5000 | Statcast batter percentiles |
| `pitcher_percentile_ranks` | **50** (1 if `player_name`) | 5000 | Statcast pitcher percentiles |
| `outs_above_average` | **50** | 5000 | OAA by position; not catcher |
| `outfield_directional_oaa` | **50** | 5000 | OF OAA by direction |
| `batting_stats_date_range` | **50** | 5000 | BRef batting over custom dates |
| `pitching_stats_date_range` | **50** | 5000 | BRef pitching over custom dates |

**Player filter:** For most leaderboards, pass **`player_name`** to return only that player’s rows. For **several** expected-stats players at once, use **`expected_stats_batch`**. **`team_season_*`** take **`team`** plus optional **`player_name`**. **`sort_by`** applies only to **`season_batting_stats`** (not pitching). Tools that do not take `player_name` for filtering a leaderboard: `player_lookup`, `statcast_search`, `statcast_batter`, `statcast_pitcher` (those two are already player-scoped), `team_standings`.

---

## Tool-by-Tool Reference

### 1. `player_lookup`

**Purpose:** Look up a player's IDs and years active.

**Parameters:**
- `player_name` (required) — Full name, e.g. `"Mike Trout"` or `"Trout, Mike"`
- `max_output_rows` (optional) — Rows shown (default **10**, maximum **5000**).

**Returns:** One row per Chadwick match; fuzzy lookup can return multiple rows for common names.

**Key Columns:**

| Column | Description |
|--------|-------------|
| `name_last`, `name_first` | Player name |
| `key_mlbam` | MLB Advanced Media ID (used in Statcast pitch-level data) |
| `key_retro` | Retrosheet ID |
| `key_bbref` | Baseball-Reference ID |
| `key_fangraphs` | FanGraphs ID |
| `mlb_played_first` | First MLB season |
| `mlb_played_last` | Last MLB season |

**Notes:**
- Use this first to verify a player's MLBAM ID before running pitch-level queries.
- Returns an empty result if the name is not found (no error thrown).

---

### 2. `statcast_search`

**Purpose:** Retrieve pitch-level Statcast data by date range, with optional team filter. Does NOT filter by a specific player.

**Parameters:**
- `start_date` (required) — `YYYY-MM-DD`
- `end_date` (optional) — `YYYY-MM-DD`, defaults to `start_date`
- `team` (optional) — 3-letter abbreviation (e.g. `"NYY"`, `"LAD"`, `"BOS"`)
- `max_output_rows` (optional) — Default **100**, maximum **5000**

**Default row display: 100** (observed: 162 pitches for 1 game day + 1 team, returned 100)

**Performance tip:** Keep date ranges to 1–5 days. Longer ranges are slow and will truncate more heavily.

**Data availability:** 2008 season onward.

**Key Columns:**

| Column | Description |
|--------|-------------|
| `game_date` | Date of pitch |
| `player_name` | Pitcher's name (format: "Last, First") |
| `batter` | Batter MLBAM ID |
| `pitcher` | Pitcher MLBAM ID |
| `pitch_type` | Pitch type code (FF, SL, CU, CH, SI, FC, FS, ST, etc.) |
| `pitch_name` | Full pitch name (4-Seam Fastball, Slider, etc.) |
| `release_speed` | Pitch velocity (mph) |
| `release_spin_rate` | Spin rate (rpm) |
| `events` | Plate appearance outcome (home_run, strikeout, field_out, etc.) — null for non-terminal pitches |
| `description` | Pitch result (called_strike, swinging_strike, ball, foul, hit_into_play, etc.) |
| `zone` | Strike zone location (1–9 in zone, 11–14 outside) |
| `launch_speed` | Exit velocity (mph) — null if not batted into play |
| `launch_angle` | Launch angle (degrees) — null if not batted into play |
| `hit_distance_sc` | Hit distance (feet) — null if not batted into play |
| `estimated_ba_using_speedangle` | xBA on contact — null if not batted into play |
| `estimated_woba_using_speedangle` | xwOBA — populated on terminal pitches |
| `bb_type` | Batted ball type (ground_ball, fly_ball, line_drive, popup) |
| `stand` | Batter handedness (L/R) |
| `p_throws` | Pitcher handedness (L/R) |
| `home_team`, `away_team` | Team abbreviations |
| `inning` | Inning number |
| `balls`, `strikes` | Count when pitch was thrown |

---

### 3. `statcast_batter`

**Purpose:** Pitch-level data for a specific named batter within a date range.

**Parameters:**
- `player_name` (required) — Full name, e.g. `"Aaron Judge"`
- `start_date` (required) — `YYYY-MM-DD`
- `end_date` (optional) — `YYYY-MM-DD`, defaults to `start_date`
- `max_output_rows` (optional) — Default **100**, maximum **5000**

**Default row display: 100** (observed: 116 pitches across 7 days, returned 100)

**Data availability:** 2008 season onward.

**Returns:** Same pitch-level columns as `statcast_search` (see above). The tool auto-resolves the player name to an MLBAM ID.

**Notes:**
- For active hitters, even a single week can exceed 100 rows. Keep ranges to ~3–5 days for complete data.
- Returns `"No data found"` if the player did not appear in any games in that range.

---

### 4. `statcast_pitcher`

**Purpose:** Pitch-level data for a specific named pitcher within a date range.

**Parameters:**
- `player_name` (required) — Full name, e.g. `"Gerrit Cole"`
- `start_date` (required) — `YYYY-MM-DD`
- `end_date` (optional) — `YYYY-MM-DD`, defaults to `start_date`
- `max_output_rows` (optional) — Default **100**, maximum **5000**

**Default row display: 100**

**Data availability:** 2008 season onward.

**Returns:** Same pitch-level columns as `statcast_search`.

**Notes:**
- A starter typically throws ~85–100 pitches per game, so a 1-start range will fit in 100 rows.
- Returns `"No data found"` if the pitcher did not appear (injured, off-day, etc.) — **not an error**.
- For relievers, 1–2 weeks is generally safe without truncation.

---

### 5. `season_batting_stats`

**Purpose:** Season-level batting statistics from FanGraphs for all qualifying hitters (with optional Baseball Reference fallback).

**Parameters:**
- `start_season` (required) — Year integer, e.g. `2024`
- `end_season` (optional) — Year integer; omit for single season
- `min_plate_appearances` (optional) — Integer; omit to use FanGraphs default qualified threshold (~502 PA). Applied to BRef data after fetch when fallback runs.
- `player_name` (optional) — Filter to one player after sort/limit.
- `max_output_rows` (optional) — Rows in the markdown table (default **50**, maximum **5000**).
- `sort_by` (optional) — Column name to sort before truncating (e.g. `SLG`, `HR`, `wRC+`, `OPS`). Useful for “top 200 by slugging”. If the column is missing, a **Note** is prepended and the original order is kept.
- `sort_descending` (optional) — Default **True** (highest first when `sort_by` is set).

**Default row display: 50**; increase with `max_output_rows` for longer leaderboards.

**FanGraphs vs Baseball Reference:**
- Primary path: **`batting_stats`** from FanGraphs.
- If FanGraphs errors (e.g. HTTP 403) and **`start_season == end_season`**, the server retries with **`batting_stats_bref`** and prepends *Data source: Baseball Reference (FanGraphs was unavailable).*
- **Multi-season** ranges do **not** use BRef fallback — only the error from FanGraphs is returned.

**Notes:**
- The default qualified threshold (omitting `min_plate_appearances`) corresponds to ~502 PA (FanGraphs standard).
- Setting `min_plate_appearances=1` can return hundreds of players; output is still limited by `max_output_rows`.

**Key Columns (partial — FanGraphs has 150+ total):**

| Column | Description |
|--------|-------------|
| `IDfg` | FanGraphs player ID (FG path) |
| `Season` | Season year |
| `Name`, `Team` | Player and team |
| `Age` | Player age |
| `G`, `AB`, `PA`, `H` | Games, at-bats, plate appearances, hits |
| `HR`, `RBI`, `SB` | Home runs, RBI, stolen bases |
| `BB%`, `K%` | Walk rate, strikeout rate |
| `AVG`, `OBP`, `SLG`, `OPS` | Standard rate stats |
| `ISO`, `BABIP`, `wOBA` | Advanced rate stats |
| `wRC+` | Park/league-adjusted wRC (100 = average) |
| `WAR` | Wins Above Replacement |
| `WPA`, `RE24` | Win probability added, run expectancy |
| `O-Swing%`, `Z-Swing%`, `SwStr%` | Plate discipline stats |
| `FB%`, `GB%`, `LD%` | Batted ball rates |
| `wFB`, `wSL`, `wCH`, etc. | Pitch value run values |

**BRef fallback:** Columns follow Baseball Reference / pybaseball `batting_stats_bref` (e.g. `mlbID` instead of `IDfg`). Sorting and `min_plate_appearances` still apply where possible.

---

### 6. `season_pitching_stats`

**Purpose:** Season-level pitching statistics from FanGraphs for all qualifying pitchers.

**Parameters:**
- `start_season` (required) — Year integer
- `end_season` (optional) — Year integer
- `min_innings` (optional) — Integer; omit to use FanGraphs default qualified threshold
- `player_name` (optional) — Filter to one pitcher.
- `max_output_rows` (optional) — Rows in the markdown table (default **50**, maximum **5000**). There is no **`sort_by`** parameter on this tool.

**Default row display: 50.**

**Notes:**
- Default qualified threshold is ~162 IP (1 IP per team game).
- Setting `min_innings=1` returns hundreds of pitchers; output is limited by `max_output_rows`.

**Key Columns (partial — there are 150+ total):**

| Column | Description |
|--------|-------------|
| `IDfg` | FanGraphs player ID |
| `Season` | Season year |
| `Name`, `Team` | Player and team |
| `W`, `L`, `ERA`, `FIP` | Traditional and fielding-independent stats |
| `IP`, `G`, `GS`, `SV` | Innings pitched, games, starts, saves |
| `K/9`, `BB/9`, `K/BB`, `HR/9` | Rate stats |
| `WHIP`, `BABIP`, `LOB%` | Strand and luck stats |
| `xFIP`, `SIERA`, `tERA` | Advanced ERA estimators |
| `SwStr%`, `O-Swing%`, `Z-Contact%` | Plate discipline |
| `GB%`, `FB%`, `LD%`, `IFFB%` | Batted ball profile |
| `WAR`, `RAR`, `WPA`, `RE24` | Value stats |

---

### 7. `statcast_batter_expected_stats`

**Purpose:** Expected stats leaderboard (xBA, xSLG, xwOBA vs. actual) for batters.

**Parameters:**
- `year` (required) — Season year integer
- `min_plate_appearances` (optional) — Default: 50
- `player_name` (optional) — If set, returns **only that player’s row** (full Statcast table is fetched server-side, so stars are not cut off by the 50-row display limit).

**Row limit: 50** for leaderboard mode; **1 row** (or a few) when `player_name` is set.

**Sorted by:** Plate appearances descending (most PA first).

**Key Columns:**

| Column | Description |
|--------|-------------|
| `last_name, first_name` | Player name |
| `player_id` | MLBAM ID |
| `year` | Season |
| `pa`, `bip` | Plate appearances, balls in play |
| `ba`, `est_ba` | Actual BA, expected BA |
| `est_ba_minus_ba_diff` | xBA − BA (positive = underperforming) |
| `slg`, `est_slg` | Actual SLG, expected SLG |
| `est_slg_minus_slg_diff` | xSLG − SLG |
| `woba`, `est_woba` | Actual wOBA, expected wOBA |
| `est_woba_minus_woba_diff` | xwOBA − wOBA |

---

### 8. `statcast_pitcher_expected_stats`

**Purpose:** Expected stats allowed leaderboard for pitchers. Includes xERA.

**Parameters:**
- `year` (required) — Season year integer
- `min_plate_appearances` (optional) — Default: 50
- `player_name` (optional) — Filter to one pitcher’s row (same as batter expected stats).

**Row limit: 50** for leaderboard; **1 row** when `player_name` is set.

**Sorted by:** Plate appearances faced descending.

**Key Columns:** All columns from `statcast_batter_expected_stats`, plus:

| Column | Description |
|--------|-------------|
| `era` | Actual ERA |
| `xera` | Expected ERA based on contact quality |
| `era_minus_xera_diff` | ERA − xERA (positive = ERA worse than expected) |

---

### 9. `statcast_batter_pitch_arsenal`

**Purpose:** Batting performance broken down by pitch type faced.

**Parameters:**
- `year` (required) — Season year integer
- `player_name` (optional) — Filter to a specific batter; if omitted returns full leaderboard
- `min_plate_appearances` (optional) — Minimum PA per pitch type; default: 10

**Row limit:**
- **No truncation when `player_name` is provided** — all pitch types returned (e.g., 8 rows for Aaron Judge)
- **50 rows** when no player is specified (full leaderboard mode)

**Key Columns:**

| Column | Description |
|--------|-------------|
| `player_id`, `last_name, first_name` | Player identity |
| `team_name_alt` | Team abbreviation |
| `pitch_type`, `pitch_name` | Pitch code and full name |
| `run_value_per_100` | Run value per 100 pitches (positive = batter advantage) |
| `run_value` | Total run value |
| `pitches`, `pitch_usage` | Pitch count and usage % |
| `pa` | Plate appearances where pitch was thrown |
| `ba`, `slg`, `woba` | Batting performance against this pitch |
| `whiff_percent` | Whiff rate |
| `k_percent` | Strikeout rate |
| `put_away` | Put-away rate (K% on 2-strike counts) |
| `est_ba`, `est_slg`, `est_woba` | Expected stats on contact |
| `hard_hit_percent` | Hard-hit rate (exit velo ≥ 95 mph) |

---

### 10. `statcast_pitcher_pitch_arsenal`

**Purpose:** Pitch mix and velocity breakdown for pitchers (how often each pitch is thrown and how fast).

**Parameters:**
- `year` (required) — Season year integer
- `min_pitches` (optional) — Minimum total pitches thrown; default: 100

**Row limit: 50** (observed: 712 qualifying pitchers in 2024, returned 50)

**Key Columns:**

| Column | Description |
|--------|-------------|
| `last_name, first_name` | Player name |
| `pitcher` | MLBAM pitcher ID |
| `ff_avg_speed` | 4-seam fastball average velocity |
| `si_avg_speed` | Sinker average velocity |
| `fc_avg_speed` | Cutter average velocity |
| `sl_avg_speed` | Slider average velocity |
| `ch_avg_speed` | Changeup average velocity |
| `cu_avg_speed` | Curveball average velocity |
| `fs_avg_speed` | Split-finger average velocity |
| `kn_avg_speed` | Knuckleball average velocity |
| `st_avg_speed` | Sweeper average velocity |
| `sv_avg_speed` | Slurve average velocity |

**Notes:**
- `nan` values mean the pitcher did not throw that pitch type.
- This tool shows velocity only, not pitch usage %. For usage %, use `statcast_pitcher_arsenal_stats`.

---

### 11. `statcast_pitcher_arsenal_stats`

**Purpose:** Performance stats (run value, whiff rate, BA allowed, etc.) broken down by pitch type for pitchers.

**Parameters:**
- `year` (required) — Season year integer
- `min_plate_appearances` (optional) — Minimum PA per pitch type; default: 25

**Row limit: 50** (observed: 1,896 pitcher-pitch-type rows in 2024, returned 50)

**Key Columns:** Same schema as `statcast_batter_pitch_arsenal`:
`player_id`, `team_name_alt`, `pitch_type`, `pitch_name`, `run_value_per_100`, `run_value`, `pitches`, `pitch_usage`, `pa`, `ba`, `slg`, `woba`, `whiff_percent`, `k_percent`, `put_away`, `est_ba`, `est_slg`, `est_woba`, `hard_hit_percent`

**Notes:**
- Each row is a single pitcher × pitch type combination.
- With 1,896 rows for 2024 at 25 PA minimum, there are many more rows than can be returned. A pitcher with 5 pitch types would contribute 5 rows. To get stats for a specific pitcher, use `statcast_batter_pitch_arsenal` (which doesn't have a pitcher-specific filter), or cross-reference `player_id` with results from `player_lookup`.

---

### 12. `statcast_batter_exitvelo_barrels`

**Purpose:** Exit velocity, barrel rate, and hard-hit rate leaderboard for batters.

**Parameters:**
- `year` (required) — Season year integer
- `min_batted_ball_events` (optional) — Default: 50

**Row limit: 50** (observed: 485 qualifying batters in 2024, returned 50)

**Sorted by:** Batted ball events descending.

**Key Columns:**

| Column | Description |
|--------|-------------|
| `last_name, first_name` | Player name |
| `player_id` | MLBAM ID |
| `attempts` | Batted ball events |
| `avg_hit_angle` | Average launch angle |
| `anglesweetspotpercent` | Sweet spot % (launch angle 8–32°) |
| `max_hit_speed` | Max exit velocity (mph) |
| `avg_hit_speed` | Average exit velocity (mph) |
| `ev50` | Median exit velocity |
| `fbld` | Avg EV on fly balls + line drives |
| `gb` | Avg EV on ground balls |
| `max_distance` | Max hit distance (feet) |
| `avg_distance` | Average hit distance |
| `avg_hr_distance` | Average HR distance |
| `ev95plus` | Number of 95+ mph batted balls |
| `ev95percent` | Rate of 95+ mph batted balls |
| `barrels` | Total barrels |
| `brl_percent` | Barrel % (barrels / BBE) |
| `brl_pa` | Barrel per PA % |

---

### 13. `statcast_pitcher_exitvelo_barrels`

**Purpose:** Exit velocity and barrel rate allowed leaderboard for pitchers.

**Parameters:**
- `year` (required) — Season year integer
- `min_batted_ball_events` (optional) — Default: 50

**Row limit: 50** (observed: 573 qualifying pitchers in 2024, returned 50)

**Sorted by:** Batted ball events (faced) descending.

**Key Columns:** Same schema as `statcast_batter_exitvelo_barrels` (columns represent what the pitcher *allowed*, not produced).

---

### 14. `sprint_speed_leaderboard`

**Purpose:** Sprint speed in feet per second, measured on competitive running plays.

**Parameters:**
- `year` (required) — Season year integer
- `min_opportunities` (optional) — Default: 10

**Row limit: 50**

**Key Columns:** Player name, sprint speed (ft/sec), opportunities (competitive runs).

---

### 15. `team_standings`

**Purpose:** MLB division standings for a full season.

**Parameters:**
- `season` (required) — Year integer, e.g. `2024`
- `max_output_rows` (optional) — Maximum rows **per division** table (default **15**, maximum **5000**). Normal seasons have 5 teams per division, so the default shows every team.

**Returns:** Up to 6 division tables (AL East, AL Central, AL West, NL East, NL Central, NL West). Each table is truncated separately if a division has more rows than `max_output_rows`.

**Key Columns:**

| Column | Description |
|--------|-------------|
| `Tm` | Team name |
| `W` | Wins |
| `L` | Losses |
| `W-L%` | Winning percentage |
| `GB` | Games behind division leader (`--` for leader) |

---

### 16. `batter_percentile_ranks`

**Purpose:** Statcast percentile ranks (0–100) for qualified hitters — exit velocity, barrel%, xwOBA, chase%, sprint speed, etc.

**Parameters:** `year` (required), `player_name` (optional — one row for that player).

**Row limit:** 50 for full leaderboard; 1 row when filtered.

---

### 17. `pitcher_percentile_ranks`

**Purpose:** Statcast percentile ranks for qualified pitchers — spin, velocity, whiff%, xERA-related metrics, etc.

**Parameters:** `year` (required), `player_name` (optional).

---

### 18. `outs_above_average`

**Purpose:** Outs Above Average (OAA) by fielding position.

**Parameters:**
- `year` (required)
- `position` — `SS`, `2B`, `3B`, `1B`, `LF`, `CF`, `RF`, or `ALL` / `all` for all positions in the leaderboard
- `min_attempts` — `"q"` (qualified) or an integer (default `"q"`)

**Note:** Catcher is **not** supported by Baseball Savant’s OAA leaderboard used here.

---

### 19. `outfield_directional_oaa`

**Purpose:** Outfielders’ OAA split by direction (e.g. back vs in, toward 3B vs 1B lines).

**Parameters:** `year` (required), `min_opportunities` (optional, default `"q"`).

---

### 20. `batting_stats_date_range`

**Purpose:** Aggregated batting stats between two dates (Baseball Reference daily leaders table).

**Parameters:** `start_date`, `end_date` — `YYYY-MM-DD`, year ≥ 2008.

---

### 21. `pitching_stats_date_range`

**Purpose:** Aggregated pitching stats between two dates (Baseball Reference).

**Parameters:** Same as batting date range.

---

### 22. `expected_stats_batch`

**Purpose:** Return Statcast **expected** stats (xBA, xSLG, xwOBA; pitchers also xERA) for **multiple** batters and/or pitchers in a **single** tool call — intended for “whole lineup + rotation”, “Yankees starters”, etc.

**Parameters:**
- `year` (required)
- `batters` (optional) — Comma-, semicolon-, or newline-separated names (e.g. `"Aaron Judge, Juan Soto, Giancarlo Stanton"`)
- `pitchers` (optional) — Same format for pitchers
- `min_plate_appearances` (optional) — Default: 50 (applies to both leaderboards)
- `max_output_rows` (optional) — Caps rows in **each** of the batter and pitcher markdown sections (default: all matched rows, up to **5000** per section)

Provide at least one of `batters` or `pitchers`.

**Implementation:** Fetches the full batter expected-stats leaderboard **once** and the full pitcher expected-stats leaderboard **once**, then filters to each requested name (same matching rules as `player_name` elsewhere). Missing or non-qualifying names are listed in **Notes** at the end of each section.

**Roster caveat:** This MCP does **not** query a live 26-man or lineup API. The client must supply current player names (from context, the web, or repeated `player_lookup` calls).

**Calendar caveat:** For the **current** season year (e.g. 2026 in March), Baseball Savant’s expected-stats **leaderboard may be empty** until enough regular-season PA/IP exist (or until the feed is published). If you get zero rows, use **`year` = previous season** for full-season xBA/xSLG/xwOBA, or lower `min_plate_appearances` after games have been played.

---

### 23. `team_season_batting_stats`

**Purpose:** **Actual** full-season batting stats for **every player** on an MLB team (not a league leaderboard). Use for “Phillies lineup”, “all 2025 Yankees hitters”, etc.

**Parameters:**
- `team` (required) — 3-letter code matching **Baseball Reference** / FanGraphs (e.g. `PHI`, `NYY`, `LAD`, `ARI`).
- `season` (required) — Year (e.g. `2025`).
- `min_plate_appearances` (optional) — Default `1`; used only for the FanGraphs request.
- `player_name` (optional) — Restrict to one batter.
- `max_output_rows` (optional) — Default **200**, maximum **5000**.

**Default row limit: 200** in the MCP output.

**Data path:** Tries **FanGraphs** (`batting_stats(..., team=...)`). If that errors or returns no rows, scrapes **Baseball Reference** (`/teams/{TEAM}/{YEAR}.shtml`) and selects the batting table with the **highest max PA** (avoids picking a postseason-only table).

**Response header** includes `**Source:** FanGraphs` or `**Source:** Baseball Reference`.

---

### 24. `team_season_pitching_stats`

**Purpose:** **Actual** full-season pitching for the **whole staff** (rotation + bullpen).

**Parameters:** Same pattern as §23, with `min_innings` (default `1`) instead of PA, plus **`max_output_rows`** (default **200**, max **5000**).

**Default row limit: 200.**

**Data path:** FanGraphs first, then BRef. The pitching table is chosen by **highest max GS** among tables with `Player` / `ERA` / `IP` / `GS` (full-season starters beat small-sample playoff tables).

**Tip:** Sort or filter on **`GS`** in the returned table to separate rotation (many starts) from relievers.

---

## Extended tools (v0.2 — 22 additional tools)

Use **`statcast_tool_directory`** for the canonical markdown list. Summary:

| Tool | Source | Notes |
|------|--------|--------|
| `statcast_tool_directory` | Local | Full catalog text |
| `team_schedule` | BRef | ~162 rows/season; `redirect_stdout` hides pybaseball prints |
| `player_stat_splits` | BRef | Requires valid BRef `key_bbref` via Chadwick; wide output |
| `statcast_game_pitches` | Savant | **100** pitch rows max in MCP; pass real `game_pk` |
| `batter_vs_pitcher_statcast` | Savant | Short date ranges; **80** sample rows + summary text |
| `lahman_season_batting` / `lahman_season_pitching` / `lahman_season_teams` | Lahman | First use may **download** the Lahman zip (~100MB); `teamID` e.g. `NYA` |
| `top_prospects_mlb` | MLB.com | May break if MLB returns HTML instead of a table |
| `amateur_draft_round` | BRef | Per **year + round** |
| `war_daily_batting` / `war_daily_pitching` | BRef files | Large tables; optional `season` filter |
| `season_fielding_stats` | FanGraphs | Same 403/500 caveats as other FG tools |
| `league_team_batting_totals` / `league_team_pitching_totals` | FanGraphs | One row per team (`team=0,ts`) |
| `statcast_running_splits_detail` | Savant | 90 ft split times |
| `statcast_outfield_catch_probability` | Savant | OF catch stars |
| `statcast_outfield_jump` | Savant | OF jump |
| `statcast_catcher_framing` | Savant | CSV format can change |
| `statcast_catcher_poptime` | Savant | Pop time to 2B/3B |
| `statcast_pitcher_pitch_movement` | Savant | `pitch_type` e.g. `FF` |
| `statcast_pitcher_active_spin_leaderboard` | Savant | May warn on old seasons |

**Tests:** `PYTHONPATH=src python scripts/verify_tools.py` exercises **46** tools (2024 fixtures).

---

## Practical Usage Patterns

### Getting complete data when truncated

Tools that return "Showing X of Y total rows" are **truncated at the displayed limit** (no pagination). Mitigations:

- **Leaderboards (season stats, expected stats, exit velo):** Pass a higher **`max_output_rows`** (up to **5000**) on tools that support it. For **`season_batting_stats`**, set **`sort_by`** to the stat you care about so the top *N* rows are meaningful. Tighten `min_plate_appearances`, `min_innings`, or `min_batted_ball_events` to shrink *Y* when you only need qualifiers. For **many** players’ expected stats, use `expected_stats_batch` instead of one call per player.
- **Pitch-level data (statcast_batter / statcast_pitcher):** Raise **`max_output_rows`** (up to 5000) and/or split the date range into smaller chunks.
- **Season batting/pitching (league):** For a **whole team’s** actual stats, use **`team_season_batting_stats`** / **`team_season_pitching_stats`**. For league leaderboards, use `season_*` with **`max_output_rows`** as needed.

### Identifying a player before querying

Always use `player_lookup` first if you're unsure of spelling or want to confirm a player's active years:
```
player_lookup("Shohei Ohtani")  →  key_mlbam: 660271, mlb_played_first: 2018
```

### Pitch type codes

| Code | Full Name |
|------|-----------|
| FF | 4-Seam Fastball |
| SI | Sinker |
| FC | Cutter |
| SL | Slider |
| ST | Sweeper |
| CU | Curveball |
| KC | Knuckle Curve |
| CH | Changeup |
| FS | Split-Finger |
| KN | Knuckleball |
| SV | Slurve |
| EP | Eephus |

### Recommended date ranges for pitch-level tools

| Scenario | Recommended range |
|----------|-------------------|
| Single game for a batter | 1 day (usually ~15–20 pitches) |
| One start for a pitcher | 1 day (usually ~85–100 pitches, fits in 100-row limit) |
| Weekly batter analysis | 3–5 days (may hit 100-row limit for everyday players) |
| Reliever stretch | 1–2 weeks (usually safe under 100 rows) |
| General statcast_search (all players) | 1 day + team filter for best precision |

---

## Known Limitations

1. **Row caps:** Default display limits (often **50** for leaderboards, **100** for pitch-level, **200** for team seasons) can be raised with **`max_output_rows`** up to **5000** per call — not “50 only”, but there is still **no pagination** beyond that cap.
2. **Very large queries:** **`max_output_rows=5000`** still produces huge markdown; clients may save output to a file instead of inline chat.
3. **`statcast_pitcher` and `statcast_batter` return no error on bad/inactive player queries** — you get `"No data found"` silently. Confirm with `player_lookup` when unsure.
4. **`season_batting_stats` / `season_pitching_stats` (FanGraphs) have 150+ columns** — wide tables; trim in post-processing if needed.
5. **`expected_stats_batch` does not resolve rosters** — you must list player names. For **actual team-wide season stats**, use **`team_season_batting_stats`** / **`team_season_pitching_stats`** instead.
6. **FanGraphs may error** — **`season_batting_stats`** (single-season) can fall back to **Baseball Reference**; **`team_season_*`** use BRef when FG fails or returns nothing. Column names may differ by source.
7. **`season_pitching_stats` has no BRef fallback** in this server — FG errors surface to the client.
8. **`sort_by`** is implemented for **`season_batting_stats`** only, not **`season_pitching_stats`**.
