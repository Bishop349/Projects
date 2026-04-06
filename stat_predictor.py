#!/usr/bin/env python3
"""
Minnesota Timberwolves — Live Stat Predictor

Requirements:
    pip install nba_api
"""

import argparse
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Terminal colors ───────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    GREEN  = "\033[38;5;35m"
    BLUE   = "\033[38;5;69m"
    SILVER = "\033[38;5;247m"
    YELLOW = "\033[38;5;220m"
    RED    = "\033[38;5;160m"
    CYAN   = "\033[38;5;80m"
    GRAY   = "\033[38;5;240m"
    PURPLE = "\033[38;5;141m"
    ORANGE = "\033[38;5;208m"

def green(s):  return f"{C.GREEN}{s}{C.RESET}"
def bold(s):   return f"{C.BOLD}{s}{C.RESET}"
def dim(s):    return f"{C.DIM}{C.SILVER}{s}{C.RESET}"
def yellow(s): return f"{C.YELLOW}{s}{C.RESET}"
def red(s):    return f"{C.RED}{s}{C.RESET}"
def blue(s):   return f"{C.BLUE}{s}{C.RESET}"
def gray(s):   return f"{C.GRAY}{s}{C.RESET}"
def cyan(s):   return f"{C.CYAN}{s}{C.RESET}"
def purple(s): return f"{C.PURPLE}{s}{C.RESET}"
def orange(s): return f"{C.ORANGE}{s}{C.RESET}"

def strip_ansi(s):
    return re.sub(r"\033\[[0-9;]*m", "", str(s))

def rjust(s, w):
    pad = max(0, w - len(strip_ansi(str(s))))
    return " " * pad + str(s)

def ljust(s, w):
    pad = max(0, w - len(strip_ansi(str(s))))
    return str(s) + " " * pad

# ── Constants ─────────────────────────────────────────────────────────────────

MIN_TEAM_ID    = 1610612750   # Minnesota Timberwolves NBA.com team ID
NBA_GAME_MINS  = 48.0         # regulation minutes per game
DB_PATH        = Path(__file__).parent / "timberwolves_2025_26.db"

# Weights: how much to trust live pace vs season average
# Early game → trust season avg more. Late game → trust live pace more.
def blend_weight(minutes_played: float) -> float:
    """Returns 0.0–1.0: how much weight to give the live per-min pace."""
    if minutes_played <= 0:
        return 0.0
    # Ramp from 0 → 1 over the first 24 minutes (half a game)
    return min(1.0, minutes_played / 24.0)

# ── Database ──────────────────────────────────────────────────────────────────

