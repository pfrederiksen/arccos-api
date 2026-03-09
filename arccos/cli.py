"""
arccos CLI — pull your Arccos Golf data from the terminal.

Uses the reverse-engineered Arccos Golf API. Not affiliated with Arccos Golf LLC.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
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
        return "🔴"
    if minutes > 270:
        return "🟡"
    return "🟢"


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
      arccos handicap              Current handicap index
      arccos clubs                 Smart club distances
      arccos pace                  Pace of play by course
      arccos stats                 Strokes gained analysis

    \b
    Credentials are cached in ~/.arccos_creds.json after first login.
    Set ARCCOS_EMAIL and ARCCOS_PASSWORD to skip the prompts.
    """


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--email", envvar="ARCCOS_EMAIL", prompt="Arccos email", help="Your Arccos account email.")
@click.option("--password", envvar="ARCCOS_PASSWORD", prompt="Password", hide_input=True, help="Your Arccos password.")
def login(email: str, password: str):
    """Authenticate and save credentials to ~/.arccos_creds.json."""
    from arccos import ArccosClient
    from arccos.exceptions import ArccosAuthError

    with console.status("Logging in…"):
        try:
            client = ArccosClient(email=email, password=password)
        except ArccosAuthError as e:
            err_console.print(f"[red]Login failed:[/red] {e}")
            sys.exit(1)

    console.print(f"[green]✓[/green] Logged in as [bold]{client.email}[/bold]")
    console.print(f"  User ID: [dim]{client.user_id}[/dim]")
    console.print(f"  Credentials cached at [dim]~/.arccos_creds.json[/dim]")


# ---------------------------------------------------------------------------
# rounds
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--limit",  "-n", default=20,       show_default=True, help="Number of rounds to show.")
@click.option("--offset", "-o", default=0,         show_default=True, help="Pagination offset.")
@click.option("--after",  "-a", default=None,      help="Show rounds after date (YYYY-MM-DD).")
@click.option("--before", "-b", default=None,      help="Show rounds before date (YYYY-MM-DD).")
@click.option("--json",   "as_json", is_flag=True, help="Output raw JSON.")
def rounds(limit: int, offset: int, after: str, before: str, as_json: bool):
    """List your recent golf rounds."""
    client = _get_client()

    with console.status("Fetching rounds…"):
        data = client.rounds.list(
            limit=limit, offset=offset,
            after_date=after, before_date=before,
        )

    if as_json:
        _output_json(data)
        return

    if not data:
        console.print("[dim]No rounds found.[/dim]")
        return

    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        title=f"[bold]Rounds[/bold] [dim]({len(data)} shown)[/dim]",
    )
    table.add_column("Date",      style="white",  no_wrap=True)
    table.add_column("Score",     style="bold",   justify="right")
    table.add_column("Holes",     justify="right")
    table.add_column("Course ID", justify="right", style="dim")
    table.add_column("Round ID",  justify="right", style="dim")

    for r in data:
        date  = r.get("startTime", "")[:10]
        score = str(r.get("noOfShots", "—"))
        holes = str(r.get("noOfHoles", "—"))
        cid   = str(r.get("courseId", "—"))
        rid   = str(r.get("roundId", "—"))
        table.add_row(date, score, holes, cid, rid)

    console.print(table)


