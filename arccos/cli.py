"""
arccos CLI — pull your Arccos Golf data from the terminal.

Uses the reverse-engineered Arccos Golf API. Not affiliated with Arccos Golf LLC.
"""

from __future__ import annotations

import json
import os
import sys

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client():
    """Build an ArccosClient from env vars or cached creds, with a friendly error."""
    from arccos import ArccosClient
    from arccos.exceptions import ArccosAuthError

    email    = os.environ.get("ARCCOS_EMAIL")
    password = os.environ.get("ARCCOS_PASSWORD")

    try:
        return ArccosClient(email=email, password=password)
    except ArccosAuthError as e:
        err_console.print(f"[red]Auth failed:[/red] {e}")
        err_console.print("Run [bold]arccos login[/bold] or set ARCCOS_EMAIL and ARCCOS_PASSWORD.")
        sys.exit(1)
    except ValueError:
        err_console.print(
            "[red]Not logged in.[/red] Run [bold]arccos login[/bold] first, or set "
            "ARCCOS_EMAIL and ARCCOS_PASSWORD environment variables."
        )
        sys.exit(1)


def _output_json(data):
    click.echo(json.dumps(data, indent=2))


def _flag(minutes: int) -> str:
    if minutes > 300:
        return "\U0001f534"
    if minutes > 270:
        return "\U0001f7e1"
    return "\U0001f7e2"


def _build_course_map(client) -> dict[int, str]:
    """Build a courseId → courseName lookup from the user's played courses."""
    try:
        played = client.courses.played()
        return {
            c["courseId"]: c.get("courseName") or c.get("name") or f"Course {c['courseId']}"
            for c in played
        }
    except Exception:
        return {}


def _score_color(score: int, par: int | None) -> str:
    """Return a Rich color string based on score relative to par."""
    if par is None:
        return "bold"
    diff = score - par
    if diff <= -2:
        return "bold yellow"  # eagle or better
    if diff == -1:
        return "bold green"   # birdie
    if diff == 0:
        return "white"        # par
    if diff == 1:
        return "red"          # bogey
    return "bold red"         # double+


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="arccos", prog_name="arccos")
def cli():
    """
    \b
    arccos — Your Arccos Golf data in the terminal.

    \b
    Quick start:
      arccos login                 Authenticate and save credentials
      arccos rounds                Your recent rounds
      arccos round <id>            Hole-by-hole round detail
      arccos handicap              Current handicap index
      arccos clubs                 Smart club distances
      arccos courses               Courses you've played
      arccos pace                  Pace of play by course
      arccos stats                 Strokes gained analysis
      arccos bests                 Personal bests (all-time records)
      arccos overview              Overall stats (GIR%, FIR%, putts)
      arccos scoring               Scoring trend over recent rounds
      arccos export                Export rounds to JSON/CSV
      arccos logout                Clear cached credentials

    \b
    Credentials are cached in ~/.arccos_creds.json after first login.
    Set ARCCOS_EMAIL and ARCCOS_PASSWORD to skip the prompts.
    """


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--email", envvar="ARCCOS_EMAIL", prompt="Arccos email",
              help="Your Arccos account email.")
@click.option("--password", envvar="ARCCOS_PASSWORD", prompt="Password",
              hide_input=True, help="Your Arccos password.")
def login(email: str, password: str):
    """Authenticate and save credentials to ~/.arccos_creds.json."""
    from arccos import ArccosClient
    from arccos.exceptions import ArccosAuthError

    with console.status("Logging in\u2026"):
        try:
            client = ArccosClient(email=email, password=password)
        except ArccosAuthError as e:
            err_console.print(f"[red]Login failed:[/red] {e}")
            sys.exit(1)

    console.print(f"[green]\u2713[/green] Logged in as [bold]{client.email}[/bold]")
    console.print(f"  User ID: [dim]{client.user_id}[/dim]")
    console.print("  Credentials cached at [dim]~/.arccos_creds.json[/dim]")


