"""
Statcast MCP Server

An MCP server that provides natural-language access to MLB Statcast data.
Built on pybaseball, it exposes tools for pitch-level data, season stats,
expected stats, exit velocity, pitcher arsenals, sprint speed, and standings.
"""

from __future__ import annotations

import pandas as pd
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Statcast",
    instructions=(
        "Query MLB Statcast data using natural language. "
        "Access pitch-level data, batting and pitching stats, "
        "leaderboards, expected stats, exit velocity, pitcher arsenals, "
        "sprint speed, and team standings. Data available from 2008 onward."
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

    if "mlb_played_last" in results.columns:
        results = results.sort_values("mlb_played_last", ascending=False)

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


# ---------------------------------------------------------------------------
# Tools — Player Lookup
# ---------------------------------------------------------------------------


@mcp.tool()
def player_lookup(player_name: str) -> str:
    """Look up a baseball player to find their MLBAM ID, years active, and database IDs.

    Accepts names like 'Mike Trout', 'Trout, Mike', or 'Shohei Ohtani'.
    Useful for verifying a player's identity or finding their MLBAM / FanGraphs /
    Baseball-Reference IDs before running other queries.
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

    return _fmt(results, max_rows=10)


# ---------------------------------------------------------------------------
# Tools — Pitch-Level Statcast Data
# ---------------------------------------------------------------------------


@mcp.tool()
def statcast_search(
    start_date: str,
    end_date: str | None = None,
    team: str | None = None,
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
    return _fmt(data, max_rows=100)


@mcp.tool()
def statcast_batter(
    player_name: str,
    start_date: str,
    end_date: str | None = None,
) -> str:
    """Get pitch-level Statcast data for a specific batter in a date range.

    Returns every pitch the batter saw — pitch type, velocity, exit velocity,
    launch angle, expected batting average, and much more.

    Args:
        player_name: Full name of the batter (e.g. 'Aaron Judge').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format (defaults to start_date).

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
        + _fmt(data, max_rows=100)
    )


