# EvalForge — Specification

> A CLI that generates Microsoft Copilot Studio Agent Evaluation test sets from a Copilot Studio solution export. Open-source. Single distributable command.

-----

## 0. How to use this spec with Claude Code

This spec describes **what** to build, not **how**. Choose your own libraries, project layout, and tooling — make defensible choices and document them in the README.

The spec is organized as **milestones**. Tell Claude Code:

> “Read SPEC.md. Implement Milestone 1 only. Stop and let me review before starting Milestone 2.”

Each milestone has explicit acceptance criteria. Don’t skip ahead.

-----

## 1. Product goal

Given a Copilot Studio solution export (or a directory of topic YAML files), produce a CSV file ready to import into Copilot Studio’s Agent Evaluation feature, containing realistic test cases with appropriate grader assignments.

The user runs one command and gets back a usable test set. They review, edit if needed, and upload to Copilot Studio. EvalForge does not run the eval — Copilot Studio does.

-----

## 2. Constraints

- **Language:** Python.
- Everything else (CLI framework, YAML parser, LLM client, packaging, distribution) is your call. Pick modern, well-maintained tools and explain the choice in a short ADR or in the README.

-----

## 3. CLI surface (the user contract)

The product is defined by what the user can type. Implement these capabilities; name the commands sensibly.

**Primary capability: generate a test set**

- Input: a Copilot Studio solution `.zip` export, **or** a directory of topic YAML files
- Output: a CSV file ready to import into Copilot Studio Agent Evaluation
- User can choose the **generation mode** (see §6)
- User can choose **how many cases per topic**
- User can **filter** which topics to generate for
- User can pick the **LLM provider** and model
- User can run a **dry-run** that shows what would be generated without spending tokens
- User can supply a **seed** for reproducible generation

**Secondary capabilities (nice to have, can ship in M3+):**

- Inspect: parse the input and print the topics, knowledge sources, and tools as a readable summary — useful for debugging
- Validate: take an existing CSV and verify it conforms to Copilot Studio’s eval import format
- Init: drop a default config file in the current directory

A configuration file (TOML or similar) lets users pin defaults so they don’t retype flags. Per-invocation flags override the file.

-----

## 4. Input contract

### Solution `.zip` exports

Copilot Studio solution exports are standard Power Platform solution archives. They contain a `bots/<bot>/botcomponents/<topic>/topic.yaml` structure plus knowledge source and tool metadata. Parse these in-memory; don’t write to disk.

For each topic, capture:

- ID, name, description
- Trigger phrases / trigger intent
- Attached knowledge sources (with their descriptions)
- Attached tools (with their descriptions)
- The raw YAML — preserved as context for the LLM

Filter out system topics by default (the user can opt them in).

### Topic YAML directories

If the input is a directory, treat each `*.yaml` as a topic. Useful when a developer is iterating on extracted topics.

-----

## 5. Output contract: Copilot Studio eval CSV

> ⚠️ **The canonical CSV column schema lives in Philip’s existing `copilot-studio-eval` skill.** Read that skill before implementing the writer. Do not invent the format from this document.

What this spec *can* tell you:

- Copilot Studio supports four grader types: **Compare meaning**, **Keyword match**, **General quality**, **Exact match**
- Each row is a test case: a user question, an expected response, a grader, and grader-specific fields (keywords for `Keyword match`, etc.)
- The output must import cleanly into Copilot Studio without manual fixes — encoding, escaping, header row all need to be exactly right

Validate every generated row before writing: empty questions, missing keywords for `Keyword match`, malformed multi-turn payloads should all be caught and either fixed or surfaced as errors.

-----

## 6. Generation modes

Each mode produces a different *kind* of test case. The interesting work in EvalForge is making these modes produce genuinely useful tests, not just paraphrases of trigger phrases.

**Happy-path** — Realistic user phrasings of the trigger intent. Expected responses align with the topic’s message nodes or its attached knowledge. Default grader: `Compare meaning`.

**Edge cases** — Misspellings, partial information, wrong language (Swedish question to English-only topic), multi-intent inputs. Default grader: `Compare meaning` or `General quality`.

**Hallucination bait** — Questions that *look* like they belong to the topic but reference data the agent shouldn’t have (“what’s the price of [SKU that doesn’t exist]”). Tests grounding and refusal. Default grader: `Keyword match` against expected refusal phrasing, or `General quality` with explicit refusal guidance.

**Multi-turn** — Two- or three-turn conversations testing context retention and clarification flow. Format depends on what Copilot Studio’s eval CSV supports — verify before implementing.

**Mixed** — Calls all four with proportional allocation (suggested: 40/30/20/10 for happy/edge/hallucination/multi-turn).

The grader assignment can be suggested by the generator and overridden by a rule-based assigner — open-ended answers default to `Compare meaning`, fixed strings default to `Exact match`, etc.

-----

## 7. LLM provider abstraction

The user provides an API key. EvalForge calls an LLM to generate cases. **Default provider is Anthropic; OpenAI and Azure OpenAI must also work.** Use structured output (tool use / JSON schema) so the model returns typed test cases — never parse free text.

Cache LLM responses on disk, keyed by a hash of the input topic + mode + count + seed. Re-running with identical inputs should cost zero tokens.

-----

## 8. Quality bar

A v1 release is acceptable when:

- Running EvalForge against a real Copilot Studio solution produces a CSV that imports cleanly without manual fixes
- A 20-row spot check by Philip on the output shows test cases he’d actually use — not LLM-paraphrased tautologies
- The same input + same seed produces the same output (deterministic given seed)
- A user can install via `pipx` (or equivalent) on macOS and Linux and run the quickstart in under five minutes

-----

## 9. Milestones

### M1 — Parsing + inspect

**Goal:** Prove we can read Copilot Studio exports.

Acceptance:

- A single command parses a `.zip` solution export and prints a clean table of topics, knowledge sources, and tools
- Same command works for a directory of YAML files
- Tests cover at least one anonymized fixture solution (Philip provides)

### M2 — Single mode end-to-end

**Goal:** A real CSV that imports into Copilot Studio.

Acceptance:

- Generate command works for one mode (happy-path)
- Output imports cleanly into Copilot Studio Agent Evaluation — Philip verifies manually
- LLM provider abstraction in place (Anthropic working; others stubbed)
- Response caching works (re-runs are free)

### M3 — All modes + grader assignment

**Goal:** Mixed-mode generation that’s actually useful.

Acceptance:

- All four modes implemented plus mixed allocation
- Grader assigner produces sensible choices on a 50-row sample (Philip spot-checks)
- OpenAI and Azure OpenAI providers working
- Topic filtering, case count, seed flags work

### M4 — Polish + release

**Goal:** Public launch.

Acceptance:

- README answers “what is this, why use it, install it, run it” in the first 100 words
- Inspect, validate, and init commands ship
- Published to PyPI via CI on tag
- Repo has license (MIT), contributing guide, and a 30-second terminal demo (asciinema GIF)

-----

## 10. Out of scope (don’t build)

- Running the eval. Copilot Studio owns this.
- A web UI or hosted service.
- Direct integration with Dataverse or live Copilot Studio APIs.
- Custom grader types beyond the four Copilot Studio supports.
- Power Automate flow generation.
- Anything that calls a running agent.

These belong to CSObserve. If a feature feels like it does, stop.