# ---------------------------------------------------------------------------
# rounds
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--limit", "-n", default=20, show_default=True,
              help="Number of rounds to show.")
@click.option("--offset", "-o", default=0,         show_default=True, help="Pagination offset.")
@click.option("--after",  "-a", default=None,      help="Show rounds after date (YYYY-MM-DD).")
@click.option("--before", "-b", default=None,      help="Show rounds before date (YYYY-MM-DD).")
@click.option("--course", "-c", default=None,      help="Filter by course name (substring match).")
@click.option("--json",   "as_json", is_flag=True, help="Output raw JSON.")
def rounds(limit: int, offset: int, after: str, before: str, course: str, as_json: bool):
    """List your recent golf rounds."""
    client = _get_client()

    with console.status("Fetching rounds\u2026"):
        data = client.rounds.list(
            limit=limit, offset=offset,
            after_date=after, before_date=before,
        )
        course_map = _build_course_map(client)

    if as_json:
        _output_json(data)
        return

    if not data:
        console.print("[dim]No rounds found.[/dim]")
        return

    # Client-side course name filter (case-insensitive substring)
    if course:
        needle = course.lower()
        data = [
            r for r in data
            if needle in (course_map.get(r.get("courseId"), "")).lower()
        ]
        if not data:
            console.print(f"[dim]No rounds found matching \"{course}\".[/dim]")
            return

    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        title=f"[bold]Rounds[/bold] [dim]({len(data)} shown)[/dim]",
    )
    table.add_column("Date",    style="white",  no_wrap=True)
    table.add_column("Score",   style="bold",   justify="right")
    table.add_column("+/-",     justify="right")
    table.add_column("Holes",   justify="right")
    table.add_column("Course")
    table.add_column("ID",      justify="right", style="dim")

    for r in data:
        date  = r.get("startTime", "")[:10]
        score = str(r.get("noOfShots", "\u2014"))
        ou    = r.get("overUnder")
        ou_s  = f"{ou:+d}" if ou is not None else ""
        holes = str(r.get("noOfHoles", "\u2014"))
        cname = course_map.get(r.get("courseId"), str(r.get("courseId", "\u2014")))
        rid   = str(r.get("roundId", "\u2014"))
        table.add_row(date, score, ou_s, holes, cname, rid)

    console.print(table)


# ---------------------------------------------------------------------------
# handicap
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--history", "-H", is_flag=True,    help="Show handicap history instead of current.")
@click.option("--rounds", "-n", default=20, show_default=True,
              help="Rounds to include in history.")
@click.option("--json",   "as_json", is_flag=True, help="Output raw JSON.")
def handicap(history: bool, rounds: int, as_json: bool):
    """Show your current handicap index (or revision history)."""
    client = _get_client()

    with console.status("Fetching handicap\u2026"):
        data = (
            client.handicap.history(rounds=rounds)
            if history
            else client.handicap.current()
        )

    if as_json:
        _output_json(data)
        return

    if not history:
        # The API returns SGA-style handicap breakdown
        HCP_LABELS = {
            "userHcp": "Overall",
            "driveHcp": "Driving",
            "approachHcp": "Approach",
            "chipHcp": "Short Game",
            "sandHcp": "Sand",
            "puttHcp": "Putting",
        }
        if isinstance(data, dict) and "userHcp" in data:
            table = Table(
                box=box.ROUNDED,
                header_style="bold cyan",
                title="[bold]Handicap Breakdown[/bold]",
            )
            table.add_column("Category", style="white bold")
            table.add_column("HCP", justify="right", style="bold")
            for key, label in HCP_LABELS.items():
                val = data.get(key)
                if val is None:
                    continue
                # Arccos uses negative = better (lower handicap)
                color = "green" if val < -15 else "yellow" if val < -10 else "red"
                table.add_row(label, f"[{color}]{val:.1f}[/{color}]")
            console.print(table)
        else:
            console.print(Panel(
                Text(str(data), justify="center"),
                title="[bold cyan]Handicap Index[/bold cyan]",
                expand=False,
            ))
    else:
        if not data:
            console.print("[dim]No handicap history found.[/dim]")
            return
        table = Table(
            box=box.ROUNDED, header_style="bold cyan",
            title="[bold]Handicap History[/bold]",
        )
        first = data[0] if isinstance(data, list) else data
        if isinstance(first, dict):
            for key in first:
                table.add_column(key)
            for row in data:
                table.add_row(*[str(v) for v in row.values()])
        else:
            table.add_column("Entry")
            for row in data:
                table.add_row(str(row))
        console.print(table)


