# Running the Tests

Phase 1 + Phase 2 tests use ad-hoc `uv run --with` invocation (no pyproject.toml required):

```bash
uv run --with pytest --with python-dotenv --with python-slugify \
  --with respx --with httpx --with httpx-retries \
  --with tavily-python --with inflect \
  pytest .claude/skills/google-ad-research/scripts/tests/ -x
```

Run a single test file:
```bash
uv run --with pytest --with respx --with httpx --with httpx-retries \
  pytest .claude/skills/google-ad-research/scripts/tests/test_serp_fetch.py -x -v
```

All tests are unit tests with mocked HTTP — no live API keys needed. Full suite runs in ~15 seconds.
Promotion to pyproject.toml is deferred to Phase 6.
