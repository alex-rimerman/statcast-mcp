"""
Statcast MCP Server

An MCP server that provides natural-language access to MLB data: Statcast
(pitch/game/matchup/defense/movement), FanGraphs, Baseball Reference, Lahman,
schedules, splits, draft/prospects, and WAR files — **46** tools via pybaseball.
"""

from __future__ import annotations

import pandas as pd
from mcp.server.fastmcp import FastMCP

from statcast_mcp.limits import (
    DEFAULT_LEADERBOARD_ROWS,
    DEFAULT_PITCH_LEVEL_ROWS,
    DEFAULT_PLAYER_LOOKUP_ROWS,
    DEFAULT_TEAM_SEASON_ROWS,
    MAX_OUTPUT_ROWS_CAP,
    output_limit,
)

mcp = FastMCP(
    "Statcast",
    instructions=(
        "Query MLB Statcast data using natural language. "
        "For expected stats on a whole lineup or rotation, use expected_stats_batch "
        "with comma-separated batters and/or pitchers — not one call per player. "
        "Other leaderboards accept optional player_name for a single player. "
        "Pitch-level tools use statcast_batter/statcast_pitcher with names and dates. "
        "There is no automatic team roster for expected stats: resolve names first. "
        "For full **team** actual season stats (lineup + staff), use "
        "team_season_batting_stats and team_season_pitching_stats with a 3-letter code "
        "(e.g. PHI). "
        "Expanded tools (see statcast_tool_directory): team schedule, BRef splits, Lahman history, "
        "draft, WAR files, extra Statcast defense/movement, league team totals, game_pk pitch logs, "
        "and batter-vs-pitcher Statcast summaries. "
        "Data from Baseball Savant, FanGraphs, Baseball Reference, Lahman, and MLB.com (2008+)."
    ),
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PITCH_DISPLAY_COLS = [
    "game_date",
    "player_name",
    "batter",
    "pitcher",
    "pitch_type",
    "pitch_name",
    "release_speed",
    "release_spin_rate",
    "events",
    "description",
    "zone",
    "launch_speed",
    "launch_angle",
    "hit_distance_sc",
    "estimated_ba_using_speedangle",
    "estimated_woba_using_speedangle",
    "bb_type",
    "stand",
    "p_throws",
    "home_team",
    "away_team",
    "inning",
    "balls",
    "strikes",
]


def _sort_playerid_lookup_by_recency(results: pd.DataFrame) -> pd.DataFrame:
    """Sort ``playerid_lookup`` rows by ``mlb_played_last`` (handles str/float mix)."""
    if results.empty or "mlb_played_last" not in results.columns:
        return results
    out = results.copy()
    out["_mpl"] = pd.to_numeric(out["mlb_played_last"], errors="coerce")
    return out.sort_values("_mpl", ascending=False, na_position="last").drop(
        columns=["_mpl"]
    )


def _resolve_player(player_name: str) -> tuple[int, str]:
    """Return (mlbam_id, 'First Last') for a player name string.

    Accepts formats: 'First Last', 'Last, First'.
    Picks the most-recent player when multiple matches are returned.
    """
    from pybaseball import playerid_lookup

    name = player_name.strip()
    if "," in name:
        last, first = (p.strip() for p in name.split(",", 1))
    else:
        parts = name.split()
        if len(parts) < 2:
            raise ValueError(
                f"Please provide both first and last name. Got: '{player_name}'"
            )
        first, last = parts[0], " ".join(parts[1:])

    results = playerid_lookup(last, first, fuzzy=True)

    if results.empty:
        raise ValueError(
            f"No player found matching '{player_name}'. "
            "Check the spelling and try again."
        )

    results = _sort_playerid_lookup_by_recency(results)

    row = results.iloc[0]
    return int(row["key_mlbam"]), f"{row['name_first']} {row['name_last']}"


def _trim_pitch_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the most useful pitch-level columns to manage output size."""
    cols = [c for c in _PITCH_DISPLAY_COLS if c in df.columns]
    return df[cols] if cols else df


def _fmt(df: pd.DataFrame, max_rows: int = 50) -> str:
    """Render a DataFrame as a markdown table with row-count metadata."""
    if df is None or (hasattr(df, "empty") and df.empty):
        return "No data found for the given criteria."

    total = len(df)
    truncated = total > max_rows
    display = df.head(max_rows) if truncated else df

    header = (
        f"Showing {max_rows} of {total} total rows.\n\n"
        if truncated
        else f"{total} rows returned.\n\n"
    )
    return header + display.to_markdown(index=False)


def _filter_player_rows(df: pd.DataFrame, player_name: str) -> pd.DataFrame:
    """Keep rows for one player across Statcast / FanGraphs / BRef column layouts.

    Uses MLBAM id when available, FanGraphs ``IDfg`` when present, and
    name matching on ``last_name, first_name`` or ``Name`` as fallback.
    Multiple rows are returned when the table is split by pitch type (arsenal).
    """
    from pybaseball import playerid_lookup

    name = player_name.strip()
    if "," in name:
        last, first = (p.strip() for p in name.split(",", 1))
    else:
        parts = name.split()
        if len(parts) < 2:
            raise ValueError(
                f"Please provide both first and last name. Got: '{player_name}'"
            )
        first, last = parts[0], " ".join(parts[1:])

    results = playerid_lookup(last, first, fuzzy=True)
    if results.empty:
        raise ValueError(
            f"No player found matching '{player_name}'. "
            "Check the spelling and try again."
        )
    results = _sort_playerid_lookup_by_recency(results)
    row = results.iloc[0]
    mlbam = int(row["key_mlbam"])
    fg_raw = row.get("key_fangraphs")
    fg_id = int(fg_raw) if fg_raw is not None and pd.notna(fg_raw) else None
    last_s = str(row["name_last"])
    first_s = str(row["name_first"])

    if df is None or df.empty:
        return df

    if "player_id" in df.columns:
        m = df["player_id"].astype(float).astype(int) == mlbam
        if m.any():
            return df[m]

    if "pitcher" in df.columns:
        m = df["pitcher"].astype(float).astype(int) == mlbam
        if m.any():
            return df[m]

    if "mlbID" in df.columns:
        m = df["mlbID"].astype(float).astype(int) == mlbam
        if m.any():
            return df[m]

    if "IDfg" in df.columns and fg_id is not None:
        m = df["IDfg"].astype(float).astype(int) == fg_id
        if m.any():
            return df[m]

    if "last_name, first_name" in df.columns:
        col = df["last_name, first_name"].str.lower()
        target = f"{last_s}, {first_s}".lower()
        m = col == target
        if m.any():
            return df[m]
        m = col.str.contains(last_s, case=False, na=False) & col.str.contains(
            first_s, case=False, na=False
        )
        if m.any():
            return df[m]

    if "Name" in df.columns:
        m = df["Name"].str.contains(last_s, case=False, na=False) & df[
            "Name"
        ].str.contains(first_s, case=False, na=False)
        if m.any():
            return df[m]

    if "Player" in df.columns:
        col = df["Player"].astype(str).str.replace("*", "", regex=False)
        m = col.str.contains(last_s, case=False, na=False) & col.str.contains(
            first_s, case=False, na=False
        )
        if m.any():
            return df[m]

    return df.iloc[0:0]


def _parse_player_name_list(player_names: str) -> list[str]:
    """Split comma/semicolon/newline-separated names into a clean list."""
    if not player_names or not str(player_names).strip():
        return []
    text = str(player_names).replace(";", ",").replace("\n", ",")
    return [p.strip() for p in text.split(",") if p.strip()]


def _batch_filter_players(
    df: pd.DataFrame,
    names: list[str],
) -> tuple[pd.DataFrame, list[str]]:
    """Return concatenated rows for each name; collect per-name errors."""
    chunks: list[pd.DataFrame] = []
    errors: list[str] = []
    for raw in names:
        try:
            part = _filter_player_rows(df, raw)
        except ValueError as e:
            errors.append(f"{raw}: {e}")
            continue
        if part.empty:
            errors.append(f"{raw}: no qualifying row in this leaderboard")
        else:
            chunks.append(part)
    if not chunks:
        return pd.DataFrame(), errors
    return pd.concat(chunks, ignore_index=True), errors


def _resolve_stat_column(df: pd.DataFrame, sort_by: str) -> str | None:
    """Match a user stat name (e.g. ``SLG``, ``wRC+``) to a column in ``df``."""
    if df.empty or not sort_by or not str(sort_by).strip():
        return None
    s = str(sort_by).strip()
    if s in df.columns:
        return s
    lower_map = {str(c).lower(): c for c in df.columns}
    if s.lower() in lower_map:
        return lower_map[s.lower()]
    return None


def _sort_dataframe_by_column(
    df: pd.DataFrame,
    sort_by: str,
    *,
    descending: bool,
) -> tuple[pd.DataFrame, str | None]:
    """Sort by numeric interpretation of ``sort_by`` column. Returns (df, warning or None)."""
    col = _resolve_stat_column(df, sort_by)
    if col is None:
        return df, f"Unknown sort column {sort_by!r}; available columns include SLG, HR, OPS, wRC+, PA, etc."
    out = df.copy()
    key = pd.to_numeric(out[col], errors="coerce")
    out = out.assign(_sort_key=key).sort_values(
        "_sort_key", ascending=not descending, na_position="last"
    )
    return out.drop(columns=["_sort_key"]), None


def _normalize_team_abbr(team: str) -> str:
    """Validate and normalize a 3-letter MLB / Baseball-Reference team code."""
    t = team.strip().upper()
    if len(t) != 3:
        raise ValueError(
            f"Team must be a 3-letter abbreviation (e.g. PHI, NYY, LAD). Got: {team!r}"
        )
    return t


def _bref_pick_batting_table(tables: list) -> pd.DataFrame:
    """Select the full-season batting table from BRef (not postseason-only).

    BRef exposes multiple ``Player``/``PA`` tables; we pick the one whose largest
    ``PA`` is highest (regular season has everyday players at 600+ PA).
    """
    best: pd.DataFrame | None = None
    best_max_pa = -1.0
    for t in tables:
        if not isinstance(t, pd.DataFrame):
            continue
        cols = {str(c).strip() for c in t.columns}
        if "Player" not in cols or "PA" not in cols:
            continue
        pa = pd.to_numeric(t["PA"], errors="coerce")
        mx = float(pa.max()) if pa.notna().any() else -1.0
        if mx > best_max_pa:
            best_max_pa = mx
            best = t
    if best is None:
        raise ValueError("No batting table found on Baseball Reference team page.")
    return best.copy()


def _bref_pick_pitching_table(tables: list) -> pd.DataFrame:
    """Select the full-season pitching table (not postseason / split tables).

    Pick the table with the largest maximum ``GS`` (starters log 25–35 starts).
    """
    best: pd.DataFrame | None = None
    best_max_gs = -1.0
    for t in tables:
        if not isinstance(t, pd.DataFrame):
            continue
        cols = {str(c).strip() for c in t.columns}
        if not {"Player", "ERA", "IP", "GS"} <= cols:
            continue
        gs = pd.to_numeric(t["GS"], errors="coerce")
        mx = float(gs.max()) if gs.notna().any() else -1.0
        if mx > best_max_gs:
            best_max_gs = mx
            best = t
    if best is None:
        raise ValueError("No pitching table found on Baseball Reference team page.")
    return best.copy()


def _clean_bref_totals_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop team-total and junk rows from a BRef ``Player`` column table."""
    if df.empty or "Player" not in df.columns:
        return df
    out = df.copy()
    out["Player"] = out["Player"].astype(str).str.replace("*", "", regex=False).str.strip()
    bad = {"team totals", "player", ""}
    mask = ~out["Player"].str.lower().isin(bad) & out["Player"].notna()
    return out.loc[mask].reset_index(drop=True)


def _team_batting_from_bref(team: str, season: int) -> pd.DataFrame:
    """Scrape team batting from Baseball Reference (full roster, actual stats)."""
    url = f"https://www.baseball-reference.com/teams/{team}/{season}.shtml"
    tables = pd.read_html(url)
    bat = _bref_pick_batting_table(tables)
    return _clean_bref_totals_rows(bat)


def _team_pitching_from_bref(team: str, season: int) -> pd.DataFrame:
    """Scrape team pitching from Baseball Reference (full roster, actual stats)."""
    url = f"https://www.baseball-reference.com/teams/{team}/{season}.shtml"
    tables = pd.read_html(url)
    pit = _bref_pick_pitching_table(tables)
    return _clean_bref_totals_rows(pit)


# ---------------------------------------------------------------------------
# Tools — Player Lookup
# ---------------------------------------------------------------------------


@mcp.tool()
def player_lookup(player_name: str, max_output_rows: int | None = None) -> str:
    """Look up a baseball player to find their MLBAM ID, years active, and database IDs.

    Accepts names like 'Mike Trout', 'Trout, Mike', or 'Shohei Ohtani'.
    Useful for verifying a player's identity or finding their MLBAM / FanGraphs /
    Baseball-Reference IDs before running other queries.

    Args:
        max_output_rows: Max rows in the result table (default 10). Capped at 5000.
    """
    from pybaseball import playerid_lookup

    name = player_name.strip()
    if "," in name:
        last, first = (p.strip() for p in name.split(",", 1))
    else:
        parts = name.split()
        if len(parts) == 1:
            last, first = parts[0], None
        else:
            first, last = parts[0], " ".join(parts[1:])

    try:
        results = playerid_lookup(last, first, fuzzy=True)
    except Exception as e:
        return f"Error looking up player: {e}"

    if results.empty:
        return (
            f"No player found matching '{player_name}'. "
            "Check the spelling and try again."
        )

    return _fmt(
        results,
        max_rows=output_limit(max_output_rows, DEFAULT_PLAYER_LOOKUP_ROWS),
    )


# ---------------------------------------------------------------------------
# Tools — Pitch-Level Statcast Data
# ---------------------------------------------------------------------------


@mcp.tool()
def statcast_search(
    start_date: str,
    end_date: str | None = None,
    team: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Search for pitch-level Statcast data within a date range.

    Returns pitch-by-pitch data including pitch type, velocity, spin rate,
    exit velocity, launch angle, expected stats, and more.

    Args:
        start_date: Start date in YYYY-MM-DD format (e.g. '2024-07-04').
        end_date: End date in YYYY-MM-DD format. Defaults to start_date for
                  single-day queries.
        team: Optional three-letter team abbreviation to filter results
              (e.g. 'NYY', 'LAD', 'BOS').
        max_output_rows: Max pitch rows in the markdown table (default 100). Capped at 5000.

    Data is available from the 2008 season onward.
    Tip: keep date ranges to 1-5 days for faster results.
    """
    from pybaseball import statcast

    if end_date is None:
        end_date = start_date

    try:
        data = statcast(start_dt=start_date, end_dt=end_date, team=team)
    except Exception as e:
        return f"Error fetching Statcast data: {e}"

    data = _trim_pitch_cols(data)
    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_PITCH_LEVEL_ROWS),
    )


@mcp.tool()
def statcast_batter(
    player_name: str,
    start_date: str,
    end_date: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Get pitch-level Statcast data for a specific batter in a date range.

    Returns every pitch the batter saw — pitch type, velocity, exit velocity,
    launch angle, expected batting average, and much more.

    Args:
        player_name: Full name of the batter (e.g. 'Aaron Judge').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format (defaults to start_date).
        max_output_rows: Max pitch rows in the table (default 100). Capped at 5000.

    Great for analyzing a hitter's performance over a specific period.
    """
    from pybaseball import statcast_batter as _sb

    try:
        mlbam_id, name = _resolve_player(player_name)
    except ValueError as e:
        return str(e)

    if end_date is None:
        end_date = start_date

    try:
        data = _sb(start_dt=start_date, end_dt=end_date, player_id=mlbam_id)
    except Exception as e:
        return f"Error fetching data for {player_name}: {e}"

    data = _trim_pitch_cols(data)
    return (
        f"Statcast batting data for {name} (MLBAM ID: {mlbam_id}):\n\n"
        + _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_PITCH_LEVEL_ROWS),
        )
    )


