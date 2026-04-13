"""
Additional MCP tools: schedules, splits, Lahman, draft, WAR, extra Statcast leaderboards.

Registered from ``server`` via ``register_expanded_tools`` after core helpers exist.
"""

from __future__ import annotations

import contextlib
import io
from typing import Any, Callable

import pandas as pd

from statcast_mcp.limits import (
    DEFAULT_BVP_SAMPLE_ROWS,
    DEFAULT_LAHMAN_TEAMS_ROWS,
    DEFAULT_LEADERBOARD_ROWS,
    DEFAULT_LEAGUE_TEAM_TOTALS_ROWS,
    DEFAULT_PITCH_LEVEL_ROWS,
    DEFAULT_PLAYER_SPLITS_PITCHING_GAME_ROWS,
    DEFAULT_PLAYER_SPLITS_PRIMARY_ROWS,
    DEFAULT_PLAYER_SPLITS_SINGLE_TABLE_ROWS,
    DEFAULT_SCHEDULE_ROWS,
    DEFAULT_TEAM_SEASON_ROWS,
    output_limit,
)

# ---------------------------------------------------------------------------
# Catalog (for statcast_tool_directory)
# ---------------------------------------------------------------------------

TOOL_CATALOG = """\
## Statcast MCP — full tool catalog

### Discovery
- **statcast_tool_directory** — This list in chat-friendly form.

### Player ID
- **player_lookup** — Chadwick / MLBAM / FanGraphs IDs.

### Pitch-level Statcast
- **statcast_search** — Pitches by date range + optional team.
- **statcast_batter** — All pitches to a batter in a date range.
- **statcast_pitcher** — All pitches from a pitcher in a date range.
- **statcast_game_pitches** — Every pitch in one game (`game_pk`).

### Matchups & splits
- **batter_vs_pitcher_statcast** — Aggregated Statcast results for one batter vs one pitcher over dates.
- **player_stat_splits** — Baseball Reference platoon / home-road / month splits (needs BRef player id).

### Season leaderboards (league)
- **season_batting_stats**, **season_pitching_stats** — FanGraphs.
- **season_fielding_stats** — FanGraphs fielding leaderboard.

### Team season (full roster)
- **team_season_batting_stats**, **team_season_pitching_stats** — FG + BRef fallback.

### Team schedule & results
- **team_schedule** — Game-by-game scores, W/L, attendance (BRef).

### League team totals (FanGraphs)
- **league_team_batting_totals**, **league_team_pitching_totals** — One row per team.

### Expected stats & barrels
- **statcast_batter_expected_stats**, **statcast_pitcher_expected_stats**, **expected_stats_batch**.

### Pitch arsenals & movement
- **statcast_batter_pitch_arsenal**, **statcast_pitcher_pitch_arsenal**, **statcast_pitcher_arsenal_stats**.
- **statcast_pitcher_pitch_movement**, **statcast_pitcher_active_spin**.

### Running & defense (Statcast)
- **sprint_speed_leaderboard**, **statcast_running_splits_detail**.
- **outs_above_average**, **outfield_directional_oaa**.
- **statcast_outfield_catch_probability**, **statcast_outfield_jump**.
- **statcast_catcher_framing**, **statcast_catcher_poptime**.

### Percentiles & exit velo
- **batter_percentile_ranks**, **pitcher_percentile_ranks**.
- **statcast_batter_exitvelo_barrels**, **statcast_pitcher_exitvelo_barrels**.

### Standings & prospects
- **team_standings**.
- **top_prospects_mlb** — MLB.com pipeline table.

### Draft
- **amateur_draft_round** — BRef amateur draft by year + round.

### Historical (Lahman / Baseball Data Bank)
- **lahman_season_batting**, **lahman_season_pitching**, **lahman_season_teams** — Filtered slices (downloads DB on first use).

### WAR components (Baseball Reference daily files)
- **war_daily_batting**, **war_daily_pitching** — Season-filtered WAR components.

### Baseball Reference date ranges
- **batting_stats_date_range**, **pitching_stats_date_range**.
"""


