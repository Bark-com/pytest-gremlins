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
| `fix/workspace-module-names` | Module names derived from rootdir are unimportable in a workspace, so no mutation activates and every gremlin reads as survived |
| `fix/instrumented-packages` | An instrumented `__init__.py` stops being a package, so imports beneath it fail |
| `fix/async-lightweight-runner` | The lightweight runner discards coroutines, so `async def` tests never run and their gremlins read as survived |
| `fix/parametrised-node-ids` | Node-ID normalisation strips uppercase parametrisation IDs such as `[GB]`, breaking test selection |
| `fix/coverage-prescan-timeout` | The coverage pre-scan's 120s cap is not configurable |
| `fix/coverage-prescan-core` | `COVERAGE_CORE=sysmon` cannot record dynamic contexts, so the per-test map comes back incomplete |
| `fix/empty-coverage-map-is-fatal` | An empty coverage map warns and then reports a mutation score measured against nothing |
| `perf/test-hash-lookup` | A per-mutant linear scan is quadratic in (gremlins x test files) |
| `feat/json-report-selected-tests` | `selected_tests` on every result makes the JSON report large enough to OOM the runner |
| `fix/bounded-result-collection` | `as_completed` with no timeout lets one stuck mutant hang the run for ever, silently |

## Keeping it current

```bash
git fetch upstream
git checkout main && git merge --ff-only upstream/main && git push
git checkout bark && git rebase upstream/main   # resolve, re-run the suite, re-tag
```

When an upstream release contains a fix, drop that topic branch from `bark` and
delete its row above. When the table is empty, delete the fork and depend on
PyPI again.

## Before you push here

The full upstream gate, from `CONTRIBUTING.md`:

```bash
uv run pytest
uv run mypy src/pytest_gremlins
uv run ruff check . && uv run ruff format --check .
```