# ---------------------------------------------------------------------------
# clubs
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--after",  "-a", default=None,      help="Filter shots after date (YYYY-MM-DD).")
@click.option("--before", "-b", default=None,      help="Filter shots before date (YYYY-MM-DD).")
@click.option("--min-shots", default=None, type=int, help="Minimum shots required for a distance.")
@click.option("--json",   "as_json", is_flag=True, help="Output raw JSON.")
def clubs(after: str, before: str, min_shots: int, as_json: bool):
    """Show smart club distances (AI-filtered carry distances per club)."""
    client = _get_client()

    with console.status("Fetching club distances\u2026"):
        data = client.clubs.smart_distances(
            num_shots=min_shots,
            start_date=after,
            end_date=before,
        )
        # Fetch the user's bag to map clubId → clubType + make/model.
        # The smart distances endpoint only returns clubId (bag slot).
        bag_clubs: dict[int, dict] = {}
        try:
            profile = client._http.get(f"/users/{client.user_id}")
            bag_id = profile.get("bagId")
            if bag_id:
                bag = client.clubs.bag(str(bag_id))
                for bc in bag.get("clubs", []):
                    bag_clubs[bc["clubId"]] = bc
        except Exception:
            pass

    if as_json:
        _output_json(data)
        return

    # Filter out deleted clubs (old clubs replaced in the bag)
    if bag_clubs:
        data = [
            c for c in data
            if bag_clubs.get(c.get("clubId"), {}).get("isDeleted") != "T"
        ]

    if not data:
        console.print("[dim]No club data found.[/dim]")
        return

    from arccos.resources.clubs import CLUB_TYPE_NAMES

    table = Table(
        box=box.ROUNDED,
        header_style="bold cyan",
        title="[bold]Smart Club Distances[/bold]",
    )
    table.add_column("Club", style="white bold")
    table.add_column("Model", style="dim")
    table.add_column("Smart", justify="right", style="green bold")
    table.add_column("Longest", justify="right")
    table.add_column("Range", justify="right", style="dim")
    table.add_column("Shots", justify="right", style="dim")

    for c in data:
        # Resolve: clubId (bag slot) → clubType → display name
        club_id = c.get("clubId")
        bag_club = bag_clubs.get(club_id, {})
        club_type = bag_club.get("clubType", club_id)
        name = CLUB_TYPE_NAMES.get(club_type, f"#{club_id}")

        # Make + model from bag data
        make = bag_club.get("clubMakeOther", "")
        model_name = bag_club.get("clubModelOther", "")
        club_model = f"{make} {model_name}".strip() if make or model_name else ""

        # Smart distance: may be a dict {"distance": X, "unit": "yd"}
        smart_raw = c.get("smartDistance")
        if isinstance(smart_raw, dict):
            smart = f"{smart_raw['distance']:.0f}y"
        elif smart_raw is not None:
            smart = f"{smart_raw}y"
        else:
            smart = "\u2014"

        # Longest
        longest_raw = c.get("longest")
        longest = f"{longest_raw['distance']:.0f}y" if isinstance(longest_raw, dict) else "\u2014"

        # Range
        range_raw = c.get("range")
        if isinstance(range_raw, dict):
            rng = (
                f"{range_raw['low']:.0f}"
                f"\u2013{range_raw['high']:.0f}y"
            )
        else:
            rng = "\u2014"

        # Shot count
        usage = c.get("usage", {})
        shots = str(usage.get("count", "\u2014")) if isinstance(usage, dict) else "\u2014"

        table.add_row(name, club_model, smart, longest, rng, shots)

    console.print(table)
    console.print("[dim]Smart distance = average with outlier shots removed.[/dim]")


