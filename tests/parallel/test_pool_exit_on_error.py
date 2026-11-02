"""Unwinding from an error must not wait on the work that caused it.

`__exit__` shuts the pool down with `wait=True`, which waits on every running
worker — including a wedged one. Any fail-fast inside the `with` block therefore
blocks in exactly the place it was trying to escape.
"""

from __future__ import annotations

import pytest

from pytest_gremlins.parallel.pool import WorkerPool


@pytest.mark.small
class DescribeLeavingTheWorkerPool:
    def it_waits_for_workers_on_a_clean_exit(self, monkeypatch: pytest.MonkeyPatch):
        waited: list[bool] = []
        monkeypatch.setattr(WorkerPool, 'shutdown', lambda _self, wait=True: waited.append(wait))

        with WorkerPool(max_workers=1):
            pass

        assert waited == [True]

    def it_does_not_wait_when_an_error_is_propagating(self, monkeypatch: pytest.MonkeyPatch):
        waited: list[bool] = []
        monkeypatch.setattr(WorkerPool, 'shutdown', lambda _self, wait=True: waited.append(wait))

        with pytest.raises(RuntimeError), WorkerPool(max_workers=1):
            raise RuntimeError('fail fast')

        assert waited == [False]
