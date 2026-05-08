# Phase 7 — Niche Pulse (time-sensitive sidecar)

This phase surfaces trending themes, regulatory shifts, competitor news, and
trending negative candidates from news published in the last 7 days. It is
deliberately a **sidecar** — niche-pulse data does NOT merge into
`keywords.json` because it has a different lifecycle (1-30 day shelf life vs
evergreen).

## When to run it

Phase 7 is optional. Recommended cadence:
- **Per campaign brief** — once during initial research
- **Weekly** — re-run only Phase 7 against an existing run folder to refresh

It's safe to skip if the operator only wants evergreen keyword research.

## Step 27: Confirm operator wants niche pulse

Ask the operator:

> "Run Phase 7 (Niche Pulse) — fetch news from the last 7 days to surface
> trending themes, regulatory shifts, and competitor news? Costs ~12 Serper
> credits + ~12 Tavily credits."

If yes → continue. If no → skip to next phase or stop.

## Step 28: Fetch news

Reuse the same seed keywords generated in Step 6. Pass them to `pulse_fetch.py`:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/pulse_fetch.py" \
  --run-dir "{run_dir}" \
  --seeds {seed1} {seed2} ... \
  --gl {gl} \
  --hl {hl} \
  --days 7 \
  --num 10
```

Parse stdout JSON. Surface `serper_news_count`, `tavily_news_count`,
`serper_credits_used`, `tavily_credits_used` to the operator.

Exit code handling:
- **Exit 0:** continue to Step 29.
- **Exit 2:** Tavily quota exceeded — partial data still written. Ask operator
  to continue with partial pulse or stop.
- **Exit 3:** auth or fatal IO. Stop and surface stderr.

**Do not advance until both `raw/serper-news.json` and `raw/tavily-news.json`
exist.**

## Step 29: Synthesize the pulse

Optional: include known competitor brand names so they're flagged in the
competitor_news section.

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/pulse_synth.py" \
  --run-dir "{run_dir}" \
  --brand "MD Now" --brand "Dr. G" --brand "Complete Care"
```

Parse stdout JSON. Confirm `niche-pulse.json` exists at the run root and
surface counts to operator.

## Step 30: Re-render the report

`render_report.py` automatically picks up `niche-pulse.json` when re-run, so
just re-run it:

```bash
uv run --with python-slugify --with python-dotenv --with tabulate \
  "${CLAUDE_SKILL_DIR}/scripts/render_report.py" --run-dir "{run_dir}"
```

The report (md, json, html) will now include a **Niche Pulse** section
containing trending themes, regulatory alerts, competitor news, and trending
negative candidates.

**STOP.** Phase 7 is done. The operator can re-run Phase 7 against this run
folder weekly to refresh the pulse without re-running Phases 2-6.

## Anti-patterns

- **Do not merge niche-pulse keywords into `keywords.json`.** Different
  lifecycle (days-weeks vs evergreen). Polluting the main ranking with
  short-lived terms corrupts the source-diversity signal.
- **Do not bid on niche-pulse keywords without operator review.** Trending
  themes can be temporary noise (one news cycle, no commercial intent).
  Treat the section as opportunity discovery, not a campaign-ready list.
- **Do not skip Step 27.** The operator should always opt in — niche pulse
  is sometimes irrelevant for the brief and consumes paid API credits.
- **Do not use `--days` > 30.** Beyond 30 days the "trending" framing breaks
  down and the data is no longer time-sensitive in any useful way.