# ---------------------------------------------------------------------------
# pace
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--limit", "-n", default=200, show_default=True, help="Max rounds to analyse.")
@click.option("--json",  "as_json", is_flag=True, help="Output raw JSON.")
def pace(limit: int, as_json: bool):
    """Show pace of play (round duration) by course."""
    client = _get_client()

    with console.status(f"Fetching up to {limit} rounds and course names\u2026"):
        data = client.rounds.pace_of_play(
            rounds=client.rounds.list(limit=limit)
        )

    if as_json:
        _output_json(data)
        return

    n_rounds  = len(data["rounds"])
    n_courses = len(data["course_averages"])

    avg = data['overall_avg_display']
    console.print(
        f"\n[bold]Pace of Play[/bold] \u2014 "
        f"[dim]{n_rounds} rounds across {n_courses} courses[/dim]"
        f"   Overall avg: [bold cyan]{avg}[/bold cyan]\n"
    )

    table = Table(
        box=box.ROUNDED,
        header_style="bold cyan",
        title="[bold]By Course[/bold] (slowest first)",
    )
    table.add_column("",        width=2)
    table.add_column("Avg Time", justify="right", style="bold")
    table.add_column("Course",   style="white")
    table.add_column("Rounds",   justify="right", style="dim")

    for c in data["course_averages"]:
        flag = _flag(c["avg_minutes"])
        table.add_row(flag, c["avg_display"], c["course"], str(c["rounds"]))

    console.print(table)

    console.print("\n[bold]Recent Rounds:[/bold]")
    recent_table = Table(box=box.SIMPLE, show_header=True, header_style="dim")
    recent_table.add_column("",       width=2)
    recent_table.add_column("Date",   style="dim")
    recent_table.add_column("Time",   justify="right", style="bold")
    recent_table.add_column("Score",  justify="right")
    recent_table.add_column("Course")

    for r in data["rounds"][:10]:
        flag = _flag(r["duration_minutes"])
        recent_table.add_row(
            flag, r["date"], r["duration_display"],
            str(r["score"] or "\u2014"), r["course"],
        )

    console.print(recent_table)
    console.print("[dim]\U0001f534 >5h  \U0001f7e1 4.5\u20135h  \U0001f7e2 <4.5h[/dim]")


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("round_ids", nargs=-1, type=int, required=False)
@click.option("--latest", "-l", is_flag=True, help="Use your most recent round.")
@click.option("--json",   "as_json", is_flag=True, help="Output raw JSON.")
def stats(round_ids: tuple, latest: bool, as_json: bool):
    """
    Show strokes gained (SGA) analysis.

    Pass one or more ROUND_IDs, or use --latest for your most recent round.

    \b
    Examples:
      arccos stats --latest
      arccos stats 26685289
      arccos stats 26685289 26627133
    """
    client = _get_client()

    if not round_ids and not latest:
        console.print("[yellow]Pass one or more round IDs, or use --latest.[/yellow]")
        console.print("  arccos stats --latest")
        console.print("  arccos stats 26685289")
        sys.exit(1)

    if latest:
        with console.status("Fetching latest round\u2026"):
            rd = client.rounds.list(limit=1)
        if not rd:
            err_console.print("[red]No rounds found.[/red]")
            sys.exit(1)
        round_ids = (rd[0]["roundId"],)
        date = rd[0].get("startTime", "")[:10]
        console.print(f"Using round [dim]{round_ids[0]}[/dim] ({date})")

    from arccos.exceptions import ArccosError

    try:
        with console.status(f"Fetching strokes gained for {len(round_ids)} round(s)\u2026"):
            data = client.stats.strokes_gained(list(round_ids))
    except ArccosError as e:
        err_console.print(f"[red]SGA fetch failed:[/red] {e}")
        err_console.print("[dim]The SGA endpoint may not be available for all accounts.[/dim]")
        sys.exit(1)

    if as_json:
        _output_json(data)
        return

    # Pretty print known SGA fields
    SGA_LABELS = {
        "overallSga":  ("Overall",      "Total strokes gained vs. scratch"),
        "drivingSga":  ("Driving",      "Off the tee"),
        "approachSga": ("Approach",     "Approach shots to the green"),
        "shortSga":    ("Short Game",   "Chipping and pitching"),
        "puttingSga":  ("Putting",      "On the green"),
    }

    table = Table(
        box=box.ROUNDED,
        header_style="bold cyan",
        title="[bold]Strokes Gained Analysis[/bold]",
    )
    table.add_column("Category",    style="white bold")
    table.add_column("SG",          justify="right", style="bold", no_wrap=True)
    table.add_column("Description", style="dim")

    for key, (label, desc) in SGA_LABELS.items():
        val = data.get(key)
        if val is None:
            continue
        color = "green" if val >= 0 else "red"
        table.add_row(label, f"[{color}]{val:+.2f}[/{color}]", desc)

    console.print(table)
    console.print("[dim]Positive = better than scratch. Negative = worse.[/dim]")

    # Dump any extra keys not in our label map
    extras = {k: v for k, v in data.items() if k not in SGA_LABELS and isinstance(v, (int, float))}
    if extras:
        console.print("\n[dim]Other data:[/dim]")
        for k, v in extras.items():
            console.print(f"  [dim]{k}:[/dim] {v}")


