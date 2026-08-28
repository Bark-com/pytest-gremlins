"""Resolving a test file's hash must not rescan every test file each time.

`_build_test_hashes_for_gremlin` maps each of a gremlin's covering tests to the
content hash of the file it lives in, and finds it by walking the whole
`test_hashes` dict looking for a matching path — once per test, per gremlin. It
is called on both cache paths, the read and the write, so the cost is paid for
every mutant whether it hits cache or not.

The work is quadratic in (gremlins x test files) and lands on the main thread
after every mutant has already finished, which is the worst place for it: the
progress line reads 100% and the run then goes quiet. It is cheap while the
cache is warm and ruinous on the cold run after a large test-suite change —
exactly when a nightly is most needed.

`test_hashes` is populated during collection and fixed by the time the mutation
loop runs, so the answer for a given path cannot change within a run.
"""

from __future__ import annotations

import pytest

from pytest_gremlins.plugin import GremlinSession, _build_test_hashes_for_gremlin


class CountingHashes(dict[str, str]):
    """A test_hashes dict that records how often it is walked."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.walks = 0

    def items(self):  # type: ignore[override]
        self.walks += 1
        return super().items()


@pytest.fixture
def session_with_two_test_files() -> GremlinSession:
    node_ids = {
        'test_one': 'tests/test_a.py::test_one',
        'test_two': 'tests/test_a.py::test_two',
        'test_three': 'tests/test_b.py::test_three',
    }
    return GremlinSession(
        enabled=True,
        test_node_ids=node_ids,
        test_name_to_node_ids={name: [node_id] for name, node_id in node_ids.items()},
        test_hashes=CountingHashes({'tests/test_a.py': 'hash-a', 'tests/test_b.py': 'hash-b'}),
    )


@pytest.mark.small
class DescribeResolvingTestFileHashes:
    def it_maps_every_covering_test_to_its_file_hash(self, session_with_two_test_files: GremlinSession):
        result = _build_test_hashes_for_gremlin(
            ['test_one', 'test_two', 'test_three'],
            session_with_two_test_files,
        )
        assert result == {'test_one': 'hash-a', 'test_two': 'hash-a', 'test_three': 'hash-b'}

    def it_walks_the_hashes_once_per_distinct_file(self, session_with_two_test_files: GremlinSession):
        hashes = session_with_two_test_files.test_hashes
        assert isinstance(hashes, CountingHashes)

        _build_test_hashes_for_gremlin(['test_one', 'test_two', 'test_three'], session_with_two_test_files)

        assert hashes.walks == 2

    def it_does_not_rescan_for_a_later_gremlin(self, session_with_two_test_files: GremlinSession):
        hashes = session_with_two_test_files.test_hashes
        assert isinstance(hashes, CountingHashes)

        for _ in range(10):
            _build_test_hashes_for_gremlin(['test_one', 'test_two', 'test_three'], session_with_two_test_files)

        assert hashes.walks == 2

    def it_omits_a_test_whose_file_has_no_hash(self):
        session = GremlinSession(
            enabled=True,
            test_node_ids={'test_orphan': 'tests/test_missing.py::test_orphan'},
            test_hashes={'tests/test_a.py': 'hash-a'},
        )
        assert _build_test_hashes_for_gremlin(['test_orphan'], session) == {}

    def it_keeps_each_session_independent(self, session_with_two_test_files: GremlinSession):
        _build_test_hashes_for_gremlin(['test_one'], session_with_two_test_files)

        other = GremlinSession(
            enabled=True,
            test_node_ids={'test_one': 'tests/test_a.py::test_one'},
            test_hashes={'tests/test_a.py': 'different-hash'},
        )
        assert _build_test_hashes_for_gremlin(['test_one'], other) == {'test_one': 'different-hash'}