@mcp.tool()
def statcast_pitcher(
    player_name: str,
    start_date: str,
    end_date: str | None = None,
) -> str:
    """Get pitch-level Statcast data for a specific pitcher in a date range.

    Returns every pitch thrown — pitch type, velocity, spin rate, movement,
    exit velocity allowed, and more.

    Args:
        player_name: Full name of the pitcher (e.g. 'Gerrit Cole').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format (defaults to start_date).

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
        + _fmt(data, max_rows=100)
    )


# ---------------------------------------------------------------------------
# Tools — Season-Level Stats (FanGraphs)
# ---------------------------------------------------------------------------


@mcp.tool()
def season_batting_stats(
    start_season: int,
    end_season: int | None = None,
    min_plate_appearances: int | None = None,
) -> str:
    """Get season-level batting statistics from FanGraphs.

    Returns comprehensive stats: AVG, OBP, SLG, wOBA, wRC+, HR, SB, WAR,
    and many more for every qualifying batter.

    Args:
        start_season: First season to include (e.g. 2024).
        end_season: Last season to include. Omit for a single year.
        min_plate_appearances: Minimum plate appearances to qualify.
            Leave blank to use the FanGraphs default qualified threshold.

    Great for finding league leaders, comparing players, or reviewing a full season.
    """
    from pybaseball import batting_stats

    if end_season is None:
        end_season = start_season

    try:
        data = batting_stats(start_season, end_season, qual=min_plate_appearances)
    except Exception as e:
        return f"Error fetching batting stats: {e}"

    return _fmt(data, max_rows=50)


@mcp.tool()
def season_pitching_stats(
    start_season: int,
    end_season: int | None = None,
    min_innings: int | None = None,
) -> str:
    """Get season-level pitching statistics from FanGraphs.

    Returns comprehensive stats: ERA, FIP, WHIP, K/9, BB/9, WAR,
    and many more for every qualifying pitcher.

    Args:
        start_season: First season to include (e.g. 2024).
        end_season: Last season to include. Omit for a single year.
        min_innings: Minimum innings pitched to qualify.
            Leave blank to use the FanGraphs default qualified threshold.

    Great for finding pitching leaders, comparing pitchers, or analyzing a season.
    """
    from pybaseball import pitching_stats

    if end_season is None:
        end_season = start_season

    try:
        data = pitching_stats(start_season, end_season, qual=min_innings)
    except Exception as e:
        return f"Error fetching pitching stats: {e}"

    return _fmt(data, max_rows=50)


# ---------------------------------------------------------------------------
# Tools — Statcast Leaderboards (Expected Stats & Exit Velocity)
# ---------------------------------------------------------------------------


@mcp.tool()
def statcast_batter_expected_stats(
    year: int,
    min_plate_appearances: int = 50,
) -> str:
    """Get expected batting stats leaderboard from Statcast.

    Returns xBA (expected batting average), xSLG (expected slugging),
    xwOBA (expected weighted on-base average), and the difference from
    actual stats. These estimate what a batter *deserves* based on
    quality of contact.

    Args:
        year: Season year (e.g. 2024).
        min_plate_appearances: Minimum PA to qualify (default 50).

    Great for identifying lucky/unlucky hitters or finding undervalued players.
    """
    from pybaseball import statcast_batter_expected_stats as _fn

    try:
        data = _fn(year, minPA=min_plate_appearances)
    except Exception as e:
        return f"Error fetching expected batting stats: {e}"

    return _fmt(data, max_rows=50)


@mcp.tool()
def statcast_pitcher_expected_stats(
    year: int,
    min_plate_appearances: int = 50,
) -> str:
    """Get expected stats allowed by pitchers from Statcast.

    Returns xBA, xSLG, xwOBA allowed — what pitchers *should have* allowed
    based on contact quality. Compares expected vs. actual to reveal
    over/under-performers.

    Args:
        year: Season year (e.g. 2024).
        min_plate_appearances: Minimum PA against to qualify (default 50).

    Great for finding pitchers who outperformed or underperformed their contact quality.
    """
    from pybaseball import statcast_pitcher_expected_stats as _fn

    try:
        data = _fn(year, minPA=min_plate_appearances)
    except Exception as e:
        return f"Error fetching expected pitching stats: {e}"

    return _fmt(data, max_rows=50)


@mcp.tool()
def statcast_batter_pitch_arsenal(
    year: int,
    player_name: str | None = None,
    min_plate_appearances: int = 10,
) -> str:
    """Get batting stats broken down by pitch type for batters.

    Returns BA, SLG, wOBA, whiff rate, K rate, run value, and hard-hit rate
    for each pitch type a batter faced (4-seam, slider, curve, changeup, etc.).

    Args:
        year: Season year (e.g. 2024).
        player_name: Optional. Filter to a specific batter (e.g. 'Aaron Judge').
            If omitted, returns the full leaderboard.
        min_plate_appearances: Minimum PA per pitch type to qualify (default 10).

    Great for analyzing how a hitter performs against fastballs vs. breaking balls.
    """
    from pybaseball import statcast_batter_pitch_arsenal as _fn

    try:
        data = _fn(year, minPA=min_plate_appearances)
    except Exception as e:
        return f"Error fetching batter pitch arsenal data: {e}"

    if player_name:
        try:
            _, full_name = _resolve_player(player_name)
            # Data uses "Last, First" format
            parts = full_name.split()
            search_name = f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else full_name
            mask = data["last_name, first_name"].str.contains(
                search_name,
                case=False,
                na=False,
            )
            data = data[mask]
            if data.empty:
                return f"No pitch-by-pitch data found for {player_name} in {year}."
            header = f"Batting stats by pitch type for {full_name} ({year}):\n\n"
            return header + _fmt(data, max_rows=20)
        except ValueError as e:
            return str(e)

    return _fmt(data, max_rows=50)


@mcp.tool()
def statcast_batter_exitvelo_barrels(
    year: int,
    min_batted_ball_events: int = 50,
) -> str:
    """Get exit velocity and barrel rate leaderboard for batters.

    Returns average exit velocity, max exit velocity, barrel percentage,
    hard-hit rate, and batted ball quality metrics. A 'barrel' is a
    batted ball with the ideal combination of exit velocity and launch angle
    that almost always results in a hit.

    Args:
        year: Season year (e.g. 2024).
        min_batted_ball_events: Minimum batted ball events to qualify (default 50).

    Great for finding the hardest hitters and best contact quality in baseball.
    """
    from pybaseball import statcast_batter_exitvelo_barrels as _fn

    try:
        data = _fn(year, minBBE=min_batted_ball_events)
    except Exception as e:
        return f"Error fetching exit velocity data: {e}"

    return _fmt(data, max_rows=50)


@mcp.tool()
def statcast_pitcher_exitvelo_barrels(
    year: int,
    min_batted_ball_events: int = 50,
) -> str:
    """Get exit velocity and barrel rate allowed by pitchers.

    Returns average exit velocity, barrel percentage, and hard-hit rate
    allowed. Lower values indicate a pitcher who limits hard contact.

    Args:
        year: Season year (e.g. 2024).
        min_batted_ball_events: Minimum batted ball events against (default 50).

    Great for finding pitchers who suppress hard contact most effectively.
    """
    from pybaseball import statcast_pitcher_exitvelo_barrels as _fn

    try:
        data = _fn(year, minBBE=min_batted_ball_events)
    except Exception as e:
        return f"Error fetching exit velocity data: {e}"

    return _fmt(data, max_rows=50)


# ---------------------------------------------------------------------------
# Tools — Pitcher Arsenal
# ---------------------------------------------------------------------------


@mcp.tool()
def statcast_pitcher_pitch_arsenal(
    year: int,
    min_pitches: int = 100,
) -> str:
    """Get pitch arsenal breakdown for all pitchers in a season.

    Shows the percentage mix of each pitch type thrown (four-seam fastball,
    slider, curveball, changeup, etc.) for every qualifying pitcher.

    Args:
        year: Season year (e.g. 2024).
        min_pitches: Minimum total pitches thrown to qualify (default 100).

    Great for understanding what pitches a pitcher throws and how often.
    """
    from pybaseball import statcast_pitcher_pitch_arsenal as _fn

    try:
        data = _fn(year, minP=min_pitches)
    except Exception as e:
        return f"Error fetching pitch arsenal data: {e}"

    return _fmt(data, max_rows=50)


@mcp.tool()
def statcast_pitcher_arsenal_stats(
    year: int,
    min_plate_appearances: int = 25,
) -> str:
    """Get performance stats broken down by pitch type for each pitcher.

    Shows batting average, slugging, whiff rate, put-away rate, and run values
    for every individual pitch type a pitcher throws.

    Args:
        year: Season year (e.g. 2024).
        min_plate_appearances: Minimum PA for each pitch type (default 25).

    Great for evaluating which specific pitches are most (or least) effective.
    """
    from pybaseball import statcast_pitcher_arsenal_stats as _fn

    try:
        data = _fn(year, minPA=min_plate_appearances)
    except Exception as e:
        return f"Error fetching arsenal stats: {e}"

    return _fmt(data, max_rows=50)


# ---------------------------------------------------------------------------
# Tools — Sprint Speed
# ---------------------------------------------------------------------------


@mcp.tool()
def sprint_speed_leaderboard(
    year: int,
    min_opportunities: int = 10,
) -> str:
    """Get the Statcast sprint speed leaderboard.

    Returns each player's sprint speed in feet per second, measured on
    competitive running plays. Sprint speed is one of the best measures
    of raw speed and baserunning ability.

    Args:
        year: Season year (e.g. 2024).
        min_opportunities: Minimum competitive run opportunities (default 10).

    Great for finding the fastest players in baseball.
    """
    from pybaseball import statcast_sprint_speed as _fn

    try:
        data = _fn(year, min_opportunities=min_opportunities)
    except Exception as e:
        return f"Error fetching sprint speed data: {e}"

    return _fmt(data, max_rows=50)


# ---------------------------------------------------------------------------
# Tools — Team Data
# ---------------------------------------------------------------------------


@mcp.tool()
def team_standings(season: int) -> str:
    """Get MLB division standings for a given season.

    Returns win-loss records, winning percentage, and games back
    for all 30 teams organised by division (AL East, AL Central, AL West,
    NL East, NL Central, NL West).

    Args:
        season: The season year (e.g. 2024).
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

    parts: list[str] = []
    for i, table in enumerate(tables):
        label = division_names[i] if i < len(division_names) else f"Division {i + 1}"
        parts.append(f"### {label}\n\n{table.to_markdown(index=False)}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
