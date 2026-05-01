# EvalForge

A CLI that turns a Microsoft Copilot Studio solution export into a test set
ready to upload to Copilot Studio's Agent Evaluation feature.

> **Status:** Milestone 3. All four generation modes (happy-path, edge case,
> hallucination, multi-turn) plus mixed allocation. Anthropic, OpenAI, and
> Azure OpenAI providers all working. Rule-based grader assigner. Polish
> (validate, init, packaging, README/demo) lands in M4.
> See [`SPEC.md`](SPEC.md).

## What's in the box

- `evalforge inspect` — parse a `.zip` solution export or directory of topic
  YAMLs and print rich tables of topics, knowledge sources, and tools.
- `evalforge generate` — generate a Copilot Studio Agent Evaluation CSV in
  any of five modes:
  - `happy_path` — realistic phrasings of the trigger intent.
  - `edge_case` — typos, partial info, wrong language, multi-intent.
  - `hallucination` — refusal-bait questions referencing data the agent
    can't have.
  - `multi_turn` — 2- or 3-turn conversations testing context retention.
  - `mixed` — splits the requested count 40/30/20/10 across the four.
- **Rule-based grader assigner.** The LLM suggests a grader per case
  (Compare meaning / Keyword match / General quality / Exact match). A
  rule-based assigner has the final say — promotes happy-path cases that
  match a topic message node verbatim to `Exact match`, demotes
  unsupported `Exact match` suggestions, softens keywordless hallucination
  cases to `General quality`, etc.
- **Three providers.**
  - Anthropic (`claude-opus-4-7`) — adaptive thinking, `effort: medium`,
    prompt caching, strict tool use.
  - OpenAI (`gpt-4o`) — `response_format` json_schema strict.
  - Azure OpenAI — same path as OpenAI, takes a deployment name as `--model`.
- **On-disk response cache.** Re-running the same command with the same
  seed costs zero tokens. Each sub-mode in a mixed run is cached separately.

## Install (dev)

```bash
git clone https://github.com/nordiiin/evalforge.git
cd evalforge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Set whichever API key matches your provider:

```bash
export ANTHROPIC_API_KEY=sk-ant-...        # for --provider anthropic (default)
export OPENAI_API_KEY=sk-...               # for --provider openai
export AZURE_OPENAI_API_KEY=...            # for --provider azure
export AZURE_OPENAI_ENDPOINT=https://...   # for --provider azure
```

Once published, `pipx install evalforge` will be the supported install path.

## Usage

```bash
# Inspect what's in a solution
evalforge inspect path/to/MySolution.zip
evalforge inspect path/to/MySolution.zip --include-system --show-triggers

# Generate happy-path cases (default mode)
evalforge generate path/to/MySolution.zip -o test-set.csv --count 5

# Mixed mode — 40/30/20/10 split across all four modes
evalforge generate path/to/MySolution.zip -o test-set.csv \
    --mode mixed --count 10 --seed 42

# Single mode focused on edge cases
evalforge generate path/to/MySolution.zip -o edge.csv --mode edge_case --count 5

# Switch provider
evalforge generate path/to/MySolution.zip -o test-set.csv \
    --provider openai --model gpt-4o

evalforge generate path/to/MySolution.zip -o test-set.csv \
    --provider azure --model my-gpt-4o-deployment \
    --endpoint https://my.openai.azure.com \
    --api-version 2024-08-01-preview

# Filter to specific topics, preview the prompts without spending tokens
evalforge generate path/to/MySolution.zip -o /tmp/x.csv \
    --topic "Order Status" --topic "Store Hours" \
    --mode mixed --count 20 --dry-run
```

## Working assumptions: CSV column schema and multi-turn format

> ⚠️  Two pieces of the output are working assumptions until verified
> against an actual Copilot Studio Agent Evaluation import:
>
> 1. **Column schema** — see `src/evalforge/csv_writer.py`. The four
>    grader labels (`Compare meaning`, `Keyword match`, `General quality`,
>    `Exact match`) are correct; only the column header names need
>    confirming.
> 2. **Multi-turn serialization** — see `src/evalforge/generation/modes/multi_turn.py`.
>    Multi-turn cases render the prior conversation as a transcript in the
>    `User input` column (`User: ...\n\nAgent: ...\n\nUser: ...`) and put
>    the agent's expected reply in `Expected response`.
>
> Both are isolated to one place each. To swap formats, edit those two
> files; nothing else in the pipeline is format-aware. The CLI prints a
> `⚠` warning whenever multi-turn rows are written to the CSV.

## Tech choices

- **CLI:** [`typer`](https://typer.tiangolo.com/) + [`rich`](https://github.com/Textualize/rich).
- **YAML:** [`pyyaml`](https://pyyaml.org/) — only `safe_load` is needed.
- **LLM SDKs:** [`anthropic`](https://github.com/anthropics/anthropic-sdk-python)
  and [`openai`](https://github.com/openai/openai-python). Both are imported
  lazily by the provider factory.
- **Build backend:** [`hatchling`](https://hatch.pypa.io/) with PEP 621
  metadata and a `src/` layout.
- **Tests:** [`pytest`](https://pytest.org/) — 90+ tests, all LLM-free.

## Architecture

```
src/evalforge/
├── parser/         — Copilot Studio solution / YAML parsing
├── generation/
│   ├── modes/      — one module per mode, registers a ModeSpec
│   │   ├── happy_path.py
│   │   ├── edge_case.py
│   │   ├── hallucination.py
│   │   └── multi_turn.py
│   ├── allocation.py  — 40/30/20/10 mixed split (largest-remainder)
│   ├── grader.py      — grader labels + rule-based assigner
│   ├── generator.py   — per-topic orchestration; dispatches to mode + cache
│   └── prompt.py      — mode-agnostic user-message builder
├── providers/      — anthropic_, openai_ (both OpenAI + Azure), factory
├── cache.py        — JSON-file cache keyed by SHA-256
├── csv_writer.py   — CSV writer + grader/keyword validation
└── cli.py          — typer commands
```

## Cache layout

LLM responses are cached as JSON files keyed by SHA-256 of `(provider,
model, mode, count, seed, topic-fingerprint)`. Default location is
`~/.cache/evalforge/`; override with `--cache-dir` or `EVALFORGE_CACHE_DIR`.
Each sub-mode in a mixed run is cached separately, so changing `--mode mixed
--count 10` to `--count 20` only re-generates the deltas.

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
