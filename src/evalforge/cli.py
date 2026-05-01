"""EvalForge command-line entry point."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from evalforge import __version__
from evalforge.parser.models import Solution
from evalforge.parser.solution import parse_input

app = typer.Typer(
    name="evalforge",
    help="Generate Copilot Studio Agent Evaluation test sets from solution exports.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"evalforge {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the EvalForge version and exit.",
    ),
) -> None:
    """EvalForge — generate test sets for Copilot Studio Agent Evaluation."""


@app.command()
def inspect(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Path to a .zip solution export or a directory of topic YAMLs.",
    ),
    include_system: bool = typer.Option(
        False,
        "--include-system",
        help="Include system topics (Greeting, Fallback, On Error, ...).",
    ),
    show_triggers: bool = typer.Option(
        False,
        "--show-triggers",
        help="Print every trigger phrase under each topic.",
    ),
) -> None:
    """Parse a Copilot Studio solution and print its topics, knowledge, and tools."""
    try:
        solution = parse_input(input_path)
    except Exception as exc:  # noqa: BLE001 - user-facing error surface
        console.print(f"[red]Failed to parse input:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    _render(solution, include_system=include_system, show_triggers=show_triggers)


def _render(solution: Solution, *, include_system: bool, show_triggers: bool) -> None:
    console.print()
    console.print(f"[bold]Source:[/bold] {solution.source}")
    if solution.bot_name:
        console.print(f"[bold]Bot:[/bold]    {solution.bot_name}")
    console.print()

    visible_topics = [t for t in solution.topics if include_system or not t.is_system]
    hidden = len(solution.topics) - len(visible_topics)

    topics_table = Table(
        title=f"Topics ({len(visible_topics)})",
        title_justify="left",
        header_style="bold",
    )
    topics_table.add_column("Name")
    topics_table.add_column("Description", overflow="fold", max_width=60)
    topics_table.add_column("Triggers", justify="right")
    topics_table.add_column("Knowledge", justify="right")
    topics_table.add_column("Tools", justify="right")
    if visible_topics:
        for topic in sorted(visible_topics, key=lambda t: t.name.lower()):
            label = topic.name + (" [dim](system)[/dim]" if topic.is_system else "")
            topics_table.add_row(
                label,
                topic.description or "",
                str(len(topic.trigger_phrases)),
                str(len(topic.knowledge_source_ids)),
                str(len(topic.tool_ids)),
            )
    else:
        topics_table.add_row("[dim](none)[/dim]", "", "", "", "")
    console.print(topics_table)
    if hidden and not include_system:
        plural = "s" if hidden != 1 else ""
        console.print(
            f"[dim]({hidden} system topic{plural} hidden — pass "
            f"--include-system to show.)[/dim]"
        )
    console.print()

    if show_triggers and visible_topics:
        for topic in sorted(visible_topics, key=lambda t: t.name.lower()):
            console.print(f"[bold]{topic.name}[/bold] — triggers:")
            if topic.trigger_phrases:
                for phrase in topic.trigger_phrases:
                    console.print(f"  • {phrase}")
            else:
                console.print("  [dim](no trigger phrases)[/dim]")
            console.print()

    ks_table = Table(
        title=f"Knowledge sources ({len(solution.knowledge_sources)})",
        title_justify="left",
        header_style="bold",
    )
    ks_table.add_column("Name")
    ks_table.add_column("Kind")
    ks_table.add_column("Description", overflow="fold", max_width=60)
    if solution.knowledge_sources:
        for ks in sorted(solution.knowledge_sources, key=lambda k: k.name.lower()):
            ks_table.add_row(ks.name, ks.kind, ks.description or "")
    else:
        ks_table.add_row("[dim](none)[/dim]", "", "")
    console.print(ks_table)
    console.print()

    tools_table = Table(
        title=f"Tools ({len(solution.tools)})",
        title_justify="left",
        header_style="bold",
    )
    tools_table.add_column("Name")
    tools_table.add_column("Kind")
    tools_table.add_column("Description", overflow="fold", max_width=60)
    if solution.tools:
        for tool in sorted(solution.tools, key=lambda t: t.name.lower()):
            tools_table.add_row(tool.name, tool.kind, tool.description or "")
    else:
        tools_table.add_row("[dim](none)[/dim]", "", "")
    console.print(tools_table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
