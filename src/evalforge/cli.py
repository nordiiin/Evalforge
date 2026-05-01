"""EvalForge command-line entry point."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from evalforge import __version__
from evalforge.cache import ResponseCache, default_cache_dir
from evalforge.csv_writer import write_csv
from evalforge.generation.generator import (
    SUPPORTED_MODES,
    generate_for_topic,
    resolve_referenced,
)
from evalforge.generation.prompt import build_happy_path_prompt
from evalforge.parser.models import Solution, Topic
from evalforge.parser.solution import parse_input
from evalforge.providers.factory import SUPPORTED_PROVIDERS, make_provider

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


@app.command()
def generate(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Path to a .zip solution export or a directory of topic YAMLs.",
    ),
    output: Path = typer.Option(
        ...,
        "-o",
        "--output",
        help="Path to write the generated CSV.",
    ),
    mode: str = typer.Option(
        "happy_path",
        "--mode",
        help=f"Generation mode. Currently supported: {sorted(SUPPORTED_MODES)}.",
    ),
    count: int = typer.Option(
        5,
        "--count",
        min=1,
        help="Number of test cases to generate per topic.",
    ),
    seed: int = typer.Option(
        None,
        "--seed",
        help="Seed for reproducible generation. Used in the cache key.",
    ),
    provider: str = typer.Option(
        "anthropic",
        "--provider",
        help=f"LLM provider. Working in M2: anthropic. Stubbed: openai, azure.",
    ),
    model: str = typer.Option(
        None,
        "--model",
        help="Provider model. Defaults to the provider's recommended model.",
    ),
    topic_filter: list[str] = typer.Option(
        None,
        "--topic",
        help="Only generate for topics whose name matches. Repeat for multiple.",
    ),
    include_system: bool = typer.Option(
        False,
        "--include-system",
        help="Generate for system topics (Greeting, Fallback, ...) too.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print the request that would be sent for each topic; spend no tokens.",
    ),
    cache_dir: Path = typer.Option(
        None,
        "--cache-dir",
        help="Directory to cache LLM responses. Default: $EVALFORGE_CACHE_DIR or ~/.cache/evalforge.",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Bypass the response cache (always re-generate).",
    ),
) -> None:
    """Generate a test set CSV from a Copilot Studio solution.

    The CSV column schema is a working assumption — see csv_writer.py for the
    note. Confirm the columns import cleanly before relying on production output.
    """
    if mode not in SUPPORTED_MODES:
        console.print(
            f"[red]Mode {mode!r} is not implemented yet.[/red] "
            f"M2 supports: {sorted(SUPPORTED_MODES)}. Other modes land in M3."
        )
        raise typer.Exit(code=2)
    if provider not in SUPPORTED_PROVIDERS:
        console.print(
            f"[red]Unknown provider {provider!r}.[/red] "
            f"Choose from: {', '.join(SUPPORTED_PROVIDERS)}."
        )
        raise typer.Exit(code=2)

    try:
        solution = parse_input(input_path)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to parse input:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    selected = _select_topics(
        solution.topics,
        topic_filter=topic_filter,
        include_system=include_system,
    )
    if not selected:
        console.print(
            "[red]No topics match the filter.[/red] "
            "Pass --include-system to include system topics, or relax --topic filters."
        )
        raise typer.Exit(code=1)

    if dry_run:
        _print_dry_run(solution, selected, mode=mode, count=count, seed=seed)
        return

    if provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(
            "[red]ANTHROPIC_API_KEY is not set.[/red] "
            "Export it before running generate, or pass --dry-run to preview without LLM calls."
        )
        raise typer.Exit(code=1)

    try:
        llm = make_provider(provider, model=model)
    except NotImplementedError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    cache = None
    if not no_cache:
        resolved_cache_dir = cache_dir or default_cache_dir()
        cache = ResponseCache(resolved_cache_dir)
        console.print(f"[dim]Cache directory: {resolved_cache_dir}[/dim]")

    all_cases = []
    cached_count = 0
    fresh_count = 0
    for topic in selected:
        knowledge_sources, tools = resolve_referenced(solution, topic)
        console.print(
            f"[bold]{topic.name}[/bold] — "
            f"requesting {count} case(s) ({len(knowledge_sources)} KS, {len(tools)} tool(s))"
        )
        cases, was_cached = generate_for_topic(
            topic=topic,
            knowledge_sources=knowledge_sources,
            tools=tools,
            provider=llm,
            mode=mode,
            count=count,
            seed=seed,
            cache=cache,
        )
        all_cases.extend(cases)
        if was_cached:
            cached_count += 1
            console.print(f"  [dim]→ {len(cases)} case(s) from cache[/dim]")
        else:
            fresh_count += 1
            console.print(f"  [green]→ {len(cases)} case(s) generated[/green]")

    try:
        write_csv(output, all_cases)
    except ValueError as exc:
        console.print(f"[red]CSV validation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print()
    console.print(
        f"[bold green]Wrote {len(all_cases)} case(s)[/bold green] across "
        f"{len(selected)} topic(s) to {output} "
        f"({cached_count} cached, {fresh_count} fresh)"
    )


def _select_topics(
    topics: list[Topic],
    *,
    topic_filter: list[str] | None,
    include_system: bool,
) -> list[Topic]:
    visible = [t for t in topics if include_system or not t.is_system]
    if not topic_filter:
        return visible
    wanted = {name.lower() for name in topic_filter}
    return [t for t in visible if t.name.lower() in wanted]


def _print_dry_run(
    solution: Solution,
    topics: list[Topic],
    *,
    mode: str,
    count: int,
    seed: int | None,
) -> None:
    console.print()
    console.print(f"[bold]Dry run[/bold] — mode={mode}, count={count}, seed={seed}")
    console.print(f"[bold]Source:[/bold] {solution.source}")
    if solution.bot_name:
        console.print(f"[bold]Bot:[/bold]    {solution.bot_name}")
    console.print(f"[bold]Topics:[/bold]  {len(topics)}")
    console.print()
    for topic in topics:
        knowledge_sources, tools = resolve_referenced(solution, topic)
        console.print(f"[bold cyan]── {topic.name} ──[/bold cyan]")
        prompt = build_happy_path_prompt(
            topic=topic,
            knowledge_sources=knowledge_sources,
            tools=tools,
            count=count,
            seed=seed,
        )
        console.print(prompt)
        console.print()


@app.command()
def validate(
    csv_path: Path = typer.Argument(  # noqa: ARG001
        ...,
        exists=True,
        readable=True,
        help="Path to an existing CSV to validate.",
    ),
) -> None:
    """Validate an existing CSV against the Copilot Studio import format. (M4)"""
    console.print(
        "[yellow]validate is a placeholder for M4 — not implemented yet.[/yellow]"
    )
    raise typer.Exit(code=2)


@app.command()
def init() -> None:
    """Drop a default config file in the current directory. (M4)"""
    console.print(
        "[yellow]init is a placeholder for M4 — not implemented yet.[/yellow]"
    )
    raise typer.Exit(code=2)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
