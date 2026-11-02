# Bark's fork of pytest-gremlins

This fork exists to carry fixes we need **while they are in review upstream**, not
to diverge from it. It is not a competing project, and nothing here is
Bark-specific: every change is a bug in pytest-gremlins that any user hits.

Upstream: <https://github.com/mikelane/pytest-gremlins> (MIT).

## Branches

- `main` — a plain mirror of upstream. Never commit here.
- `bark` — what we ship. `upstream/main` with every topic branch below merged in.
  Tagged `v<upstream>+bark.<n>` and pinned by tag from the consuming repo.
- one topic branch per fix — each is a single upstream pull request, and each
  stands alone against `upstream/main`.

## The fixes

| Branch | What it fixes |
| --- | --- |
| `fix/bounded-result-collection` | `as_completed` with no timeout lets one stuck mutant hang the run for ever, silently |
| `feat/json-report-selected-tests` | `selected_tests` on every result makes the JSON report large enough to exhaust the runner's memory |

### Retired, because upstream fixed them

Each was checked against upstream by running its own regression test there, or,
where upstream's internals had moved, by reading the code that replaced it.

| Branch | Upstream fix |
| --- | --- |
| `fix/async-lightweight-runner` | #544: every gremlin runs through pytest; the lightweight runner is gone |
| `fix/workspace-module-names` | #599, #607: instrumented modules resolve by import origin |
| `fix/instrumented-packages` | #599: package `__init__` gremlins import under the package name |
| `fix/parametrised-node-ids` | its regression tests pass on upstream unchanged |
| `fix/coverage-prescan-timeout` | `coverage_timeout` in `[tool.pytest-gremlins]` |
| `fix/coverage-prescan-core` | the pre-scan's rc file sets `core = ctrace` |
| `perf/test-hash-lookup` | test hashes are looked up by file in a dict |
| `fix/empty-coverage-map-is-fatal` | an empty map now falls back to the whole suite, which is slow but correct |

## Keeping it current

```bash
git fetch upstream
git checkout main && git merge --ff-only upstream/main && git push
# rebuild bark: upstream/main, then each topic branch merged in, then this file
# and the +bark.<n> version. Re-run the suite, re-tag.
```

Before carrying a topic branch forward, run its own regression test against plain
`upstream/main`. If it passes, upstream has fixed it: retire the branch and move
its row above. When the first table is empty, delete the fork and depend on PyPI
again.

## Before you push here

The full upstream gate, from `CONTRIBUTING.md`:

```bash
uv run pytest
uv run mypy src/pytest_gremlins
uv run ruff check . && uv run ruff format --check .
```