@mcp.tool()
def statcast_pitcher(
    player_name: str,
    start_date: str,
    end_date: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Get pitch-level Statcast data for a specific pitcher in a date range.

    Returns every pitch thrown — pitch type, velocity, spin rate, movement,
    exit velocity allowed, and more.

    Args:
        player_name: Full name of the pitcher (e.g. 'Gerrit Cole').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format (defaults to start_date).
        max_output_rows: Max pitch rows in the table (default 100). Capped at 5000.

    Great for analyzing a pitcher's stuff, outings, or trends over time.
    """
    from pybaseball import statcast_pitcher as _sp

    try:
        mlbam_id, name = _resolve_player(player_name)
    except ValueError as e:
        return str(e)

    if end_date is None:
        end_date = start_date

    try:
        data = _sp(start_dt=start_date, end_dt=end_date, player_id=mlbam_id)
    except Exception as e:
        return f"Error fetching data for {player_name}: {e}"

    data = _trim_pitch_cols(data)
    return (
        f"Statcast pitching data for {name} (MLBAM ID: {mlbam_id}):\n\n"
        + _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_PITCH_LEVEL_ROWS),
        )
    )


# ---------------------------------------------------------------------------
# Tools — Season-Level Stats (FanGraphs)
# ---------------------------------------------------------------------------


@mcp.tool()
def season_batting_stats(
    start_season: int,
    end_season: int | None = None,
    min_plate_appearances: int | None = None,
    player_name: str | None = None,
    max_output_rows: int | None = None,
    sort_by: str | None = None,
    sort_descending: bool = True,
) -> str:
    """Get season-level batting statistics from FanGraphs.

    Returns comprehensive stats: AVG, OBP, SLG, wOBA, wRC+, HR, SB, WAR,
    and many more for every qualifying batter.

    Args:
        start_season: First season to include (e.g. 2024).
        end_season: Last season to include. Omit for a single year.
        min_plate_appearances: Minimum plate appearances to qualify.
            Leave blank to use the FanGraphs default qualified threshold.
        player_name: Optional. Filter to one player (e.g. 'Aaron Judge').
        max_output_rows: Max rows in the table (default 50). Capped at 5000.
        sort_by: Optional stat column to sort by before truncating (e.g. ``SLG``, ``HR``, ``wRC+``, ``OPS``).
            Use this for leaderboards (e.g. top 200 by slugging).
        sort_descending: If True (default), highest values first when ``sort_by`` is set.

    If FanGraphs is unavailable (e.g. HTTP 403), a **single-season** query falls back to
    Baseball Reference via pybaseball (same sort/min-PA behavior).

    Great for finding league leaders, comparing players, or reviewing a full season.
    """
    from pybaseball import batting_stats

    if end_season is None:
        end_season = start_season

    prefix = ""
    try:
        data = batting_stats(start_season, end_season, qual=min_plate_appearances)
    except Exception as e:
        if start_season != end_season:
            return f"Error fetching batting stats: {e}"
        try:
            from pybaseball import batting_stats_bref

            data = batting_stats_bref(start_season)
            prefix = (
                "*Data source: Baseball Reference (FanGraphs was unavailable).*\n\n"
            )
            if min_plate_appearances is not None:
                pa = pd.to_numeric(data["PA"], errors="coerce")
                data = data.loc[pa >= int(min_plate_appearances)].reset_index(drop=True)
        except Exception as e2:
            return f"Error fetching batting stats: {e}\nBaseball Reference fallback failed: {e2}"

    sort_warn: str | None = None
    if sort_by:
        data, sort_warn = _sort_dataframe_by_column(
            data, sort_by, descending=sort_descending
        )
        if sort_warn:
            prefix += f"**Note:** {sort_warn}\n\n"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No batting stats row for {player_name} in {start_season}-{end_season} "
                "with the given PA threshold."
            )

    return prefix + _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


@mcp.tool()
def season_pitching_stats(
    start_season: int,
    end_season: int | None = None,
    min_innings: int | None = None,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Get season-level pitching statistics from FanGraphs.

    Returns comprehensive stats: ERA, FIP, WHIP, K/9, BB/9, WAR,
    and many more for every qualifying pitcher.

    Args:
        start_season: First season to include (e.g. 2024).
        end_season: Last season to include. Omit for a single year.
        min_innings: Minimum innings pitched to qualify.
            Leave blank to use the FanGraphs default qualified threshold.
        player_name: Optional. Filter to one pitcher (e.g. 'Gerrit Cole').
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Great for finding pitching leaders, comparing pitchers, or analyzing a season.
    """
    from pybaseball import pitching_stats

    if end_season is None:
        end_season = start_season

    try:
        data = pitching_stats(start_season, end_season, qual=min_innings)
    except Exception as e:
        return f"Error fetching pitching stats: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No FanGraphs pitching row for {player_name} in {start_season}-{end_season} "
                "with the given IP threshold."
            )

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