# ---------------------------------------------------------------------------
# courses
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def courses(as_json: bool):
    """List courses you have played."""
    client = _get_client()

    with console.status("Fetching courses\u2026"):
        data = client.courses.played()

    if as_json:
        _output_json(data)
        return

    if not data:
        console.print("[dim]No courses found.[/dim]")
        return

    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        title=f"[bold]Courses Played[/bold] [dim]({len(data)} total)[/dim]",
    )
    table.add_column("Course Name",   style="white bold")
    table.add_column("City")
    table.add_column("State")
    table.add_column("Rounds Played", justify="right")
    table.add_column("Course ID",     justify="right", style="dim")

    for c in data:
        name   = c.get("courseName") or c.get("name") or "\u2014"
        city   = c.get("city") or c.get("courseCity") or "\u2014"
        state  = c.get("state") or c.get("courseState") or "\u2014"
        played = str(c.get("roundsPlayed") or c.get("roundCount") or "\u2014")
        cid    = str(c.get("courseId") or c.get("id") or "\u2014")
        table.add_row(name, city, state, played, cid)

    console.print(table)


# ---------------------------------------------------------------------------
# round
# ---------------------------------------------------------------------------

@cli.command(name="round")
@click.argument("round_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def round_detail(round_id: int, as_json: bool):
    """Show hole-by-hole detail for a single round."""
    client = _get_client()

    with console.status(f"Fetching round {round_id}\u2026"):
        meta = client.rounds.get(round_id)
        # Try to get par data from the course
        par_map: dict[int, int] = {}
        course_id = meta.get("courseId")
        if course_id:
            try:
                course = client.courses.get(course_id)
                for h in course.get("holes", []):
                    par_map[h["holeId"]] = h.get("par", 0)
            except Exception:
                pass

    if as_json:
        _output_json(meta)
        return

    # --- Summary panel ---
    date = meta.get("startTime", "\u2014")[:10] if meta.get("startTime") else "\u2014"
    score = meta.get("noOfShots", "\u2014")
    course_name = meta.get("courseName") or str(meta.get("courseId", "\u2014"))
    n_holes = meta.get("noOfHoles", "\u2014")
    over_under = meta.get("overUnder")
    ou_str = f" ({over_under:+d})" if over_under is not None else ""

    summary = (
        f"[bold]Date:[/bold]   {date}\n"
        f"[bold]Course:[/bold] {course_name}\n"
        f"[bold]Score:[/bold]  {score}{ou_str}\n"
        f"[bold]Holes:[/bold]  {n_holes}"
    )
    console.print(Panel(
        summary,
        title=f"[bold cyan]Round {round_id}[/bold cyan]",
        expand=False,
    ))

    # Holes are embedded in the round response
    holes = meta.get("holes", [])
    if not holes:
        console.print("[dim]No hole data available.[/dim]")
        return

    has_par = bool(par_map)
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        title="[bold]Hole-by-Hole[/bold]",
    )
    table.add_column("Hole", justify="right")
    if has_par:
        table.add_column("Par", justify="right", style="dim")
    table.add_column("Score", justify="right", style="bold")
    table.add_column("Putts", justify="right")
    table.add_column("FIR", justify="center")
    table.add_column("GIR", justify="center")

    total_score = 0
    total_putts = 0
    total_par = 0
    for h in holes:
        hole_num = h.get("holeId", 0)
        sc = h.get("noOfShots")
        putts = h.get("putts")
        fir = h.get("isFairWay", "\u2014")
        gir = h.get("isGir", "\u2014")
        par = par_map.get(hole_num)

        if sc is not None:
            color = _score_color(sc, par)
            score_str = f"[{color}]{sc}[/{color}]"
            total_score += sc
        else:
            score_str = "\u2014"

        putts_str = str(putts) if putts is not None else "\u2014"
        if putts is not None:
            total_putts += putts
        if par is not None:
            total_par += par

        # Color FIR/GIR: T=green, F=red
        if fir == "T":
            fir = "[green]T[/green]"
        elif fir == "F":
            fir = "[red]F[/red]"
        if gir == "T":
            gir = "[green]T[/green]"
        elif gir == "F":
            gir = "[red]F[/red]"

        row = [str(hole_num)]
        if has_par:
            row.append(str(par) if par else "\u2014")
        row.extend([score_str, putts_str, fir, gir])
        table.add_row(*row)

    # Totals row
    table.add_section()
    tot_row = ["[bold]Tot[/bold]"]
    if has_par:
        tot_row.append(f"[bold]{total_par}[/bold]" if total_par else "")
    tot_row.extend([
        f"[bold]{total_score}[/bold]",
        f"[bold]{total_putts}[/bold]",
        "", "",
    ])
    table.add_row(*tot_row)

    console.print(table)


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------

