# Statcast MCP — tools summary

**Tool count: 46** (call `statcast_tool_directory` in the MCP for the full catalog).

**One-liner for social posts**

> **Statcast MCP** — **46** tools for MLB data in ChatGPT / Cursor / Claude: Statcast (pitches, games, matchups, defense, movement, active spin), FanGraphs season & team leaderboards, **full team rosters** (FG + BRef), **Lahman** historical slices, **schedules & splits** (BRef), **draft & prospects**, **WAR** daily files, xStats (incl. **batch** lineups), sprint & running splits, standings, percentiles, OAA, and BRef date-range streaks. Natural language → Savant / FG / BRef / Lahman / MLB data.

**Shorter (~280 chars)**

> Statcast MCP: **46** @MLB data tools for AI — Statcast pitch/game/matchup data, FG & team seasons, Lahman history, schedules & BRef splits, draft/prospects, WAR files, xStats batch lineups, defense (OAA, OF jump, catch prob, framing), movement/active spin, standings, percentiles. pybaseball + MCP. ⚾📊

**Hashtags (optional)**

`#MLB` `#Sabermetrics` `#Statcast` `#MCP` `#OpenSource` `#Python`

**Tool count by area**

| Area | Tools |
|------|--------|
| Discovery | `statcast_tool_directory` |
| Identity | `player_lookup` |
| Pitch-level Statcast | `statcast_search`, `statcast_batter`, `statcast_pitcher`, `statcast_game_pitches` |
| Matchups & splits | `batter_vs_pitcher_statcast`, `player_stat_splits` |
| Season (league) | `season_batting_stats`, `season_pitching_stats`, `season_fielding_stats` |
| Season (**team roster**) | `team_season_batting_stats`, `team_season_pitching_stats` |
| League team totals (FG) | `league_team_batting_totals`, `league_team_pitching_totals` |
| Schedule | `team_schedule` |
| Expected / barrels / arsenals | `statcast_batter_expected_stats`, `statcast_pitcher_expected_stats`, `expected_stats_batch`, `statcast_batter_pitch_arsenal`, `statcast_batter_exitvelo_barrels`, `statcast_pitcher_exitvelo_barrels`, `statcast_pitcher_pitch_arsenal`, `statcast_pitcher_arsenal_stats`, `statcast_pitcher_pitch_movement`, `statcast_pitcher_active_spin_leaderboard` |
| Running | `sprint_speed_leaderboard`, `statcast_running_splits_detail` |
| Standings | `team_standings` |
| Statcast percentiles | `batter_percentile_ranks`, `pitcher_percentile_ranks` |
| Defense (Statcast) | `outs_above_average`, `outfield_directional_oaa`, `statcast_outfield_catch_probability`, `statcast_outfield_jump`, `statcast_catcher_framing`, `statcast_catcher_poptime` |
| BRef date ranges | `batting_stats_date_range`, `pitching_stats_date_range` |
| Historical (Lahman) | `lahman_season_batting`, `lahman_season_pitching`, `lahman_season_teams` |
| Prospects & draft | `top_prospects_mlb`, `amateur_draft_round` |
| WAR files | `war_daily_batting`, `war_daily_pitching` |

**Verify locally**

```bash
PYTHONPATH=src python scripts/verify_tools.py
```

Expect **0 failures**; some tools may **WARN** if FanGraphs or MLB.com block automated requests (403/HTML). Lahman first use may download a large zip.
