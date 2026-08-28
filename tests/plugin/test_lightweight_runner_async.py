"""The lightweight runner must actually execute async test functions.

The runner skips pytest and calls the test callable directly. An ``async def``
test returns a coroutine and executes nothing, so no assertion inside it can
fail: the runner reads that as a pass and the gremlin is reported as surviving,
while the test that would zap it sits in the suite, passing.

These are subprocess tests because the runner is generated as a standalone
script and executed by a worker, so running it as a script is the only way to
observe what the worker observes.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pytest_gremlins.plugin import _get_lightweight_runner_script

ASYNC_TESTS = """
async def test_async_that_fails():
    assert False


async def test_async_that_passes():
    assert True


class TestAsyncMethods:
    async def test_async_method_that_fails(self):
        assert False

    async def test_async_method_that_passes(self):
        assert True
"""

SYNC_TESTS = """
def test_sync_that_fails():
    assert False


def test_sync_that_passes():
    assert True
"""


def _run_lightweight_runner(rootdir: Path, node_id: str) -> int:
    """Execute the generated runner against one node ID, returning its exit code."""
    runner = rootdir / 'gremlin_lightweight_runner.py'
    runner.write_text(_get_lightweight_runner_script())
    completed = subprocess.run(
        [sys.executable, str(runner), node_id],
        cwd=rootdir,
        env={'GREMLIN_ROOTDIR': str(rootdir), 'PATH': '', 'PYTHONPATH': str(rootdir)},
        capture_output=True,
        timeout=30,
        check=False,
    )
    return completed.returncode


@pytest.fixture
def async_test_project(tmp_path: Path) -> Path:
    (tmp_path / 'test_async_sample.py').write_text(ASYNC_TESTS)
    return tmp_path


@pytest.fixture
def sync_test_project(tmp_path: Path) -> Path:
    (tmp_path / 'test_sync_sample.py').write_text(SYNC_TESTS)
    return tmp_path


@pytest.mark.medium
class DescribeLightweightRunnerWithAsyncTests:
    def it_fails_for_a_failing_async_function(self, async_test_project: Path):
        exit_code = _run_lightweight_runner(async_test_project, 'test_async_sample.py::test_async_that_fails')
        assert exit_code == 1

    def it_passes_for_a_passing_async_function(self, async_test_project: Path):
        exit_code = _run_lightweight_runner(async_test_project, 'test_async_sample.py::test_async_that_passes')
        assert exit_code == 0

    def it_fails_for_a_failing_async_method(self, async_test_project: Path):
        exit_code = _run_lightweight_runner(
            async_test_project,
            'test_async_sample.py::TestAsyncMethods::test_async_method_that_fails',
        )
        assert exit_code == 1

    def it_passes_for_a_passing_async_method(self, async_test_project: Path):
        exit_code = _run_lightweight_runner(
            async_test_project,
            'test_async_sample.py::TestAsyncMethods::test_async_method_that_passes',
        )
        assert exit_code == 0


@pytest.mark.medium
class DescribeLightweightRunnerWithSyncTests:
    """Synchronous tests keep behaving exactly as they did."""

    def it_fails_for_a_failing_sync_function(self, sync_test_project: Path):
        exit_code = _run_lightweight_runner(sync_test_project, 'test_sync_sample.py::test_sync_that_fails')
        assert exit_code == 1

    def it_passes_for_a_passing_sync_function(self, sync_test_project: Path):
        exit_code = _run_lightweight_runner(sync_test_project, 'test_sync_sample.py::test_sync_that_passes')
        assert exit_code == 0
