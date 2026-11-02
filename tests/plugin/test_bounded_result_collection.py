"""Result collection must not wait for ever.

Results are collected with a bare `as_completed(futures)` and no timeout, so one
future that never resolves blocks the parent indefinitely. A run of ours
completed 9,798 of 10,096 mutants at about sixteen a second, stopped dead with
roughly nineteen seconds of work left, and was still silent thirty-two minutes
later.

Nothing in the log said which mutants were outstanding, because nothing prints
them, so there was nothing to take to the next run.

The deadline is per completion, not for the run: the run is healthy for as long
as results keep arriving, however long it takes in total.
"""

from __future__ import annotations

from concurrent.futures import Future
from typing import Any

import pytest

from pytest_gremlins.plugin import GremlinCollectionStalledError, _as_completed_or_stalled


def _resolved(value: str) -> Future[str]:
    future: Future[str] = Future()
    future.set_result(value)
    return future


@pytest.mark.small
class DescribeCollectingResultsThatArrive:
    def it_yields_every_future_that_completed(self):
        futures = {_resolved('a'): 'g1', _resolved('b'): 'g2'}
        collected = list(_as_completed_or_stalled(futures, stall_timeout=30.0))
        assert {future.result() for future in collected} == {'a', 'b'}

    def it_accepts_a_plain_iterable_of_futures(self):
        futures = [_resolved('a')]
        assert [future.result() for future in _as_completed_or_stalled(futures, stall_timeout=30.0)] == ['a']


@pytest.mark.small
class DescribeCollectingResultsThatNeverArrive:
    def it_gives_up_rather_than_waiting_for_ever(self):
        never: Future[Any] = Future()
        with pytest.raises(GremlinCollectionStalledError):
            list(_as_completed_or_stalled({never: 'g-stuck'}, stall_timeout=0.01))

    def it_says_how_many_mutants_were_outstanding(self):
        never: Future[Any] = Future()
        also_never: Future[Any] = Future()
        with pytest.raises(GremlinCollectionStalledError, match='2 mutant'):
            list(_as_completed_or_stalled({never: 'g-one', also_never: 'g-two'}, stall_timeout=0.01))

    def it_names_the_outstanding_mutants(self, capsys: pytest.CaptureFixture[str]):
        never: Future[Any] = Future()
        with pytest.raises(GremlinCollectionStalledError):
            list(_as_completed_or_stalled({never: 'g-stuck'}, stall_timeout=0.01))
        assert 'g-stuck' in capsys.readouterr().err

    def it_still_gives_up_when_some_results_arrived_first(self):
        never: Future[Any] = Future()
        futures = {_resolved('a'): 'g-done', never: 'g-stuck'}
        with pytest.raises(GremlinCollectionStalledError, match='1 mutant'):
            list(_as_completed_or_stalled(futures, stall_timeout=0.01))
