"""End-to-end proof that a verdict describes mutated code.

Every other test here checks one part in isolation: the module-name key, the
node IDs, the import hook, the coverage pre-scan. None of them can say that the
whole chain — instrument, key, import, select, run, classify — still produces a
verdict about the mutation rather than about pristine source.

That distinction is the one thing mutation testing cannot get wrong quietly. A
mutation that never activates still yields a verdict, so the run completes,
prints a score, and the score is a fiction. It is not a crash and not a warning;
it looks exactly like a clean pass.

So plant two mutants whose verdicts are known in advance and check both:

- ``killable`` is asserted by its test, so mutating its return must be caught.
- ``unwatched`` is called but never asserted, so mutating its return must not be.

A mutation that never activates makes the first one survive. A selection that
falls back to running the whole suite makes the second look caught. Either way
this fails, which is the point.

Driven through a real ``pytest --gremlins`` subprocess rather than ``pytester``:
the pre-scan runs a subprocess of its own, and this has to observe what a user
observes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SUBJECT = '''"""Two mutable returns with known-in-advance verdicts."""


def killable(value):
    """Asserted by its test, so mutating the return must be caught."""
    return value + 1


def unwatched(value):
    """Called but never asserted, so mutating the return must go unnoticed."""
    return value + 1
'''

TESTS = """from canary_pkg.services.commands.subject import killable, unwatched


def test_killable_is_asserted():
    assert killable(1) == 2


def test_unwatched_is_called_but_not_asserted():
    unwatched(1)
"""

DISTRIBUTION_PYPROJECT = '[project]\nname = "canary-pkg"\nversion = "0"\n'


@pytest.fixture
def workspace_project(tmp_path: Path) -> Path:
    """A distribution whose name and depth both differ from its import name.

    The hyphen matters: a module name built from the path relative to rootdir
    would contain it, and no import can produce such a name. The nesting
    matters too, because a package walk that stops at the first directory
    without an ``__init__.py`` truncates the name instead.
    """
    distribution = tmp_path / 'packages' / 'canary-pkg'
    package = distribution / 'canary_pkg' / 'services' / 'commands'
    package.mkdir(parents=True)
    (distribution / 'pyproject.toml').write_text(DISTRIBUTION_PYPROJECT)
    for parent in (
        distribution / 'canary_pkg',
        distribution / 'canary_pkg' / 'services',
        distribution / 'canary_pkg' / 'services' / 'commands',
    ):
        (parent / '__init__.py').write_text('')
    (package / 'subject.py').write_text(SUBJECT)

    tests = tmp_path / 'tests'
    tests.mkdir()
    (tests / 'test_subject.py').write_text(TESTS)
    (tmp_path / 'pytest.ini').write_text('[pytest]\naddopts =\n')
    return tmp_path


def _verdict_counts(project: Path) -> dict[str, int]:
    """Mutate the subject module and return a count of each verdict."""
    target = 'packages/canary-pkg/canary_pkg/services/commands/subject.py'
    environment = os.environ.copy()
    environment['PYTHONPATH'] = os.pathsep.join(
        [str(project / 'packages' / 'canary-pkg'), environment.get('PYTHONPATH', '')]
    )
    # A measuring parent exports --cov through PYTEST_ADDOPTS and COV_CORE_*, and
    # both follow os.environ in here. A second coverage measurement on top of the
    # pre-scan's own returns no data, and then this fails on a condition that has
    # nothing to do with what it tests. `addopts =` in pytest.ini clears the ini
    # option, not the environment variable.
    environment.pop('PYTEST_ADDOPTS', None)
    environment.pop('COVERAGE_FILE', None)
    for name in [key for key in environment if key.startswith('COV_CORE_')]:
        del environment[name]

    subprocess.run(
        [
            sys.executable,
            '-m',
            'pytest',
            'tests',
            '--gremlins',
            f'--gremlin-targets={target}',
            '--gremlin-operators=arithmetic',
            '--gremlin-report=json',
            '-q',
        ],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    report = project / 'coverage' / 'gremlins' / 'gremlins.json'
    assert report.is_file(), 'the run produced no JSON report'

    counts: dict[str, int] = {}
    for result in json.loads(report.read_text())['results']:
        status = result['status']
        counts[status] = counts.get(status, 0) + 1
    return counts


@pytest.mark.large
class DescribeAVerdictOnKnownMutants:
    def it_catches_a_mutant_whose_test_asserts_the_result(self, workspace_project: Path):
        counts = _verdict_counts(workspace_project)
        assert counts.get('zapped', 0) >= 1, f'a mutant its test provably kills was not caught: {counts}'

    def it_does_not_catch_a_mutant_nothing_asserts(self, workspace_project: Path):
        counts = _verdict_counts(workspace_project)
        assert counts.get('survived', 0) >= 1, f'an unasserted mutant was reported as caught: {counts}'

    def it_measures_every_mutant(self, workspace_project: Path):
        counts = _verdict_counts(workspace_project)
        assert counts.get('error', 0) == 0, f'a mutant could not be measured at all: {counts}'