@mcp.tool()
def team_season_batting_stats(
    team: str,
    season: int,
    min_plate_appearances: int = 1,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Full-season **actual** batting stats for one MLB team (entire roster).

    Uses **FanGraphs** when available; if that fails or returns no rows, falls back to
    scraping **Baseball Reference**'s team page (same numbers as the site: PA, HR,
    AVG/OBP/SLG, OPS+, WAR, etc.).

    Args:
        team: 3-letter team abbreviation — same as Baseball Reference
            (e.g. ``PHI``, ``NYY``, ``LAD``, ``ARI``).
        season: Calendar year of the season (e.g. 2025).
        min_plate_appearances: Minimum PA to include on the FanGraphs pull (default 1).
            Ignored for the BRef fallback, which lists everyone who appeared.
        player_name: Optional. Restrict to one player (e.g. ``Bryce Harper``).
        max_output_rows: Max rows in the table (default 200). Capped at 5000.

    Use this for “Phillies lineup stats”, “Yankees 2024 hitters”, etc. For **league**
    leaderboards without a team filter, use ``season_batting_stats`` instead.
    """
    from pybaseball import batting_stats

    abbr = _normalize_team_abbr(team)
    data: pd.DataFrame | None = None
    fg_note = ""
    try:
        data = batting_stats(
            season, season, team=abbr, qual=min_plate_appearances
        )
        if data is None or getattr(data, "empty", True):
            fg_note = "FanGraphs returned no rows."
            data = None
    except Exception as e:
        fg_note = str(e)
        data = None

    source = "FanGraphs"
    if data is None or data.empty:
        try:
            data = _team_batting_from_bref(abbr, season)
            source = "Baseball Reference"
            if fg_note:
                source += f" — {fg_note}"
        except Exception as e2:
            return (
                f"Could not load team batting stats for {abbr} {season}. "
                f"FanGraphs: {fg_note}. Baseball Reference: {e2}"
            )

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No batting row for {player_name!r} on team {abbr} in {season} "
                "(check spelling and team)."
            )

    header = f"**Source:** {source}\n**Team:** {abbr} | **Season:** {season}\n\n"
    return header + _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_TEAM_SEASON_ROWS),
    )


@mcp.tool()
def team_season_pitching_stats(
    team: str,
    season: int,
    min_innings: int = 1,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Full-season **actual** pitching stats for one MLB team (rotation + bullpen).

    Uses **FanGraphs** when available; otherwise scrapes **Baseball Reference**'s team
    pitching table (W, L, ERA, G, GS, SV, IP, SO, WAR, etc.).

    Args:
        team: 3-letter abbreviation (e.g. ``PHI``, ``NYY``).
        season: Season year (e.g. 2025).
        min_innings: Minimum IP for the FanGraphs pull (default 1). Ignored for BRef
            fallback (full staff).
        player_name: Optional. One pitcher (e.g. ``Zack Wheeler``).
        max_output_rows: Max rows in the table (default 200). Capped at 5000.

    Split **rotation vs bullpen** by sorting on ``GS`` in the table (starters vs relievers).
    For league-wide pitching only, use ``season_pitching_stats``.
    """
    from pybaseball import pitching_stats

    abbr = _normalize_team_abbr(team)
    data: pd.DataFrame | None = None
    fg_note = ""
    try:
        data = pitching_stats(season, season, team=abbr, qual=min_innings)
        if data is None or getattr(data, "empty", True):
            fg_note = "FanGraphs returned no rows."
            data = None
    except Exception as e:
        fg_note = str(e)
        data = None

    source = "FanGraphs"
    if data is None or data.empty:
        try:
            data = _team_pitching_from_bref(abbr, season)
            source = "Baseball Reference"
            if fg_note:
                source += f" — {fg_note}"
        except Exception as e2:
            return (
                f"Could not load team pitching stats for {abbr} {season}. "
                f"FanGraphs: {fg_note}. Baseball Reference: {e2}"
            )

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No pitching row for {player_name!r} on team {abbr} in {season}."
            )

    header = f"**Source:** {source}\n**Team:** {abbr} | **Season:** {season}\n\n"
    return header + _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_TEAM_SEASON_ROWS),
    )