def load_season_averages() -> dict:
    """
    Load 2025-26 season averages from the SQLite DB.
    Returns dict keyed by lowercase player name → stats dict.
    """
    if not DB_PATH.exists():
        print(red(f"⚠  Database not found: {DB_PATH}"))
        print(dim("   Run timberwolves_stats.py first to create it."))
        return {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM player_averages").fetchall()
    conn.close()

    averages = {}
    for r in rows:
        key = r["player"].lower().strip()
        averages[key] = {
            "player":    r["player"],
            "games":     r["games"],
            "minutes":   r["minutes"],   # avg min/game
            "points":    r["points"],
            "off_reb":   r["off_reb"],
            "def_reb":   r["def_reb"],
            "rebounds":  r["rebounds"],
            "assists":   r["assists"],
            "steals":    r["steals"],
            "blocks":    r["blocks"],
            "turnovers": r["turnovers"],
        }
    return averages


def match_player(name: str, averages: dict) -> dict | None:
    """Fuzzy-match a live player name to the DB. Handles 'Last, First' format."""
    # NBA API sometimes returns "Last, First" — normalize to "First Last"
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        name = f"{parts[1]} {parts[0]}"

    key = name.lower().strip()

    # Exact match
    if key in averages:
        return averages[key]

    # Partial match — first + last token
    tokens = key.split()
    for k, v in averages.items():
        k_tokens = k.split()
        if tokens and k_tokens:
            if tokens[-1] == k_tokens[-1] and tokens[0][0] == k_tokens[0][0]:
                return v

    # Last-name only fallback
    for k, v in averages.items():
        if tokens and k.split()[-1] == tokens[-1]:
            return v

    return None

# ── Live data (same logic as wolves_stats.py) ────────────────────────────────

def _parse_minutes(raw: str) -> float:
    try:
        m = re.search(r"PT(\d+)M([\d.]+)S", raw)
        if m:
            return float(m.group(1)) + float(m.group(2)) / 60
        m2 = re.search(r"PT(\d+)M", raw)
        return float(m2.group(1)) if m2 else 0.0
    except Exception:
        return 0.0


def _fmt_clock(raw_clock: str, period: int) -> str:
    try:
        m = re.search(r"PT(\d+)M([\d.]+)S", raw_clock)
        if not m:
            return raw_clock
        mins = int(m.group(1))
        secs = int(float(m.group(2)))
        q = f"Q{period}" if period <= 4 else f"OT{period - 4}"
        return f"{q} {mins}:{secs:02d}"
    except Exception:
        return raw_clock


def minutes_elapsed(period: int, clock_raw: str) -> float:
    """Total game minutes elapsed so far."""
    try:
        m = re.search(r"PT(\d+)M([\d.]+)S", clock_raw)
        mins_left = float(m.group(1)) + float(m.group(2)) / 60 if m else 0.0
    except Exception:
        mins_left = 0.0

    if period == 0:
        return 0.0
    completed_periods = max(0, period - 1)
    mins_per_period = 12.0 if period <= 4 else 5.0
    return completed_periods * 12.0 + (mins_per_period - mins_left)


def fetch_live() -> dict:
    from nba_api.live.nba.endpoints import scoreboard, boxscore

    board  = scoreboard.ScoreBoard()
    games  = board.get_dict()["scoreboard"]["games"]

    target_game_id = None
    opp_name   = "OPP"
    score_min  = "—"
    score_opp  = "—"
    status_text = "scheduled"
    clock_text  = ""
    clock_raw   = ""
    period      = 0

    for g in games:
        home_id = g["homeTeam"]["teamId"]
        away_id = g["awayTeam"]["teamId"]
        if home_id == MIN_TEAM_ID or away_id == MIN_TEAM_ID:
            target_game_id = g["gameId"]
            is_home = (home_id == MIN_TEAM_ID)

            opp_name  = g["awayTeam"]["teamTricode"] if is_home else g["homeTeam"]["teamTricode"]
            score_min = g["homeTeam"]["score"] if is_home else g["awayTeam"]["score"]
            score_opp = g["awayTeam"]["score"] if is_home else g["homeTeam"]["score"]

            gs        = g.get("gameStatus", 1)
            clock_raw = g.get("gameClock", "")
            period    = g.get("period", 0)

            if gs == 1:
                status_text = "scheduled"
                et = g.get("gameEt", "")
                try:
                    dt = datetime.strptime(et, "%Y-%m-%dT%H:%M:%SZ")
                    clock_text = dt.strftime("%-I:%M %p ET")
                except Exception:
                    clock_text = et
            elif gs == 2:
                status_text = "live"
                clock_text  = _fmt_clock(clock_raw, period)
            else:
                status_text = "final"
                clock_text  = "Final"
            break

    if not target_game_id:
        return {"status": "no_game", "clock": "No Timberwolves game today",
                "period": 0, "clockRaw": "", "scoreMin": "—",
                "scoreOpp": "—", "oppName": "—", "players": []}

    players = []
    if status_text in ("live", "final"):
        box      = boxscore.BoxScore(game_id=target_game_id)
        box_dict = box.get_dict()["game"]

        home_id   = box_dict["homeTeam"]["teamId"]
        team_data = box_dict["homeTeam"] if home_id == MIN_TEAM_ID else box_dict["awayTeam"]

        for p in team_data.get("players", []):
            s = p.get("statistics", {})
            if p.get("played", "0") != "1":
                continue

            fg_made = s.get("fieldGoalsMade", 0)
            fg_att  = s.get("fieldGoalsAttempted", 0)
            fg_pct  = round(s.get("fieldGoalsPercentage", 0) * 100, 1) if fg_att > 0 else 0.0

            players.append({
                "name":    p.get("name", "Unknown"),
                "pos":     p.get("position", ""),
                "min":     _parse_minutes(s.get("minutesCalculated", "PT0M")),
                "pts":     s.get("points", 0),
                "reb":     s.get("reboundsTotal", 0),
                "ast":     s.get("assists", 0),
                "stl":     s.get("steals", 0),
                "blk":     s.get("blocks", 0),
                "fgMade":  fg_made,
                "fgAtt":   fg_att,
                "fgPct":   fg_pct,
                "pm":      int(s.get("plusMinusPoints", 0)),
            })

    return {
        "status":   status_text,
        "clock":    clock_text,
        "clockRaw": clock_raw,
        "period":   period,
        "scoreMin": score_min,
        "scoreOpp": score_opp,
        "oppName":  opp_name,
        "players":  players,
    }

# ── Prediction engine ─────────────────────────────────────────────────────────

def predict(live: dict, avg: dict | None, game_mins_elapsed: float, status: str) -> dict:
    """
    Predict end-of-game stats for one player.

    Strategy:
      1. Estimate minutes player will finish with (blend live pace + avg).
      2. For each stat, compute:
           live_rate   = stat / mins_played  (per minute so far)
           avg_rate    = season_avg / avg_mins_per_game  (per minute historically)
           blended_rate = lerp(avg_rate, live_rate, weight)
      3. projected_final = already_accumulated + blended_rate * mins_remaining
    """
    mins_played = live["min"]
    result      = {}

    # ── Projected minutes ──────────────────────────────────────────────────
    if avg:
        avg_min_game = max(1.0, avg["minutes"])
    else:
        avg_min_game = 28.0  # fallback for unknown players

    if status == "final":
        proj_min = mins_played
    else:
        if mins_played > 0 and game_mins_elapsed > 0:
            live_min_rate  = mins_played / game_mins_elapsed
            avg_min_rate   = avg_min_game / NBA_GAME_MINS
            w              = blend_weight(mins_played)
            blended_rate   = (1 - w) * avg_min_rate + w * live_min_rate
            proj_min       = mins_played + blended_rate * (NBA_GAME_MINS - game_mins_elapsed)
        else:
            proj_min = avg_min_game
        proj_min = min(proj_min, NBA_GAME_MINS)

    result["proj_min"] = round(proj_min, 1)
    mins_remaining     = max(0.0, proj_min - mins_played)

    # ── Per-stat projection ────────────────────────────────────────────────
    stat_map = [
        ("pts",  "points"),
        ("reb",  "rebounds"),
        ("ast",  "assists"),
        ("stl",  "steals"),
        ("blk",  "blocks"),
    ]

    for live_key, avg_key in stat_map:
        current = live[live_key]

        if avg:
            avg_per_game = avg.get(avg_key, 0.0)
            avg_rate     = avg_per_game / max(1.0, avg_min_game)   # per minute
        else:
            avg_rate = 0.0

        if mins_played > 0:
            live_rate = current / mins_played
        else:
            live_rate = avg_rate

        w            = blend_weight(mins_played)
        blended_rate = (1 - w) * avg_rate + w * live_rate
        projection   = current + blended_rate * mins_remaining

        result[f"proj_{live_key}"] = round(projection, 1)

    # Confidence: higher once more minutes are played
    if mins_played == 0:
        result["confidence"] = "LOW"
    elif mins_played < 10:
        result["confidence"] = "LOW"
    elif mins_played < 20:
        result["confidence"] = "MED"
    else:
        result["confidence"] = "HIGH"

    return result

# ── Display ───────────────────────────────────────────────────────────────────

W = 104

def fmt_pm(pm):
    if pm > 0: return green(f"+{pm}")
    if pm < 0: return red(str(pm))
    return gray("0")

def conf_badge(c):
    if c == "HIGH": return green("HIGH")
    if c == "MED":  return yellow("MED ")
    return red("LOW ")

def proj_arrow(current, projected):
    """Show ↑ ↓ → based on whether projection is above/below current."""
    if projected > current + 0.4: return green("↑")
    if projected < current - 0.4: return red("↓")
    return dim("→")

def fmt_proj(current, projected):
    arrow = proj_arrow(current, projected)
    val   = f"{projected:.1f}"
    if projected >= current + 2:
        val = yellow(bold(val))
    elif projected <= current - 2:
        val = red(val)
    return f"{arrow}{val}"

def status_str(status):
    if status in ("live", "inprogress"): return red("● LIVE")
    if status == "final":               return dim("FINAL")
    if status == "no_game":             return gray("NO GAME TODAY")
    return blue("UPCOMING")

def render(data: dict, averages: dict, sort_key: str = "pts"):
    now    = datetime.now().strftime("%I:%M %p")
    status = data["status"]
    opp    = data["oppName"]
    clock  = data["clock"]

    game_elapsed = minutes_elapsed(data["period"], data["clockRaw"])

    print()
    print(green("▓" * W))
    print(f"  {bold(green('MINNESOTA TIMBERWOLVES'))}  {purple('Stat Predictor')}  {dim('· season avg + live pace')}")
    print(gray("─" * W))

    sm = bold(str(data["scoreMin"])) if isinstance(data["scoreMin"], int) else "—"
    so = bold(str(data["scoreOpp"])) if isinstance(data["scoreOpp"], int) else "—"
    print(f"  {green('MIN')} {sm}  {dim('vs')}  {so} {cyan(opp)}   {status_str(status)}  {dim(clock)}")

    if game_elapsed > 0:
        pct = min(100, int(game_elapsed / NBA_GAME_MINS * 100))
        bar_len = 30
        filled  = int(bar_len * pct / 100)
        bar     = green("█" * filled) + gray("░" * (bar_len - filled))
        print(f"  {dim('Game progress:')} {bar} {dim(f'{game_elapsed:.0f}/{NBA_GAME_MINS:.0f} min  ({pct}%)')}")

    print(gray("─" * W))

    if not data["players"]:
        print()
        if status == "no_game":
            print(f"  {dim('No Timberwolves game today.')}")
        elif status == "scheduled":
            print(f"  {dim(f'Game has not started · Tip-off: {clock}')}")
            print(f"  {dim('Season averages are shown as projected baseline.')}")
        print()
        print(green("▓" * W))
        return

    # Build enriched player rows
    rows = []
    for p in data["players"]:
        db_avg = match_player(p["name"], averages)
        proj   = predict(p, db_avg, game_elapsed, status)
        rows.append({**p, **proj, "avg": db_avg})

    SORT = {
        "pts": lambda r: r["proj_pts"],
        "reb": lambda r: r["proj_reb"],
        "ast": lambda r: r["proj_ast"],
        "min": lambda r: r["proj_min"],
        "pm":  lambda r: r["pm"],
    }
    rows.sort(key=SORT.get(sort_key, SORT["pts"]), reverse=True)

    # ── Header ──
    COL = dict(name=22, pos=3, min=5, pts=5, reb=5, ast=5, stl=4, blk=4,
                ppts=7, preb=7, past=7, conf=5, pm=5)

    def h(label, w, right=True):
        s = rjust(label, w) if right else ljust(label, w)
        return dim(s)

    sep = dim("│")
    print(
        f"  {h('PLAYER',COL['name'],False)}"
        f" {h('POS',COL['pos'])}"
        f" {h('MIN',COL['min'])}"
        f" {sep}"
        f" {h('PTS',COL['pts'])}"
        f" {h('REB',COL['reb'])}"
        f" {h('AST',COL['ast'])}"
        f" {h('STL',COL['stl'])}"
        f" {h('BLK',COL['blk'])}"
        f" {sep}"
        f" {h('~PTS',COL['ppts'])}"
        f" {h('~REB',COL['preb'])}"
        f" {h('~AST',COL['past'])}"
        f" {h('+/-',COL['pm'])}"
        f" {h('CONF',COL['conf'])}"
    )

    subhdr_live = dim(ljust("── LIVE NOW ──────────────────", 42))
    subhdr_proj = dim(ljust("── PROJECTED FINAL ──────────", 37))
    print(f"  {' ' * (COL['name'] + COL['pos'] + COL['min'] + 3)} {sep} {subhdr_live} {sep} {subhdr_proj}")

    print(gray("─" * W))

    for r in rows:
        avg = r["avg"]
        name_disp = r["name"]
        if "," in name_disp:
            parts     = [p.strip() for p in name_disp.split(",", 1)]
            name_disp = f"{parts[1]} {parts[0]}"

        avg_pts = f"{avg['points']:.1f}" if avg else "—"
        avg_reb = f"{avg['rebounds']:.1f}" if avg else "—"
        avg_ast = f"{avg['assists']:.1f}" if avg else "—"

        print(
            f"  {ljust(bold(name_disp[:COL['name']]), COL['name'])}"
            f" {rjust(dim(r['pos']), COL['pos'])}"
            f" {rjust(str(int(r['min'])), COL['min'])}"
            f" {sep}"
            f" {rjust(str(r['pts']), COL['pts'])}"
            f" {rjust(str(r['reb']), COL['reb'])}"
            f" {rjust(str(r['ast']), COL['ast'])}"
            f" {rjust(str(r['stl']), COL['stl'])}"
            f" {rjust(str(r['blk']), COL['blk'])}"
            f" {sep}"
            f" {rjust(fmt_proj(r['pts'], r['proj_pts']), COL['ppts'])}"
            f" {rjust(fmt_proj(r['reb'], r['proj_reb']), COL['preb'])}"
            f" {rjust(fmt_proj(r['ast'], r['proj_ast']), COL['past'])}"
            f" {rjust(fmt_pm(r['pm']), COL['pm'])}"
            f" {rjust(conf_badge(r['confidence']), COL['conf'])}"
        )

        # Season avg sub-row
        print(
            f"  {ljust(dim(f'season avg → {avg_pts}pts  {avg_reb}reb  {avg_ast}ast'), W - 4)}"
        )

    print(gray("─" * W))
    print(
        f"  {dim('~ = projected final  │  CONF = prediction confidence  │  arrow = vs current pace')}"
    )
    print(green("▓" * W))
    print(
        f"  {dim('Updated ' + now)}  "
        f"{dim('│')}  {dim('DB: timberwolves_2025_26.db')}  "
        f"{dim('│')}  {dim('Source: NBA.com via nba_api')}"
    )
    print()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Timberwolves live stat predictor — blends season averages with live pace."
    )
    parser.add_argument("--sort", default="pts",
                        choices=["pts", "reb", "ast", "min", "pm"],
                        help="Sort projected stats by column (default: pts)")
    parser.add_argument("--watch", action="store_true",
                        help="Auto-refresh on an interval")
    parser.add_argument("--interval", type=int, default=60,
                        help="Seconds between refreshes in watch mode (default: 60)")
    args = parser.parse_args()

    try:
        import nba_api  # noqa: F401
    except ImportError:
        print(red("Error: nba_api is not installed."))
        print(dim("  pip install nba_api"))
        sys.exit(1)

    averages = load_season_averages()
    if not averages:
        print(red("No season averages loaded — predictions will use live pace only."))

    def run_once():
        print(dim(f"\nFetching live data ({datetime.now().strftime('%I:%M:%S %p')})..."))
        try:
            data = fetch_live()
            if args.watch:
                print("\033[H\033[J", end="")
            render(data, averages, sort_key=args.sort)
        except Exception as e:
            print(red(f"Error: {e}"))
            import traceback; traceback.print_exc()

    if args.watch:
        print(cyan(f"Watching — refreshing every {args.interval}s. Ctrl+C to stop."))
        try:
            while True:
                run_once()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print(dim("\nStopped."))
    else:
        run_once()


if __name__ == "__main__":
    main()