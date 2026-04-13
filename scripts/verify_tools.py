#!/usr/bin/env python3
"""Smoke-test every MCP tool in statcast_mcp.server (requires network).

Usage (from repo root):
  PYTHONPATH=src python scripts/verify_tools.py

Exit code 0 if no tool raises; prints PASS/WARN/FAIL per tool.
"""

from __future__ import annotations

import sys
import traceback
from typing import Any, Callable

# Season/date fixtures (stable historical data)
YEAR = 2024
DATE = "2024-06-15"  # mid-season
RANGE_START = "2024-06-01"
RANGE_END = "2024-06-07"


def main() -> int:
    from statcast_mcp import server as s

    tests: list[tuple[str, Callable[[], Any]]] = [
        ("player_lookup", lambda: s.player_lookup("Mike Trout")),
        ("statcast_search", lambda: s.statcast_search(DATE, DATE, "NYY")),
        ("statcast_batter", lambda: s.statcast_batter("Aaron Judge", DATE, DATE)),
        ("statcast_pitcher", lambda: s.statcast_pitcher("Gerrit Cole", DATE, DATE)),
        ("season_batting_stats", lambda: s.season_batting_stats(YEAR, player_name="Aaron Judge")),
        ("season_pitching_stats", lambda: s.season_pitching_stats(YEAR, player_name="Gerrit Cole")),
        ("team_season_batting_stats", lambda: s.team_season_batting_stats("PHI", YEAR)),
        ("team_season_pitching_stats", lambda: s.team_season_pitching_stats("PHI", YEAR)),
        ("statcast_batter_expected_stats", lambda: s.statcast_batter_expected_stats(YEAR, player_name="Aaron Judge")),
        ("statcast_pitcher_expected_stats", lambda: s.statcast_pitcher_expected_stats(YEAR, player_name="Gerrit Cole")),
        ("expected_stats_batch", lambda: s.expected_stats_batch(YEAR, batters="Aaron Judge", pitchers=None)),
        ("statcast_batter_pitch_arsenal", lambda: s.statcast_batter_pitch_arsenal(YEAR, player_name="Aaron Judge")),
        ("statcast_batter_exitvelo_barrels", lambda: s.statcast_batter_exitvelo_barrels(YEAR)),
        ("statcast_pitcher_exitvelo_barrels", lambda: s.statcast_pitcher_exitvelo_barrels(YEAR)),
        ("statcast_pitcher_pitch_arsenal", lambda: s.statcast_pitcher_pitch_arsenal(YEAR)),
        ("statcast_pitcher_arsenal_stats", lambda: s.statcast_pitcher_arsenal_stats(YEAR)),
        ("sprint_speed_leaderboard", lambda: s.sprint_speed_leaderboard(YEAR)),
        ("team_standings", lambda: s.team_standings(YEAR)),
        ("batter_percentile_ranks", lambda: s.batter_percentile_ranks(YEAR, player_name="Aaron Judge")),
        ("pitcher_percentile_ranks", lambda: s.pitcher_percentile_ranks(YEAR, player_name="Gerrit Cole")),
        ("outs_above_average", lambda: s.outs_above_average(YEAR, "SS")),
        ("outfield_directional_oaa", lambda: s.outfield_directional_oaa(YEAR)),
        ("batting_stats_date_range", lambda: s.batting_stats_date_range(RANGE_START, RANGE_END)),
        ("pitching_stats_date_range", lambda: s.pitching_stats_date_range(RANGE_START, RANGE_END)),
    ]

    from pybaseball import statcast as _sc

    try:
        _one = _sc(DATE, DATE, team="NYY", verbose=False, parallel=False)
        _gpk = int(_one["game_pk"].iloc[0]) if _one is not None and len(_one) else 776265
    except Exception:
        _gpk = 776265

    expanded: list[tuple[str, Callable[[], Any]]] = [
        ("statcast_tool_directory", lambda: s.EXPANDED_TOOL_FUNCS["statcast_tool_directory"](short=True)),
        ("team_schedule", lambda: s.EXPANDED_TOOL_FUNCS["team_schedule"](YEAR, "PHI")),
        (
            "player_stat_splits",
            lambda: s.EXPANDED_TOOL_FUNCS["player_stat_splits"](
                "Aaron Judge", YEAR, pitching_splits=False, include_player_info=False
            ),
        ),
        ("statcast_game_pitches", lambda: s.EXPANDED_TOOL_FUNCS["statcast_game_pitches"](_gpk)),
        (
            "batter_vs_pitcher_statcast",
            lambda: s.EXPANDED_TOOL_FUNCS["batter_vs_pitcher_statcast"](
                "Aaron Judge", "Gerrit Cole", DATE, DATE
            ),
        ),
        ("lahman_season_batting", lambda: s.EXPANDED_TOOL_FUNCS["lahman_season_batting"](2023, team_id="NYA")),
        ("lahman_season_pitching", lambda: s.EXPANDED_TOOL_FUNCS["lahman_season_pitching"](2023, team_id="NYA")),
        ("lahman_season_teams", lambda: s.EXPANDED_TOOL_FUNCS["lahman_season_teams"](2023)),
        ("top_prospects_mlb", lambda: s.EXPANDED_TOOL_FUNCS["top_prospects_mlb"](None, None)),
        ("amateur_draft_round", lambda: s.EXPANDED_TOOL_FUNCS["amateur_draft_round"](2023, 1, keep_stats=False)),
        ("war_daily_batting", lambda: s.EXPANDED_TOOL_FUNCS["war_daily_batting"](YEAR)),
        ("war_daily_pitching", lambda: s.EXPANDED_TOOL_FUNCS["war_daily_pitching"](YEAR)),
        ("season_fielding_stats", lambda: s.EXPANDED_TOOL_FUNCS["season_fielding_stats"](YEAR, player_name="Mookie Betts")),
        ("statcast_running_splits_detail", lambda: s.EXPANDED_TOOL_FUNCS["statcast_running_splits_detail"](YEAR)),
        ("statcast_outfield_catch_probability", lambda: s.EXPANDED_TOOL_FUNCS["statcast_outfield_catch_probability"](YEAR)),
        ("statcast_outfield_jump", lambda: s.EXPANDED_TOOL_FUNCS["statcast_outfield_jump"](YEAR)),
        ("statcast_catcher_framing", lambda: s.EXPANDED_TOOL_FUNCS["statcast_catcher_framing"](YEAR)),
        ("statcast_catcher_poptime", lambda: s.EXPANDED_TOOL_FUNCS["statcast_catcher_poptime"](YEAR)),
        ("statcast_pitcher_pitch_movement", lambda: s.EXPANDED_TOOL_FUNCS["statcast_pitcher_pitch_movement"](YEAR)),
        ("statcast_pitcher_active_spin_leaderboard", lambda: s.EXPANDED_TOOL_FUNCS["statcast_pitcher_active_spin_leaderboard"](YEAR)),
        ("league_team_batting_totals", lambda: s.EXPANDED_TOOL_FUNCS["league_team_batting_totals"](YEAR)),
        ("league_team_pitching_totals", lambda: s.EXPANDED_TOOL_FUNCS["league_team_pitching_totals"](YEAR)),
    ]

    tests = tests + expanded

    failures = 0
    warns = 0
    for name, fn in tests:
        try:
            out = fn()
            text = out if isinstance(out, str) else str(out)
            if not text or len(text.strip()) < 3:
                print(f"FAIL {name}: empty or tiny output")
                failures += 1
            elif text.startswith("Error ") or "Error fetching" in text[:200]:
                print(f"WARN {name}: upstream/data error (tool still ran): {text[:120]}...")
                warns += 1
            else:
                print(f"PASS {name} ({len(text)} chars)")
        except Exception as e:
            print(f"FAIL {name}: {e!r}")
            traceback.print_exc()
            failures += 1

    print(f"\nSummary: {len(tests)} tools, {failures} failures, {warns} upstream warnings.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
