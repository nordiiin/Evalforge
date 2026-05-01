# EvalForge

A CLI that turns a Microsoft Copilot Studio solution export into a test set
ready to upload to Copilot Studio's Agent Evaluation feature.

> **Status:** Milestone 2. Parses a solution and generates happy-path test
> cases via the Anthropic API, with on-disk response caching. Other modes,
> OpenAI / Azure providers, and the validate / init commands land in M3 / M4.
> See [`SPEC.md`](SPEC.md).

## What's in the box

- `evalforge inspect` — parse a `.zip` solution export or directory of topic
  YAMLs and print rich tables of topics, knowledge sources, and tools.
- `evalforge generate` — generate a Copilot Studio Agent Evaluation CSV.
  Happy-path mode is implemented end-to-end against Anthropic's API; flags for
  topic filtering, count, seed, dry-run, and cache control are wired up.
- On-disk response cache — re-running the same command with the same seed
  costs zero tokens.
- LLM provider abstraction — Anthropic working; OpenAI and Azure stubbed
  behind a clear `NotImplementedError` until M3.

## Install (dev)

```bash
git clone https://github.com/nordiiin/evalforge.git
cd evalforge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=sk-ant-...
```

Once published, `pipx install evalforge` will be the supported install path.

## Usage

```bash
# Inspect what's in a solution
evalforge inspect path/to/MySolution.zip
evalforge inspect path/to/MySolution.zip --include-system --show-triggers

# Generate test cases (happy-path mode)
evalforge generate path/to/MySolution.zip -o test-set.csv --count 5

# Preview the LLM prompts without spending tokens
evalforge generate path/to/MySolution.zip -o /tmp/x.csv --dry-run

# Generate for specific topics only, with a seed for reproducibility
evalforge generate path/to/MySolution.zip -o test-set.csv \
    --topic "Order Status" --topic "Store Hours" \
    --count 10 --seed 42

# Bypass the cache (always re-generate)
evalforge generate path/to/MySolution.zip -o test-set.csv --no-cache

# Override the model (default is claude-opus-4-7)
evalforge generate path/to/MySolution.zip -o test-set.csv \
    --model claude-sonnet-4-6
```

## Working assumption: CSV column schema

> ⚠️ The exact column schema for Copilot Studio Agent Evaluation imports
> isn't in the public spec. M2 ships with the columns documented in
> `src/evalforge/csv_writer.py` as a working assumption — please verify
> against an actual Copilot Studio import (or paste the schema from the
> `copilot-studio-eval` skill referenced in `SPEC.md` §5) before relying on
> generated CSVs in production.

The four supported grader types are correct (`Compare meaning`, `Keyword
match`, `General quality`, `Exact match`); only the column header names need
confirmation.

## Tech choices

- **CLI:** [`typer`](https://typer.tiangolo.com/) + [`rich`](https://github.com/Textualize/rich).
- **YAML:** [`pyyaml`](https://pyyaml.org/) — only `safe_load` is needed.
- **LLM:** the official [`anthropic`](https://github.com/anthropics/anthropic-sdk-python) SDK.
  Default model is `claude-opus-4-7` with adaptive thinking, `effort: medium`,
  prompt caching on the system prompt, and strict tool-use for guaranteed
  JSON-shape outputs.
- **Build backend:** [`hatchling`](https://hatch.pypa.io/) with PEP 621
  metadata and a `src/` layout.
- **Tests:** [`pytest`](https://pytest.org/) — 60+ tests; LLM-free via a fake
  provider injected at the orchestration boundary.

## Cache layout

LLM responses are cached as JSON files keyed by SHA-256 of `(provider, model,
mode, count, seed, topic-fingerprint)`. Default location is
`~/.cache/evalforge/`; override with `--cache-dir` or `EVALFORGE_CACHE_DIR`.

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