def _bbref_chadwick_id(player_name: str) -> str:
    from pybaseball import playerid_lookup

    name = player_name.strip()
    if "," in name:
        last, first = (p.strip() for p in name.split(",", 1))
    else:
        parts = name.split()
        if len(parts) < 2:
            raise ValueError(f"Provide first and last name. Got: {player_name!r}")
        first, last = parts[0], " ".join(parts[1:])
    results = playerid_lookup(last, first, fuzzy=True)
    if results.empty:
        raise ValueError(f"No player found for {player_name!r}.")
    if "mlb_played_last" in results.columns:
        results = results.copy()
        results["_mpl"] = pd.to_numeric(results["mlb_played_last"], errors="coerce")
        results = results.sort_values("_mpl", ascending=False, na_position="last").drop(
            columns=["_mpl"]
        )
    bid = results.iloc[0].get("key_bbref")
    if bid is None or (isinstance(bid, float) and pd.isna(bid)) or str(bid).strip() == "":
        raise ValueError(f"No Baseball Reference ID for {player_name!r}.")
    return str(bid).strip()


def register_expanded_tools(
    mcp: Any,
    _fmt: Callable[..., str],
    _filter_player_rows: Callable[..., pd.DataFrame],
    _resolve_player: Callable[..., tuple[int, str]],
    _normalize_team_abbr: Callable[[str], str],
    _trim_pitch_cols: Callable[[pd.DataFrame], pd.DataFrame],
) -> dict[str, Callable[..., str]]:
    """Register expanded tools on ``mcp`` and return name → callable for tests."""

    registered: dict[str, Callable[..., str]] = {}

    def _reg(fn: Callable[..., str]) -> Callable[..., str]:
        wrapped = mcp.tool()(fn)
        registered[fn.__name__] = wrapped
        return wrapped

    @_reg
    def statcast_tool_directory(short: bool = True) -> str:
        """Return a markdown catalog of every MCP tool and when to use it.

        Args:
            short: If True, return compact sections; if False, include the long catalog.
        """
        if short:
            return (
                "Use this map to pick tools. For **full** text, call with `short=False`.\n\n"
                + TOOL_CATALOG
            )
        return TOOL_CATALOG

    @_reg
    def team_schedule(
        season: int,
        team: str,
        max_output_rows: int | None = None,
    ) -> str:
        """Game-by-game schedule and results for one team (Baseball Reference).

        Includes date, opponent, home/away, score, W/L, streak, attendance, pitcher W/L/SV when available.

        Args:
            season: Season year (e.g. 2024).
            team: 3-letter code (e.g. PHI, NYY).
            max_output_rows: Max rows (default 250). Capped at 5000.
        """
        from pybaseball.team_results import schedule_and_record

        abbr = _normalize_team_abbr(team)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                data = schedule_and_record(season, abbr)
        except Exception as e:
            return f"Error fetching schedule: {e}"
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_SCHEDULE_ROWS),
        )

    @_reg
    def player_stat_splits(
        player_name: str,
        year: int | None = None,
        pitching_splits: bool = False,
        include_player_info: bool = False,
        max_output_rows: int | None = None,
    ) -> str:
        """Baseball Reference split statistics for one player (platoon, home/away, etc.).

        Args:
            player_name: Full name (e.g. 'Aaron Judge').
            year: Season year; omit for career splits.
            pitching_splits: If True, use pitching splits tables instead of batting.
            include_player_info: If True, append bio snippet (handedness, etc.) when available.
            max_output_rows: Max rows per returned table (defaults vary by section). Capped at 5000.

        Note: Response can be wide; many split tables may be concatenated vertically by BRef.
        """
        from pybaseball.split_stats import get_splits

        pid = _bbref_chadwick_id(player_name)
        try:
            out = get_splits(pid, year, player_info=include_player_info, pitching_splits=pitching_splits)
        except Exception as e:
            return f"Error fetching splits: {e}"
        parts: list[str] = []
        if isinstance(out, tuple):
            if len(out) >= 1 and isinstance(out[0], pd.DataFrame):
                parts.append(
                    _fmt(
                        out[0],
                        max_rows=output_limit(
                            max_output_rows, DEFAULT_PLAYER_SPLITS_PRIMARY_ROWS
                        ),
                    )
                )
            if include_player_info and len(out) >= 2 and isinstance(out[1], dict):
                parts.append("**Player info:** " + str(out[1]))
            if pitching_splits and len(out) >= 2 and isinstance(out[-1], pd.DataFrame):
                parts.append(
                    "**Game-level (pitching):**\n"
                    + _fmt(
                        out[-1],
                        max_rows=output_limit(
                            max_output_rows, DEFAULT_PLAYER_SPLITS_PITCHING_GAME_ROWS
                        ),
                    )
                )
        else:
            parts.append(
                _fmt(
                    out,
                    max_rows=output_limit(
                        max_output_rows, DEFAULT_PLAYER_SPLITS_SINGLE_TABLE_ROWS
                    ),
                )
            )
        text = "\n\n".join(p for p in parts if p)
        return text if text.strip() else "No split data returned."

    @_reg
    def statcast_game_pitches(
        game_pk: int,
        max_output_rows: int | None = None,
    ) -> str:
        """All Statcast pitch rows for a single MLB game.

        Args:
            game_pk: MLB Advanced Media game PK (6+ digit integer; appears in Savant URLs).
            max_output_rows: Max rows (default 100). Capped at 5000.

        Find ``game_pk`` from a pitch-level query or box score.
        """
        from pybaseball.statcast import statcast_single_game

        try:
            data = statcast_single_game(int(game_pk))
        except Exception as e:
            return f"Error fetching game: {e}"
        if data is None or data.empty:
            return f"No Statcast data for game_pk={game_pk}."
        data = _trim_pitch_cols(data)
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_PITCH_LEVEL_ROWS),
        )

    @_reg
    def batter_vs_pitcher_statcast(
        batter_name: str,
        pitcher_name: str,
        start_date: str,
        end_date: str,
        max_output_rows: int | None = None,
    ) -> str:
        """Summarize Statcast outcomes for one batter against one pitcher (date range).

        Pulls the batter's pitch-level feed and filters to the given pitcher. Returns PA count,
        hits, HR, strikeouts, walks, and average exit velocity where available.

        Args:
            batter_name: Hitter's name.
            pitcher_name: Pitcher's name.
            start_date, end_date: YYYY-MM-DD (keep ranges short; Statcast is heavy).
            max_output_rows: Max sample pitch rows shown (default 80). Capped at 5000.
        """
        from pybaseball import statcast_batter as _sb

        try:
            bid, _ = _resolve_player(batter_name)
            pid, _ = _resolve_player(pitcher_name)
        except ValueError as e:
            return str(e)
        try:
            raw = _sb(start_date, end_date, player_id=bid)
        except Exception as e:
            return f"Error fetching Statcast: {e}"
        if raw is None or raw.empty:
            return (
                f"No Statcast pitches for {batter_name} in {start_date}–{end_date}. "
                "Try a shorter range or verify names."
            )
        pcol = "pitcher" if "pitcher" in raw.columns else None
        if not pcol:
            return "Unexpected Statcast schema (no pitcher column)."
        m = raw[pcol].astype(float).astype(int) == int(pid)
        df = raw.loc[m]
        if df.empty:
            return (
                f"No pitches where {pitcher_name} faced {batter_name} in this span "
                f"({len(raw)} pitches to batter vs other arms)."
            )
        events = df["events"].fillna("") if "events" in df.columns else pd.Series([], dtype=str)
        pa_like = events.isin(
            [
                "field_out",
                "single",
                "double",
                "triple",
                "home_run",
                "strikeout",
                "strikeout_double_play",
                "walk",
                "intent_walk",
                "hit_by_pitch",
                "sac_fly",
                "sac_bunt",
                "field_error",
                "fielders_choice",
                "force_out",
                "grounded_into_double_play",
            ]
        )
        pa_est = df.loc[pa_like | events.str.contains("strikeout|walk|home_run|single", case=False, na=False)]
        ev = None
        if "launch_speed" in df.columns:
            ev = pd.to_numeric(df["launch_speed"], errors="coerce").dropna()
        lines = [
            f"**Batter:** {batter_name} (MLBAM {bid})",
            f"**Pitcher:** {pitcher_name} (MLBAM {pid})",
            f"**Span:** {start_date} to {end_date}",
            f"**Pitches (filtered):** {len(df)}",
            "",
        ]
        if not events.empty:
            vc = events[events != ""].value_counts().head(15)
            lines.append("**Event counts (pitch rows):**\n" + vc.to_string())
        if ev is not None and len(ev):
            lines.append(f"\n**Avg exit velocity (batted balls with velo):** {ev.mean():.1f} mph (n={len(ev)})")
        n_sample = output_limit(max_output_rows, DEFAULT_BVP_SAMPLE_ROWS)
        summ = df.head(n_sample)
        lines.append("\n**Sample pitch rows:**\n")
        return "\n".join(lines) + _fmt(summ, max_rows=n_sample)

    @_reg
    def lahman_season_batting(
        season: int,
        team_id: str | None = None,
        max_output_rows: int | None = None,
    ) -> str:
        """Lahman / Baseball Data Bank batting rows for one season (1871–present file).

        First call may download the Lahman zip to pybaseball's cache.

        Args:
            season: ``yearID`` to filter.
            team_id: Optional 3-letter ``teamID`` (e.g. ``PHI``).
            max_output_rows: Cap output rows (default 200). Capped at 5000.
        """
        from pybaseball import batting as _bat
        from pybaseball import download_lahman

        try:
            data = _bat()
        except Exception:
            try:
                download_lahman()
                data = _bat()
            except Exception as e:
                return (
                    f"Error loading Lahman batting (first run downloads ~100MB): {e}. "
                    "Try again after `import pybaseball; pybaseball.lahman.download_lahman()` in Python."
                )
        data = data[data["yearID"] == int(season)]
        if team_id:
            tid = team_id.strip().upper()
            if "teamID" in data.columns:
                data = data[data["teamID"] == tid]
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_TEAM_SEASON_ROWS),
        )

    @_reg
    def lahman_season_pitching(
        season: int,
        team_id: str | None = None,
        max_output_rows: int | None = None,
    ) -> str:
        """Lahman pitching rows for one season; optional ``teamID`` filter."""
        from pybaseball import download_lahman
        from pybaseball import pitching as _pit

        try:
            data = _pit()
        except Exception:
            try:
                download_lahman()
                data = _pit()
            except Exception as e:
                return f"Error loading Lahman pitching: {e}"
        data = data[data["yearID"] == int(season)]
        if team_id:
            tid = team_id.strip().upper()
            if "teamID" in data.columns:
                data = data[data["teamID"] == tid]
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_TEAM_SEASON_ROWS),
        )

    @_reg
    def lahman_season_teams(
        season: int,
        max_output_rows: int | None = None,
    ) -> str:
        """Lahman **Teams** table rows for one season (standings-level team stats).

        Args:
            season: ``yearID`` to filter.
            max_output_rows: Max rows (default 60). Capped at 5000.
        """
        from pybaseball import download_lahman
        from pybaseball import teams_core

        try:
            data = teams_core()
        except Exception:
            try:
                download_lahman()
                data = teams_core()
            except Exception as e:
                return f"Error loading Lahman teams: {e}"
        data = data[data["yearID"] == int(season)]
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LAHMAN_TEAMS_ROWS),
        )

    @_reg
    def top_prospects_mlb(
        team_name: str | None = None,
        player_type: str | None = None,
        max_output_rows: int | None = None,
    ) -> str:
        """MLB Pipeline top prospects table (MLB.com / pybaseball).

        Args:
            team_name: e.g. ``Phillies`` or ``Yankees`` (no spaces in slug — use full franchise name).
            player_type: ``batters``, ``pitchers``, or None for both (concatenated).
            max_output_rows: Max rows (default 100). Capped at 5000.
        """
        from pybaseball import top_prospects

        try:
            data = top_prospects(teamName=team_name, playerType=player_type)
        except Exception as e:
            return f"Error fetching prospects: {e}"
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_PITCH_LEVEL_ROWS),
        )

    @_reg
    def amateur_draft_round(
        year: int,
        draft_round: int,
        keep_stats: bool = True,
        max_output_rows: int | None = None,
    ) -> str:
        """Amateur draft results for a given year and round (Baseball Reference).

        Args:
            max_output_rows: Max rows (default 100). Capped at 5000.
        """
        from pybaseball import amateur_draft

        try:
            data = amateur_draft(year, draft_round, keep_stats=keep_stats)
        except Exception as e:
            return f"Error fetching draft: {e}"
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_PITCH_LEVEL_ROWS),
        )

    @_reg
    def war_daily_batting(
        season: int | None = None,
        max_output_rows: int | None = None,
    ) -> str:
        """Baseball Reference WAR components for batters (``war_daily_bat``); optional season filter.

        Args:
            season: Optional year filter.
            max_output_rows: Max rows (default 200). Capped at 5000.
        """
        from pybaseball import bwar_bat

        try:
            data = bwar_bat(return_all=False)
        except Exception as e:
            return f"Error fetching batting WAR file: {e}"
        if season is not None and "year_ID" in data.columns:
            data = data[data["year_ID"] == int(season)]
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_TEAM_SEASON_ROWS),
        )

    @_reg
    def war_daily_pitching(
        season: int | None = None,
        max_output_rows: int | None = None,
    ) -> str:
        """Baseball Reference WAR components for pitchers; optional season filter.

        Args:
            season: Optional year filter.
            max_output_rows: Max rows (default 200). Capped at 5000.
        """
        from pybaseball import bwar_pitch

        try:
            data = bwar_pitch(return_all=False)
        except Exception as e:
            return f"Error fetching pitching WAR file: {e}"
        if season is not None and "year_ID" in data.columns:
            data = data[data["year_ID"] == int(season)]
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_TEAM_SEASON_ROWS),
        )

    @_reg
    def season_fielding_stats(
        start_season: int,
        end_season: int | None = None,
        player_name: str | None = None,
        max_output_rows: int | None = None,
    ) -> str:
        """FanGraphs season fielding leaderboard (DEF, UZR where available).

        Args:
            max_output_rows: Max rows (default 50). Capped at 5000.
        """
        from pybaseball import fielding_stats

        if end_season is None:
            end_season = start_season
        try:
            data = fielding_stats(start_season, end_season)
        except Exception as e:
            return f"Error fetching fielding stats: {e}"
        if player_name:
            try:
                data = _filter_player_rows(data, player_name)
            except ValueError as e:
                return str(e)
            if data.empty:
                return f"No FanGraphs fielding row for {player_name} in {start_season}–{end_season}."
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
        )

    @_reg
    def statcast_running_splits_detail(
        year: int,
        min_opportunities: int = 5,
        raw_splits: bool = True,
        max_output_rows: int | None = None,
    ) -> str:
        """90-foot sprint split times (Statcast) — raw or percentile by 5-foot windows.

        Args:
            max_output_rows: Max rows (default 50). Capped at 5000.
        """
        from pybaseball import statcast_running_splits

        try:
            data = statcast_running_splits(year, min_opp=min_opportunities, raw_splits=raw_splits)
        except Exception as e:
            return f"Error fetching running splits: {e}"
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
        )

    @_reg
    def statcast_outfield_catch_probability(
        year: int,
        min_opportunities: str | int = "q",
        max_output_rows: int | None = None,
    ) -> str:
        """Outfield jump/catch star ratings / probability buckets (Statcast).

        Args:
            max_output_rows: Max rows (default 50). Capped at 5000.
        """
        from pybaseball import statcast_outfield_catch_prob

        try:
            data = statcast_outfield_catch_prob(year, min_opp=min_opportunities)
        except Exception as e:
            return f"Error fetching catch probability: {e}"
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
        )

    @_reg
    def statcast_outfield_jump(
        year: int,
        min_attempts: str | int = "q",
        max_output_rows: int | None = None,
    ) -> str:
        """Outfield jump metric leaderboard (Statcast).

        Args:
            max_output_rows: Max rows (default 50). Capped at 5000.
        """
        from pybaseball import statcast_outfielder_jump

        try:
            data = statcast_outfielder_jump(year, min_att=min_attempts)
        except Exception as e:
            return f"Error fetching outfield jump: {e}"
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
        )

    @_reg
    def statcast_catcher_framing(
        year: int,
        min_called_pitches: str | int = "q",
        max_output_rows: int | None = None,
    ) -> str:
        """Catcher framing runs / strike rate in shadow zones (Statcast).

        Args:
            max_output_rows: Max rows (default 50). Capped at 5000.
        """
        from pybaseball import statcast_catcher_framing

        try:
            data = statcast_catcher_framing(year, min_called_p=min_called_pitches)
        except Exception as e:
            return f"Error fetching framing: {e}"
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
        )

    @_reg
    def statcast_catcher_poptime(
        year: int,
        min_second_base_attempts: int = 5,
        min_third_base_attempts: int = 0,
        max_output_rows: int | None = None,
    ) -> str:
        """Catcher pop times to 2B/3B (Statcast).

        Args:
            max_output_rows: Max rows (default 50). Capped at 5000.
        """
        from pybaseball import statcast_catcher_poptime

        try:
            data = statcast_catcher_poptime(
                year, min_2b_att=min_second_base_attempts, min_3b_att=min_third_base_attempts
            )
        except Exception as e:
            return f"Error fetching pop time: {e}"
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
        )

    @_reg
    def statcast_pitcher_pitch_movement(
        year: int,
        pitch_type: str = "FF",
        min_pitches: str | int = "q",
        max_output_rows: int | None = None,
    ) -> str:
        """Pitch movement leaderboard (break/induced) for a pitch type (Statcast).

        Args:
            max_output_rows: Max rows (default 50). Capped at 5000.
        """
        from pybaseball.statcast_pitcher import statcast_pitcher_pitch_movement

        try:
            data = statcast_pitcher_pitch_movement(year, minP=min_pitches, pitch_type=pitch_type)
        except Exception as e:
            return f"Error fetching pitch movement: {e}"
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
        )

    @_reg
    def statcast_pitcher_active_spin_leaderboard(
        year: int,
        min_pitches: int = 250,
        max_output_rows: int | None = None,
    ) -> str:
        """Active spin rate leaderboard (Statcast; spin-based or observed fallback in pybaseball).

        Args:
            max_output_rows: Max rows (default 50). Capped at 5000.
        """
        from pybaseball.statcast_pitcher import statcast_pitcher_active_spin

        try:
            data = statcast_pitcher_active_spin(year, minP=min_pitches)
        except Exception as e:
            return f"Error fetching active spin: {e}"
        if data is None or data.empty:
            return "No active spin data for this year (try a recent season)."
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
        )

    @_reg
    def league_team_batting_totals(
        season: int,
        max_output_rows: int | None = None,
    ) -> str:
        """FanGraphs **team** batting lines — one row per club (league-wide).

        May fail if FanGraphs blocks automated requests; try again later or use team_season_batting_stats.

        Args:
            max_output_rows: Max rows (default 40). Capped at 5000.
        """
        from pybaseball import fg_team_batting_data

        try:
            data = fg_team_batting_data(season, season, team="0,ts")
        except Exception as e:
            return f"Error fetching team batting totals: {e}"
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LEAGUE_TEAM_TOTALS_ROWS),
        )

    @_reg
    def league_team_pitching_totals(
        season: int,
        max_output_rows: int | None = None,
    ) -> str:
        """FanGraphs **team** pitching lines — one row per club.

        Args:
            max_output_rows: Max rows (default 40). Capped at 5000.
        """
        from pybaseball import fg_team_pitching_data

        try:
            data = fg_team_pitching_data(season, season, team="0,ts")
        except Exception as e:
            return f"Error fetching team pitching totals: {e}"
        return _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LEAGUE_TEAM_TOTALS_ROWS),
        )

    return registered
