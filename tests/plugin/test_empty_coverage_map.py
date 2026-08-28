"""An empty coverage map must stop the run, not be warned about.

Coverage-guided selection picks each gremlin's tests out of the per-test
coverage map. When the map is empty every gremlin gets an empty selection, so
nothing is run against any mutation and every gremlin is classified without a
single test having executed. The run then reports a mutation score, and that
score is not a measurement of anything.

The current handling is a warning, which nothing downstream can act on. A
warning that is followed by a confident 100% is worse than no run at all,
because it looks like a passing gate.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _pytest.outcomes import Exit

from pytest_gremlins import plugin
from pytest_gremlins.plugin import GremlinSession, _collect_coverage

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def session_with_tests() -> GremlinSession:
    return GremlinSession(
        enabled=True,
        test_node_ids={'tests/test_a.py::test_one': 'tests/test_a.py::test_one'},
        test_name_to_node_ids={'test_one': ['tests/test_a.py::test_one']},
    )


@pytest.fixture(name='_empty_collection')
def empty_collection_fixture(monkeypatch: pytest.MonkeyPatch) -> Callable[[], None]:
    def collect_nothing(*_args: object, **_kwargs: object) -> dict[str, dict[str, list[int]]]:
        return {}

    monkeypatch.setattr(plugin, '_run_tests_with_coverage', collect_nothing)
    return lambda: None


@pytest.mark.small
class DescribeCollectingNoCoverageAtAll:
    def it_stops_the_run(self, session_with_tests: GremlinSession, _empty_collection: object):
        with pytest.raises(Exit):
            _collect_coverage(session_with_tests, Path('/project'))

    def it_says_why_the_score_would_be_meaningless(self, session_with_tests: GremlinSession, _empty_collection: object):
        with pytest.raises(Exit, match='no tests would run against any mutation'):
            _collect_coverage(session_with_tests, Path('/project'))

    def it_points_at_the_timeout_as_a_cause(self, session_with_tests: GremlinSession, _empty_collection: object):
        with pytest.raises(Exit, match='coverage_timeout'):
            _collect_coverage(session_with_tests, Path('/project'))


@pytest.mark.small
class DescribeWhenAnEmptyMapIsExpected:
    def it_does_not_stop_a_session_that_collected_no_tests(self, _empty_collection: object):
        session = GremlinSession(enabled=True)
        _collect_coverage(session, Path('/project'))

    def it_does_not_stop_a_run_that_is_not_using_coverage_for_selection(
        self, session_with_tests: GremlinSession, _empty_collection: object
    ):
        session_with_tests.no_coverage_filter = True
        _collect_coverage(session_with_tests, Path('/project'))
