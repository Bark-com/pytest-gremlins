"""The coverage pre-scan must run on a core that records dynamic contexts.

The pre-scan exists to produce a per-test coverage map, and it gets one from
coverage.py's dynamic contexts. coverage.py's ``sysmon`` core cannot record
them. It says so — "Dynamic contexts aren't supported with core=sysmon; context
data may be incomplete" — and then carries on, so the map comes back missing
whichever tests were dropped.

A dropped test is never run against the gremlins it covers. The gremlin
survives, and the test that would have zapped it sits in the suite, passing.
Silent under-reporting of exactly the thing the tool exists to report.

``COVERAGE_CORE`` is an ordinary environment variable, so a project that sets it
for its own coverage runs — sysmon is cheaper, and ordinary coverage needs no
contexts — hands it to the pre-scan by inheritance without ever choosing to.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from pytest_gremlins import plugin
from pytest_gremlins.plugin import _run_tests_with_coverage


@pytest.fixture
def captured_subprocess_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Run the pre-scan without really running it, keeping the env it asked for."""
    captured: dict[str, Any] = {}

    def fake_run(*_args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        captured.update(kwargs)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=b'', stderr=b'')

    monkeypatch.setattr(plugin.subprocess, 'run', fake_run)
    return captured


@pytest.mark.medium
class DescribePreScanCoverageCore:
    def it_asks_for_a_core_that_records_dynamic_contexts(
        self, tmp_path: Path, captured_subprocess_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv('COVERAGE_CORE', 'sysmon')
        _run_tests_with_coverage(['tests/test_a.py::test_one'], tmp_path)
        assert captured_subprocess_env['env']['COVERAGE_CORE'] != 'sysmon'

    def it_overrides_an_inherited_sysmon_setting(
        self, tmp_path: Path, captured_subprocess_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv('COVERAGE_CORE', 'sysmon')
        _run_tests_with_coverage(['tests/test_a.py::test_one'], tmp_path)
        assert captured_subprocess_env['env']['COVERAGE_CORE'] == 'ctrace'

    def it_leaves_the_rest_of_the_environment_alone(
        self, tmp_path: Path, captured_subprocess_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv('A_PROJECT_VARIABLE', 'kept')
        _run_tests_with_coverage(['tests/test_a.py::test_one'], tmp_path)
        assert captured_subprocess_env['env']['A_PROJECT_VARIABLE'] == 'kept'