# ---------------------------------------------------------------------------
# Tools — Statcast Leaderboards (Expected Stats & Exit Velocity)
# ---------------------------------------------------------------------------


@mcp.tool()
def statcast_batter_expected_stats(
    year: int,
    min_plate_appearances: int = 50,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Get expected batting stats (xBA, xSLG, xwOBA vs actual) from Statcast.

    Returns xBA, xSLG, xwOBA and the gap from actual stats — what a batter
    *deserves* based on quality of contact.

    Args:
        year: Season year (e.g. 2024).
        min_plate_appearances: Minimum PA to qualify (default 50).
        player_name: Optional. If set (e.g. 'Aaron Judge'), returns only that
            player's row — use this so a star is not cut off by the 50-row
            leaderboard limit.
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Great for identifying lucky/unlucky hitters or a single player's expected line.
    """
    from pybaseball import statcast_batter_expected_stats as _fn

    try:
        data = _fn(year, minPA=min_plate_appearances)
    except Exception as e:
        return f"Error fetching expected batting stats: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No expected-stats row for {player_name} in {year} at "
                f"{min_plate_appearances}+ PA. Try a lower min_plate_appearances "
                "or confirm they qualified."
            )

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


@mcp.tool()
def statcast_pitcher_expected_stats(
    year: int,
    min_plate_appearances: int = 50,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Get expected stats allowed by pitchers from Statcast.

    Returns xBA, xSLG, xwOBA, xERA allowed vs actual — contact quality vs results.

    Args:
        year: Season year (e.g. 2024).
        min_plate_appearances: Minimum PA against to qualify (default 50).
        player_name: Optional. If set (e.g. 'Gerrit Cole'), returns only that
            pitcher's row (avoids missing them in the truncated leaderboard).
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Great for finding pitchers who outperformed or underperformed their contact quality.
    """
    from pybaseball import statcast_pitcher_expected_stats as _fn

    try:
        data = _fn(year, minPA=min_plate_appearances)
    except Exception as e:
        return f"Error fetching expected pitching stats: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No expected-stats row for {player_name} in {year} at "
                f"{min_plate_appearances}+ PA faced. Try a lower min_plate_appearances."
            )

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