@cli.command()
def logout():
    """Clear cached credentials (~/.arccos_creds.json)."""
    from arccos.auth import DEFAULT_CREDS_PATH

    if DEFAULT_CREDS_PATH.exists():
        DEFAULT_CREDS_PATH.unlink()
        console.print(
            "[green]\u2713[/green] Credentials removed from "
            "[bold]~/.arccos_creds.json[/bold]"
        )
        console.print(
            "[dim]Note: Server-side tokens are not revoked. "
            "The access key remains valid until it expires (~180 days).[/dim]"
        )
    else:
        console.print("[dim]No cached credentials found.[/dim]")


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--limit",  "-n",  default=200,     show_default=True, help="Max rounds to export.")
@click.option("--format", "-f",  "fmt",
              type=click.Choice(["json", "csv", "ndjson"]), default="json",
              show_default=True, help="Output format.")
@click.option("--output", "-o",  default="-",     help="Output file path (default: stdout).")
@click.option("--detail", "-d",  is_flag=True,    help="Include hole-by-hole data per round.")
def export(limit: int, fmt: str, output: str, detail: bool):
    """Export round data to JSON or CSV."""
    import csv

    client = _get_client()

    with console.status(f"Fetching up to {limit} rounds\u2026"):
        data = client.rounds.list(limit=limit)

    if not data:
        err_console.print("[red]No rounds found.[/red]")
        sys.exit(1)

    if detail:
        with console.status(f"Fetching hole data for {len(data)} rounds\u2026"):
            for r in data:
                try:
                    full = client.rounds.get(r["roundId"])
                    r["holes"] = full.get("holes", [])
                except Exception:
                    r["holes"] = []

    def _write(out):
        if fmt == "json":
            json.dump(data, out, indent=2)
            out.write("\n")
        elif fmt == "ndjson":
            for r in data:
                out.write(json.dumps(r) + "\n")
        elif fmt == "csv":
            if data:
                keys = list(data[0].keys())
                # Exclude nested 'holes' from CSV (not tabular)
                keys = [k for k in keys if k != "holes"]
                writer = csv.DictWriter(
                    out, fieldnames=keys, extrasaction="ignore",
                )
                writer.writeheader()
                writer.writerows(data)

    if output == "-":
        _write(sys.stdout)
    else:
        out_path = os.path.realpath(output)
        with open(out_path, "w", newline="") as out:
            _write(out)
        console.print(
            f"[green]\u2713[/green] Exported {len(data)} rounds to [bold]{output}[/bold]"
        )


