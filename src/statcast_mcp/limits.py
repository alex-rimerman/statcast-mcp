"""Output row limits for MCP markdown tables (user-overridable)."""

from __future__ import annotations

# Hard cap so a single tool call cannot dump unbounded rows into the chat.
MAX_OUTPUT_ROWS_CAP = 5000

DEFAULT_LEADERBOARD_ROWS = 50
DEFAULT_PITCH_LEVEL_ROWS = 100
DEFAULT_TEAM_SEASON_ROWS = 200
DEFAULT_PLAYER_LOOKUP_ROWS = 10

# Expanded tools (schedules, splits, Lahman slices, etc.)
DEFAULT_SCHEDULE_ROWS = 250
DEFAULT_LAHMAN_TEAMS_ROWS = 60
DEFAULT_LEAGUE_TEAM_TOTALS_ROWS = 40
DEFAULT_PLAYER_SPLITS_PRIMARY_ROWS = 120
DEFAULT_PLAYER_SPLITS_PITCHING_GAME_ROWS = 80
DEFAULT_PLAYER_SPLITS_SINGLE_TABLE_ROWS = 200
DEFAULT_BVP_SAMPLE_ROWS = 80


def output_limit(requested: int | None, default: int) -> int:
    """Return the number of rows to show in ``_fmt``.

    * ``requested`` is ``None`` → use ``default`` (per-tool: 50, 100, 200, etc.).
    * Otherwise clamp to ``[1, MAX_OUTPUT_ROWS_CAP]``.
    """
    if requested is None:
        return default
    try:
        n = int(requested)
    except (TypeError, ValueError):
        return default
    if n < 1:
        return default
    return min(n, MAX_OUTPUT_ROWS_CAP)