@mcp.tool()
def expected_stats_batch(
    year: int,
    batters: str | None = None,
    pitchers: str | None = None,
    min_plate_appearances: int = 50,
    max_output_rows: int | None = None,
) -> str:
    """Expected stats (xBA, xSLG, xwOBA vs actual) for *multiple* batters and/or pitchers in one call.

    Use this when the user asks for a lineup, rotation, "team starters",
    or any named group (e.g. Yankees 1–9 and five starters). Pass comma-separated
    names. The MCP does not fetch MLB rosters automatically — use current
    player names from context or a quick web lookup, then list them here.

    Args:
        year: Season year (e.g. 2026). If Savant has not published that season’s leaderboard
            yet (common before Opening Day or in early April), the table may be empty — use
            the prior year for full-season expected stats, or lower ``min_plate_appearances``
            once enough games are played.
        batters: Comma-separated hitter names, e.g.
            "Aaron Judge, Juan Soto, Giancarlo Stanton, Anthony Volpe, ..."
        pitchers: Comma-separated pitcher names, e.g.
            "Gerrit Cole, Carlos Rodon, Marcus Stroman, Clarke Schmidt, Luis Gil"
        min_plate_appearances: Minimum PA to qualify (default 50).
        max_output_rows: Max rows per batter/pitcher section (default: all matched rows, up to 5000).

    Provide at least one of batters or pitchers. Semicolons and newlines also separate names.
    """
    from pybaseball import (
        statcast_batter_expected_stats as _bat_exp,
        statcast_pitcher_expected_stats as _pit_exp,
    )

    batter_names = _parse_player_name_list(batters or "")
    pitcher_names = _parse_player_name_list(pitchers or "")
    if not batter_names and not pitcher_names:
        return (
            "Provide at least one of batters or pitchers as a comma-separated list "
            '(e.g. batters="Aaron Judge, Juan Soto").'
        )

    sections: list[str] = []

    def _empty_leaderboard_note(role: str, min_pa: int) -> str:
        return (
            f"**No Statcast data for {year} yet** — the `{role}` expected-stats leaderboard "
            f"returned zero rows at `min_plate_appearances={min_pa}`. "
            "That usually means the regular season has not produced enough qualified players "
            "in Savant’s feed yet, or the year’s table is not published. "
            f"Use **`year={year - 1}`** for a complete prior-season leaderboard, or retry "
            "after more games with a **lower** `min_plate_appearances`.\n\n"
        )

    if batter_names:
        try:
            df = _bat_exp(year, minPA=min_plate_appearances)
        except Exception as e:
            return f"Error fetching batter expected stats: {e}"
        if df is None or getattr(df, "empty", True):
            sections.append(f"### Batters (expected stats, {year})\n\n")
            sections.append(_empty_leaderboard_note("batter", min_plate_appearances))
        else:
            merged, errs = _batch_filter_players(df, batter_names)
            sections.append(f"### Batters (expected stats, {year})\n\n")
            if merged.empty:
                sections.append("No batter rows matched.\n\n")
            else:
                lim = output_limit(
                    max_output_rows,
                    min(len(merged), MAX_OUTPUT_ROWS_CAP),
                )
                sections.append(_fmt(merged, max_rows=lim))
            if errs:
                sections.append("\n**Notes:** " + " | ".join(errs))

    if pitcher_names:
        try:
            df = _pit_exp(year, minPA=min_plate_appearances)
        except Exception as e:
            return f"Error fetching pitcher expected stats: {e}"
        if df is None or getattr(df, "empty", True):
            sections.append(f"\n\n### Pitchers (expected stats allowed, {year})\n\n")
            sections.append(_empty_leaderboard_note("pitcher", min_plate_appearances))
        else:
            merged, errs = _batch_filter_players(df, pitcher_names)
            sections.append(f"\n\n### Pitchers (expected stats allowed, {year})\n\n")
            if merged.empty:
                sections.append("No pitcher rows matched.\n\n")
            else:
                lim = output_limit(
                    max_output_rows,
                    min(len(merged), MAX_OUTPUT_ROWS_CAP),
                )
                sections.append(_fmt(merged, max_rows=lim))
            if errs:
                sections.append("\n**Notes:** " + " | ".join(errs))

    return "".join(sections).strip()


