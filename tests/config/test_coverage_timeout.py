"""The coverage pre-scan timeout is configurable.

Coverage-guided test selection rests on one sub-run: the whole selected suite,
once, under per-test coverage contexts. Its timeout is a fixed 120 seconds, and
on expiry the collection returns an empty map. A suite that legitimately takes
longer than two minutes under coverage instrumentation therefore loses test
selection entirely — and a suite grows into that limit rather than hitting it
on day one.

The cap is a guard against a hung sub-run, not a budget, so a project has to be
able to set it against its own suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pytest_gremlins.config import (
    DEFAULT_COVERAGE_TIMEOUT_SECONDS,
    GremlinConfig,
    load_config,
    merge_configs,
)


def _write_pyproject(directory: Path, body: str) -> Path:
    (directory / 'pyproject.toml').write_text(f'[tool.pytest-gremlins]\n{body}\n')
    return directory


@pytest.mark.medium
class DescribeCoverageTimeoutFromPyproject:
    def it_reads_the_configured_value(self, tmp_path: Path):
        config = load_config(_write_pyproject(tmp_path, 'coverage_timeout = 600'))
        assert config.coverage_timeout == 600

    def it_defaults_to_unset_when_absent(self, tmp_path: Path):
        config = load_config(_write_pyproject(tmp_path, 'cache = true'))
        assert config.coverage_timeout is None

    @pytest.mark.parametrize('bad_value', ['0', '-1', 'true', '"600"'])
    def it_rejects_a_value_that_is_not_a_positive_integer(self, tmp_path: Path, bad_value: str):
        with pytest.raises(ValueError, match='coverage_timeout'):
            load_config(_write_pyproject(tmp_path, f'coverage_timeout = {bad_value}'))


@pytest.mark.small
class DescribeCoverageTimeoutPrecedence:
    def it_prefers_the_cli_value_over_the_file_value(self):
        merged = merge_configs(GremlinConfig(coverage_timeout=600), cli_coverage_timeout=900)
        assert merged.coverage_timeout == 900

    def it_keeps_the_file_value_when_the_cli_is_silent(self):
        merged = merge_configs(GremlinConfig(coverage_timeout=600))
        assert merged.coverage_timeout == 600

    def it_leaves_the_value_unset_when_neither_is_given(self):
        assert merge_configs(GremlinConfig()).coverage_timeout is None


@pytest.mark.small
class DescribeCoverageTimeoutDefault:
    def it_keeps_the_historical_two_minute_cap(self):
        assert DEFAULT_COVERAGE_TIMEOUT_SECONDS == 120
