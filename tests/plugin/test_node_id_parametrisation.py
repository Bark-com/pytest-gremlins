"""Normalising node IDs must not damage parametrised ones.

A display suffix added by pytest-test-categories is stripped so the ID can be
handed back to pytest. The pattern that does it, ``\\s*\\[[A-Z]+\\]\\s*$``, also
matches an ordinary ``@pytest.mark.parametrize`` ID whose value is uppercase —
country codes, file formats, currencies, language codes.

Stripping one breaks test selection for every gremlin those tests cover. The
node-ID map is keyed on the stripped ID while coverage contexts record the real
one, so the lookup misses, no node IDs are appended to the mutant's command, and
the mutant runs against the entire suite instead. Whatever comes back is not a
verdict about the mutation: the suite passing reads as survived, and any
unrelated failure reads as zapped.

The two cases are distinguishable. pytest-test-categories appends its label
after a space; pytest's own parametrisation never does.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pytest_gremlins.plugin import _make_node_ids_relative

ROOTDIR = Path('/project')


@pytest.mark.small
class DescribeParametrisedNodeIds:
    @pytest.mark.parametrize(
        'node_id',
        [
            'tests/test_countries.py::test_dialling_code[GB]',
            'tests/test_countries.py::test_dialling_code[IE]',
            'tests/test_images.py::test_thumbnail[WEBP]',
            'tests/test_categories.py::test_label[COUNSELLING]',
            'tests/test_money.py::TestPrice::test_currency[USD]',
        ],
    )
    def it_preserves_an_uppercase_parametrisation_id(self, node_id: str):
        assert _make_node_ids_relative([node_id], ROOTDIR) == [node_id]

    def it_preserves_a_parametrisation_id_on_an_absolute_path(self):
        result = _make_node_ids_relative(['/project/tests/test_countries.py::test_dialling_code[GB]'], ROOTDIR)
        assert result == ['tests/test_countries.py::test_dialling_code[GB]']


@pytest.mark.small
class DescribeTestCategoryLabels:
    """The suffix this normalisation exists to remove still goes."""

    @pytest.mark.parametrize(
        ('decorated', 'expected'),
        [
            ('tests/test_thing.py::test_it [SMALL]', 'tests/test_thing.py::test_it'),
            ('tests/test_thing.py::test_it [MEDIUM]', 'tests/test_thing.py::test_it'),
            ('tests/test_thing.py::test_it [LARGE]', 'tests/test_thing.py::test_it'),
            ('tests/test_thing.py::test_it [XLARGE]', 'tests/test_thing.py::test_it'),
        ],
    )
    def it_strips_a_size_label(self, decorated: str, expected: str):
        assert _make_node_ids_relative([decorated], ROOTDIR) == [expected]

    def it_strips_a_size_label_from_a_parametrised_test(self):
        decorated = 'tests/test_countries.py::test_dialling_code[GB] [SMALL]'
        expected = 'tests/test_countries.py::test_dialling_code[GB]'
        assert _make_node_ids_relative([decorated], ROOTDIR) == [expected]