@mcp.tool()
def statcast_batter_pitch_arsenal(
    year: int,
    player_name: str | None = None,
    min_plate_appearances: int = 10,
    max_output_rows: int | None = None,
) -> str:
    """Get batting stats broken down by pitch type for batters.

    Returns BA, SLG, wOBA, whiff rate, K rate, run value, and hard-hit rate
    for each pitch type a batter faced (4-seam, slider, curve, changeup, etc.).

    Args:
        year: Season year (e.g. 2024).
        player_name: Optional. Filter to a specific batter (e.g. 'Aaron Judge').
            If omitted, returns the full leaderboard.
        min_plate_appearances: Minimum PA per pitch type to qualify (default 10).
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Great for analyzing how a hitter performs against fastballs vs. breaking balls.
    """
    from pybaseball import statcast_batter_pitch_arsenal as _fn

    try:
        data = _fn(year, minPA=min_plate_appearances)
    except Exception as e:
        return f"Error fetching batter pitch arsenal data: {e}"

    if player_name:
        try:
            _, display = _resolve_player(player_name)
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No pitch-type batting data for {player_name} in {year} at "
                f"{min_plate_appearances}+ PA per pitch type."
            )
        header = f"Batting stats by pitch type for {display} ({year}):\n\n"
        return header + _fmt(
            data,
            max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
        )

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


