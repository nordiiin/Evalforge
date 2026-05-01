# EvalForge

A CLI that turns a Microsoft Copilot Studio solution export into a test set
ready to upload to Copilot Studio's Agent Evaluation feature.

> **Status:** Milestone 1. Parses a solution and prints a clean summary.
> Generation, validation, and CSV writing land in later milestones — see
> [`SPEC.md`](SPEC.md).

## What's in M1

- Parse a Copilot Studio `.zip` solution export, in-memory (no extraction).
- Parse a directory of topic YAML files, for when you're iterating on extracted
  topics.
- Print a tabular summary of topics, knowledge sources, and tools.
- Resolve references between topics and the knowledge sources / tools they call.
- Filter system topics by default; opt them in with `--include-system`.

## Install (dev)

```bash
git clone https://github.com/nordiiin/evalforge.git
cd evalforge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Once published, `pipx install evalforge` will be the supported install path.

## Usage

```bash
# Inspect a solution zip
evalforge inspect path/to/MySolution.zip

# Inspect a directory of topic YAMLs
evalforge inspect path/to/topics/

# Include greeting / fallback / on-error topics in the table
evalforge inspect path/to/MySolution.zip --include-system

# Print every trigger phrase under each topic
evalforge inspect path/to/MySolution.zip --show-triggers
```

Sample output:

```
Source: tests/fixtures/sample_solution
Bot:    EvalForge Test Bot

Topics (3)
┃ Name          ┃ Description                                   ┃ Triggers ┃ Knowledge ┃ Tools ┃
│ Order Status  │ Looks up the latest status of a customer ...  │     3    │     0     │   1   │
│ Product Info  │ Answers product questions using the catalog.  │     3    │     1     │   0   │
│ Store Hours   │ Tells the user our store opening hours.       │     3    │     0     │   0   │

Knowledge sources (1)
│ Product Catalog │ SharePoint │ SharePoint site containing all product specs and pricing. │

Tools (1)
│ Orders Lookup │ AISkill │ Looks up the status of a customer order in the orders system. │
```

## Tech choices

These are pragmatic defaults. Swap them later if there's a real reason to.

- **CLI:** [`typer`](https://typer.tiangolo.com/) — gives us auto-generated
  help, argument validation, and easy testing via `CliRunner`.
- **Tables / output:** [`rich`](https://github.com/Textualize/rich).
- **YAML:** [`pyyaml`](https://pyyaml.org/) — we only need `safe_load`, no
  round-tripping.
- **Build backend:** [`hatchling`](https://hatch.pypa.io/) — modern PEP 621
  metadata, simple `src/` layout.
- **Tests:** [`pytest`](https://pytest.org/).

## Running tests

```bash
pytest
```

## Out of scope (here as a forcing function)

- Running the eval — Copilot Studio owns this.
- Web UI / hosted service.
- Anything that calls a running agent.

See [`SPEC.md`](SPEC.md) for the full milestone plan.

## License

MIT.