# ---------------------------------------------------------------------------
# bests
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def bests(as_json: bool):
    """Show your all-time personal bests."""
    client = _get_client()

    with console.status("Fetching personal bests\u2026"):
        data = client.stats.personal_bests()

    if as_json:
        _output_json(data)
        return

    if not data:
        console.print("[dim]No personal bests found.[/dim]")
        return

    # personal_bests can be a dict or list — normalize
    items = data if isinstance(data, list) else [data]

    table = Table(
        box=box.ROUNDED,
        header_style="bold cyan",
        title="[bold]Personal Bests[/bold]",
    )
    table.add_column("Record", style="white bold")
    table.add_column("Value", justify="right", style="green bold")
    table.add_column("Details", style="dim")

    BEST_LABELS = {
        "lowestScore":       ("Lowest Score",       lambda v: str(v)),
        "lowestScore9":      ("Lowest 9-Hole",      lambda v: str(v)),
        "longestDrive":      ("Longest Drive",      lambda v: f"{v:.0f}y" if v else str(v)),
        "fewestPutts":       ("Fewest Putts",       lambda v: str(v)),
        "fewestPutts9":      ("Fewest Putts (9)",   lambda v: str(v)),
        "mostBirdies":       ("Most Birdies",       lambda v: str(v)),
        "mostPars":          ("Most Pars",          lambda v: str(v)),
        "streakPar":         ("Longest Par Streak", lambda v: str(v)),
        "streakBirdie":      ("Birdie Streak",      lambda v: str(v)),
        "longestPutt":       ("Longest Putt",       lambda v: f"{v:.0f}ft" if v else str(v)),
    }

    for item in items:
        if not isinstance(item, dict):
            continue
        for key, (label, fmt_fn) in BEST_LABELS.items():
            val = item.get(key)
            if val is not None:
                detail = ""
                # Check for associated round/date info
                date_key = f"{key}Date"
                if item.get(date_key):
                    detail = str(item[date_key])[:10]
                table.add_row(label, fmt_fn(val), detail)

    # Also show any unlabeled numeric bests
    shown_keys = set(BEST_LABELS.keys())
    for item in items:
        if not isinstance(item, dict):
            continue
        for k, v in item.items():
            if k not in shown_keys and isinstance(v, (int, float)) and not k.endswith("Date"):
                shown_keys.add(k)
                table.add_row(k, str(v), "")

    if table.row_count == 0:
        console.print("[dim]No personal bests data available.[/dim]")
        return

    console.print(table)