@mcp.tool()
def statcast_batter_exitvelo_barrels(
    year: int,
    min_batted_ball_events: int = 50,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Get exit velocity and barrel rate leaderboard for batters.

    Returns average exit velocity, max exit velocity, barrel percentage,
    hard-hit rate, and batted ball quality metrics. A 'barrel' is a
    batted ball with the ideal combination of exit velocity and launch angle
    that almost always results in a hit.

    Args:
        year: Season year (e.g. 2024).
        min_batted_ball_events: Minimum batted ball events to qualify (default 50).
        player_name: Optional. Filter to one batter (e.g. 'Aaron Judge').
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Great for finding the hardest hitters and best contact quality in baseball.
    """
    from pybaseball import statcast_batter_exitvelo_barrels as _fn

    try:
        data = _fn(year, minBBE=min_batted_ball_events)
    except Exception as e:
        return f"Error fetching exit velocity data: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No exit-velocity/barrel row for {player_name} in {year} at "
                f"{min_batted_ball_events}+ batted ball events."
            )

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


@mcp.tool()
def statcast_pitcher_exitvelo_barrels(
    year: int,
    min_batted_ball_events: int = 50,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Get exit velocity and barrel rate allowed by pitchers.

    Returns average exit velocity, barrel percentage, and hard-hit rate
    allowed. Lower values indicate a pitcher who limits hard contact.

    Args:
        year: Season year (e.g. 2024).
        min_batted_ball_events: Minimum batted ball events against (default 50).
        player_name: Optional. Filter to one pitcher (e.g. 'Gerrit Cole').
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Great for finding pitchers who suppress hard contact most effectively.
    """
    from pybaseball import statcast_pitcher_exitvelo_barrels as _fn

    try:
        data = _fn(year, minBBE=min_batted_ball_events)
    except Exception as e:
        return f"Error fetching exit velocity data: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No exit-velocity/barrel row for {player_name} in {year} at "
                f"{min_batted_ball_events}+ batted ball events against."
            )

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


# ---------------------------------------------------------------------------
# Tools — Pitcher Arsenal
# ---------------------------------------------------------------------------


@mcp.tool()
def statcast_pitcher_pitch_arsenal(
    year: int,
    min_pitches: int = 100,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Get pitch arsenal breakdown for all pitchers in a season.

    Shows average velocity (and related columns) per pitch type for qualifying pitchers.

    Args:
        year: Season year (e.g. 2024).
        min_pitches: Minimum total pitches thrown to qualify (default 100).
        player_name: Optional. Filter to one pitcher (e.g. 'Spencer Strider').
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Great for understanding what pitches a pitcher throws and how often.
    """
    from pybaseball import statcast_pitcher_pitch_arsenal as _fn

    try:
        data = _fn(year, minP=min_pitches)
    except Exception as e:
        return f"Error fetching pitch arsenal data: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No pitch-arsenal row for {player_name} in {year} at "
                f"{min_pitches}+ pitches thrown."
            )

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


@mcp.tool()
def statcast_pitcher_arsenal_stats(
    year: int,
    min_plate_appearances: int = 25,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Get performance stats broken down by pitch type for each pitcher.

    Shows batting average, slugging, whiff rate, put-away rate, and run values
    for every individual pitch type a pitcher throws.

    Args:
        year: Season year (e.g. 2024).
        min_plate_appearances: Minimum PA for each pitch type (default 25).
        player_name: Optional. Filter to one pitcher (all their pitch types).
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Great for evaluating which specific pitches are most (or least) effective.
    """
    from pybaseball import statcast_pitcher_arsenal_stats as _fn

    try:
        data = _fn(year, minPA=min_plate_appearances)
    except Exception as e:
        return f"Error fetching arsenal stats: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No pitcher arsenal stats for {player_name} in {year} at "
                f"{min_plate_appearances}+ PA per pitch type."
            )

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


# ---------------------------------------------------------------------------
# Tools — Sprint Speed
# ---------------------------------------------------------------------------


