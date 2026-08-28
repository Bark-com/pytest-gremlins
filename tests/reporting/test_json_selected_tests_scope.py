"""`selected_tests` belongs on the results someone will actually debug.

Every result entry carries `selected_tests` — every test covering that mutant —
and `to_json` renders the whole document with `json.dumps(data, indent=2)`
before a byte is written, so the string and the dict that produced it are both
resident at once.

Coverage-guided selection picks thousands of tests for a widely covered line, so
on a large suite the document runs to gigabytes and the pytest parent is killed
by the kernel in the final minute of the run. GitHub reports that as "The
operation was canceled", with no log and no exit code.

The list was added so a *surviving* mutant can be debugged: you need to know
what ran against it. A zapped mutant is not being debugged — it is a line in a
rollup. Keeping the list for survivors, timeouts and errors preserves the
intent at a fraction of the volume.
"""

from __future__ import annotations

import ast
import json
from typing import TYPE_CHECKING

import pytest

from pytest_gremlins.instrumentation.gremlin import Gremlin
from pytest_gremlins.reporting.json_reporter import JsonReporter
from pytest_gremlins.reporting.results import GremlinResult, GremlinResultStatus
from pytest_gremlins.reporting.score import MutationScore

if TYPE_CHECKING:
    from collections.abc import Callable

COVERING_TESTS = ['tests/test_a.py::test_one', 'tests/test_a.py::test_two']


@pytest.fixture
def result_for() -> Callable[[GremlinResultStatus], GremlinResult]:
    def build(status: GremlinResultStatus) -> GremlinResult:
        return GremlinResult(
            gremlin=Gremlin(
                gremlin_id=f'g-{status.value}',
                file_path='src/thing.py',
                line_number=1,
                original_node=ast.parse('a < b', mode='eval').body,
                mutated_node=ast.parse('a <= b', mode='eval').body,
                operator_name='comparison',
                description='< to <=',
            ),
            status=status,
            selected_tests=list(COVERING_TESTS),
        )

    return build


def _entries(score: MutationScore, **kwargs: object) -> dict[str, dict]:
    data = json.loads(JsonReporter(**kwargs).to_json(score))  # type: ignore[arg-type]
    return {entry['gremlin_id']: entry for entry in data['results']}


@pytest.mark.small
class DescribeSelectedTestsByDefault:
    @pytest.mark.parametrize(
        'status',
        [GremlinResultStatus.SURVIVED, GremlinResultStatus.TIMEOUT, GremlinResultStatus.ERROR],
    )
    def it_keeps_the_list_for_a_result_worth_debugging(
        self, status: GremlinResultStatus, result_for: Callable[[GremlinResultStatus], GremlinResult]
    ):
        entries = _entries(MutationScore.from_results([result_for(status)]))
        assert entries[f'g-{status.value}']['selected_tests'] == COVERING_TESTS

    def it_drops_the_list_for_a_zapped_result(self, result_for: Callable[[GremlinResultStatus], GremlinResult]):
        entries = _entries(MutationScore.from_results([result_for(GremlinResultStatus.ZAPPED)]))
        assert 'selected_tests' not in entries['g-zapped']

    def it_leaves_every_other_field_on_a_zapped_result(
        self, result_for: Callable[[GremlinResultStatus], GremlinResult]
    ):
        entries = _entries(MutationScore.from_results([result_for(GremlinResultStatus.ZAPPED)]))
        assert entries['g-zapped']['operator'] == 'comparison'
        assert entries['g-zapped']['line_number'] == 1


@pytest.mark.small
class DescribeSelectedTestsWhenAskedForAll:
    def it_keeps_the_list_for_a_zapped_result(self, result_for: Callable[[GremlinResultStatus], GremlinResult]):
        score = MutationScore.from_results([result_for(GremlinResultStatus.ZAPPED)])
        entries = _entries(score, selected_tests_for_all_results=True)
        assert entries['g-zapped']['selected_tests'] == COVERING_TESTS