# ---------------------------------------------------------------------------
# handicap
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--history", "-H", is_flag=True,    help="Show handicap history instead of current.")
@click.option("--rounds",  "-n", default=20,       show_default=True, help="Rounds to include in history.")
@click.option("--json",   "as_json", is_flag=True, help="Output raw JSON.")
def handicap(history: bool, rounds: int, as_json: bool):
    """Show your current handicap index (or revision history)."""
    client = _get_client()

    with console.status("Fetching handicap…"):
        if history:
            data = client.handicap.history(rounds=rounds)
        else:
            data = client.handicap.current()

    if as_json:
        _output_json(data)
        return

    if not history:
        console.print(Panel(
            Text(str(data), justify="center"),
            title="[bold cyan]Handicap Index[/bold cyan]",
            expand=False,
        ))
    else:
        if not data:
            console.print("[dim]No handicap history found.[/dim]")
            return
        table = Table(box=box.ROUNDED, header_style="bold cyan", title="[bold]Handicap History[/bold]")
        first = data[0] if isinstance(data, list) else data
        if isinstance(first, dict):
            for key in first.keys():
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

    with console.status("Fetching club distances…"):
        data = client.clubs.smart_distances(
            num_shots=min_shots,
            start_date=after,
            end_date=before,
        )

    if as_json:
        _output_json(data)
        return

    if not data:
        console.print("[dim]No club data found.[/dim]")
        return

    table = Table(
        box=box.ROUNDED,
        header_style="bold cyan",
        title="[bold]Smart Club Distances[/bold]",
    )
    table.add_column("Club",           style="white bold")
    table.add_column("Smart Dist.",    justify="right", style="green bold")
    table.add_column("Avg Dist.",      justify="right")
    table.add_column("Shots Tracked",  justify="right", style="dim")

    for c in data:
        name  = c.get("clubType") or c.get("name") or "?"
        smart = c.get("smartDistance")
        avg   = c.get("averageDistance")
        shots = c.get("totalShots", "—")
        table.add_row(
            name,
            f"{smart}y" if smart is not None else "—",
            f"{avg}y"   if avg   is not None else "—",
            str(shots),
        )

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

    with console.status(f"Fetching up to {limit} rounds and course names…"):
        data = client.rounds.pace_of_play(
            rounds=client.rounds.list(limit=limit)
        )

    if as_json:
        _output_json(data)
        return

    n_rounds  = len(data["rounds"])
    n_courses = len(data["course_averages"])

    console.print(
        f"\n[bold]Pace of Play[/bold] — [dim]{n_rounds} rounds across {n_courses} courses[/dim]"
        f"   Overall avg: [bold cyan]{data['overall_avg_display']}[/bold cyan]\n"
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
            str(r["score"] or "—"), r["course"],
        )

    console.print(recent_table)
    console.print("[dim]🔴 >5h  🟡 4.5–5h  🟢 <4.5h[/dim]")


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
        with console.status("Fetching latest round…"):
            rd = client.rounds.list(limit=1)
        if not rd:
            err_console.print("[red]No rounds found.[/red]")
            sys.exit(1)
        round_ids = (rd[0]["roundId"],)
        date = rd[0].get("startTime", "")[:10]
        console.print(f"Using round [dim]{round_ids[0]}[/dim] ({date})")

    with console.status(f"Fetching strokes gained for {len(round_ids)} round(s)…"):
        data = client.stats.strokes_gained(list(round_ids))

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
# export
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--limit",  "-n",  default=200,     show_default=True, help="Max rounds to export.")
@click.option("--format", "-f",  "fmt",
              type=click.Choice(["json", "csv", "ndjson"]), default="json",
              show_default=True, help="Output format.")
@click.option("--output", "-o",  default="-",     help="Output file path (default: stdout).")
def export(limit: int, fmt: str, output: str):
    """Export round data to JSON or CSV."""
    import csv
    import io

    client = _get_client()

    with console.status(f"Fetching up to {limit} rounds…"):
        data = client.rounds.list(limit=limit)

    if not data:
        err_console.print("[red]No rounds found.[/red]")
        sys.exit(1)

    out = open(output, "w", newline="") if output != "-" else sys.stdout

    try:
        if fmt == "json":
            json.dump(data, out, indent=2)
            out.write("\n")
        elif fmt == "ndjson":
            for r in data:
                out.write(json.dumps(r) + "\n")
        elif fmt == "csv":
            if data:
                writer = csv.DictWriter(out, fieldnames=data[0].keys(), extrasaction="ignore")
                writer.writeheader()
                writer.writerows(data)
    finally:
        if output != "-":
            out.close()
            console.print(f"[green]✓[/green] Exported {len(data)} rounds to [bold]{output}[/bold]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    cli()


if __name__ == "__main__":
    main()