@mcp.tool()
def sprint_speed_leaderboard(
    year: int,
    min_opportunities: int = 10,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Get the Statcast sprint speed leaderboard.

    Returns each player's sprint speed in feet per second, measured on
    competitive running plays. Sprint speed is one of the best measures
    of raw speed and baserunning ability.

    Args:
        year: Season year (e.g. 2024).
        min_opportunities: Minimum competitive run opportunities (default 10).
        player_name: Optional. Filter to one player (e.g. 'Ronald Acuna Jr.').
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Great for finding the fastest players in baseball.
    """
    from pybaseball import statcast_sprint_speed as _fn

    try:
        data = _fn(year, min_opp=min_opportunities)
    except Exception as e:
        return f"Error fetching sprint speed data: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No sprint speed row for {player_name} in {year} at "
                f"{min_opportunities}+ opportunities."
            )

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


# ---------------------------------------------------------------------------
# Tools — Team Data
# ---------------------------------------------------------------------------


@mcp.tool()
def team_standings(season: int, max_output_rows: int | None = None) -> str:
    """Get MLB division standings for a given season.

    Returns win-loss records, winning percentage, and games back
    for all 30 teams organised by division (AL East, AL Central, AL West,
    NL East, NL Central, NL West).

    Args:
        season: The season year (e.g. 2024).
        max_output_rows: Max rows **per division** table (default 15). Capped at 5000.
    """
    from pybaseball import standings

    try:
        tables = standings(season)
    except Exception as e:
        return f"Error fetching standings: {e}"

    if not tables:
        return "No standings data found."

    division_names = [
        "AL East",
        "AL Central",
        "AL West",
        "NL East",
        "NL Central",
        "NL West",
    ]

    per_div = output_limit(max_output_rows, 15)

    parts: list[str] = []
    for i, table in enumerate(tables):
        label = division_names[i] if i < len(division_names) else f"Division {i + 1}"
        if len(table) > per_div:
            table = table.head(per_div)
        parts.append(f"### {label}\n\n{table.to_markdown(index=False)}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Tools — Percentile ranks (Statcast)
# ---------------------------------------------------------------------------


@mcp.tool()
def batter_percentile_ranks(
    year: int,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Statcast percentile ranks for hitters vs the league (exit velo, barrel%, xwOBA, etc.).

    Each metric is 0–100 where higher is better for that stat. Use to answer
    "How elite is this hitter on Statcast?" or compare league-wide.

    Args:
        year: Season year (e.g. 2024).
        player_name: Optional. If set, returns only that player's row (e.g. "Aaron Judge").
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Qualifying batters: ~2.1 PA per team game (Statcast default).
    """
    from pybaseball import statcast_batter_percentile_ranks as _fn

    try:
        data = _fn(year)
    except Exception as e:
        return f"Error fetching batter percentile ranks: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return f"No percentile data found for {player_name} in {year}."

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


@mcp.tool()
def pitcher_percentile_ranks(
    year: int,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Statcast percentile ranks for pitchers vs the league (spin, whiff%, xERA, etc.).

    Each metric is 0–100. Use for "How does this pitcher's stuff compare?"

    Args:
        year: Season year (e.g. 2024).
        player_name: Optional. Filter to one pitcher (e.g. "Gerrit Cole").
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Qualifying pitchers: Statcast minimum innings/appearance thresholds.
    """
    from pybaseball import statcast_pitcher_percentile_ranks as _fn

    try:
        data = _fn(year)
    except Exception as e:
        return f"Error fetching pitcher percentile ranks: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return f"No percentile data found for {player_name} in {year}."

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


# ---------------------------------------------------------------------------
# Tools — Defense (Statcast OAA)
# ---------------------------------------------------------------------------


@mcp.tool()
def outs_above_average(
    year: int,
    position: str,
    min_attempts: str | int = "q",
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Outs Above Average (OAA) leaderboard by defensive position.

    OAA estimates how many outs a fielder saved vs an average defender.

    Args:
        year: Season year (e.g. 2024).
        position: One of: SS, 2B, 3B, 1B, LF, CF, RF, or ALL (all infield + outfield
            positions supported by Savant). Not available for catcher in this leaderboard.
        min_attempts: Minimum fielding attempts, or "q" for qualified (default).
        player_name: Optional. Filter to one fielder (use a position they actually play).
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    """
    from pybaseball import statcast_outs_above_average as _fn

    pos = position.strip().upper()
    if pos == "ALL":
        pos = "all"

    try:
        data = _fn(year, pos, min_att=min_attempts)
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error fetching OAA: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No OAA row for {player_name} at position {position} in {year}. "
                "Try position=ALL or a different position."
            )

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


@mcp.tool()
def outfield_directional_oaa(
    year: int,
    min_opportunities: str | int = "q",
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Outfielders' Outs Above Average broken out by direction (back/in, left/right).

    Shows where outfielders add or lose value relative to average.

    Args:
        year: Season year (e.g. 2024).
        min_opportunities: Minimum opportunities, or "q" for qualified (default).
        player_name: Optional. Filter to one outfielder.
        max_output_rows: Max rows in the table (default 50). Capped at 5000.
    """
    from pybaseball import statcast_outfield_directional_oaa as _fn

    try:
        data = _fn(year, min_opp=min_opportunities)
    except Exception as e:
        return f"Error fetching directional OAA: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return (
                f"No directional OAA for {player_name} in {year}. "
                "Infielders do not appear on this leaderboard."
            )

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


# ---------------------------------------------------------------------------
# Tools — Date-range stats (Baseball Reference via pybaseball)
# ---------------------------------------------------------------------------


@mcp.tool()
def batting_stats_date_range(
    start_date: str,
    end_date: str,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Batting stats aggregated over a custom date range (Baseball Reference).

    Use for hot/cold streaks, post-deadline samples, or any window between two dates.

    Args:
        start_date: Start date YYYY-MM-DD (2008+).
        end_date: End date YYYY-MM-DD (inclusive).
        player_name: Optional. Filter to one player (matches BRef ``Name`` / ``mlbID``).
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Returns rate stats (AVG, OBP, SLG, OPS) and counting stats for that span.
    Row limit applies — many players may qualify in long ranges.
    """
    from pybaseball import batting_stats_range as _fn

    try:
        data = _fn(start_date, end_date)
    except Exception as e:
        return f"Error fetching batting stats for date range: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return f"No batting stats for {player_name} in {start_date}–{end_date}."

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


@mcp.tool()
def pitching_stats_date_range(
    start_date: str,
    end_date: str,
    player_name: str | None = None,
    max_output_rows: int | None = None,
) -> str:
    """Pitching stats aggregated over a custom date range (Baseball Reference).

    Args:
        start_date: Start date YYYY-MM-DD (2008+).
        end_date: End date YYYY-MM-DD (inclusive).
        player_name: Optional. Filter to one pitcher.
        max_output_rows: Max rows in the table (default 50). Capped at 5000.

    Returns ERA, WHIP, K/9, IP, W-L, etc. for that span.
    """
    from pybaseball import pitching_stats_range as _fn

    try:
        data = _fn(start_date, end_date)
    except Exception as e:
        return f"Error fetching pitching stats for date range: {e}"

    if player_name:
        try:
            data = _filter_player_rows(data, player_name)
        except ValueError as e:
            return str(e)
        if data.empty:
            return f"No pitching stats for {player_name} in {start_date}–{end_date}."

    return _fmt(
        data,
        max_rows=output_limit(max_output_rows, DEFAULT_LEADERBOARD_ROWS),
    )


# ---------------------------------------------------------------------------
# Expanded tools (schedules, Lahman, draft, extra Statcast, catalog)
# ---------------------------------------------------------------------------

from statcast_mcp.expanded_tools import register_expanded_tools

EXPANDED_TOOL_FUNCS = register_expanded_tools(
    mcp,
    _fmt,
    _filter_player_rows,
    _resolve_player,
    _normalize_team_abbr,
    _trim_pitch_cols,
)
"""Map of expanded-tool name → callable (for tests and introspection)."""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