# ---------------------------------------------------------------------------
# overview
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def overview(as_json: bool):
    """Show overall performance stats (GIR%, FIR%, putts/round)."""
    client = _get_client()

    with console.status("Fetching overall stats\u2026"):
        data = client.stats.overall_stats()

    if as_json:
        _output_json(data)
        return

    if not data:
        console.print("[dim]No stats available.[/dim]")
        return

    STAT_LABELS = {
        "girPct":         ("GIR %",            "%"),
        "firPct":         ("Fairway %",        "%"),
        "puttsPerRound":  ("Putts / Round",    ""),
        "puttsPerGir":    ("Putts / GIR",      ""),
        "scoringAvg":     ("Scoring Avg",      ""),
        "drivingDistance": ("Driving Distance", "y"),
        "scramblePct":    ("Scramble %",       "%"),
        "sandSavePct":    ("Sand Save %",      "%"),
        "penaltyPerRound": ("Penalties / Round", ""),
    }

    table = Table(
        box=box.ROUNDED,
        header_style="bold cyan",
        title="[bold]Overall Performance[/bold]",
    )
    table.add_column("Stat", style="white bold")
    table.add_column("Value", justify="right", style="bold")

    for key, (label, unit) in STAT_LABELS.items():
        val = data.get(key)
        if val is None:
            continue
        if unit == "%":
            table.add_row(label, f"{val:.1f}%")
        elif unit == "y":
            table.add_row(label, f"{val:.0f}y")
        else:
            table.add_row(label, f"{val:.1f}" if isinstance(val, float) else str(val))

    if table.row_count == 0:
        # Fallback: show all numeric fields
        for k, v in data.items():
            if isinstance(v, (int, float)):
                table.add_row(k, f"{v:.1f}" if isinstance(v, float) else str(v))

    console.print(table)


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--limit", "-n", default=20, show_default=True,
              help="Number of recent rounds to include.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def scoring(limit: int, as_json: bool):
    """Show scoring trend over recent rounds."""
    client = _get_client()

    with console.status(f"Fetching last {limit} rounds\u2026"):
        data = client.rounds.list(limit=limit)
        course_map = _build_course_map(client)

    if as_json:
        _output_json(data)
        return

    # Filter to 18-hole rounds with valid scores
    scored = [
        r for r in data
        if r.get("noOfShots") and r.get("noOfHoles") == 18
    ]

    if not scored:
        console.print("[dim]No 18-hole rounds found.[/dim]")
        return

    scores = [r["noOfShots"] for r in scored]
    avg = sum(scores) / len(scores)
    best = min(scores)
    worst = max(scores)

    # Summary
    console.print(
        f"\n[bold]Scoring Trend[/bold] [dim]({len(scored)} rounds)[/dim]\n"
        f"  Average: [bold cyan]{avg:.1f}[/bold cyan]    "
        f"Best: [bold green]{best}[/bold green]    "
        f"Worst: [bold red]{worst}[/bold red]\n"
    )

    # Sparkline-style trend table
    table = Table(
        box=box.ROUNDED,
        header_style="bold cyan",
        title="[bold]Recent Scores[/bold] (newest first)",
    )
    table.add_column("Date", style="white", no_wrap=True)
    table.add_column("Score", justify="right", style="bold")
    table.add_column("+/-", justify="right")
    table.add_column("Course")
    table.add_column("", width=12)  # bar

    for r in scored:
        date = r.get("startTime", "")[:10]
        sc = r["noOfShots"]
        ou = r.get("overUnder")
        ou_s = f"{ou:+d}" if ou is not None else ""
        cname = course_map.get(r.get("courseId"), "")

        # Visual bar: green below avg, red above
        bar_len = min(abs(sc - int(avg)), 10)
        color = "green" if sc <= avg else "red"
        bar = f"[{color}]{'█' * bar_len}[/{color}]"

        table.add_row(date, str(sc), ou_s, cname, bar)

    console.print(table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    cli()


if __name__ == "__main__":
    main()
