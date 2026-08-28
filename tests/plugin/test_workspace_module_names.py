"""Module names must be import names, whatever the project layout.

The instrumented-source import hook is keyed by module name, so the name derived
from a file's path has to be the name Python imports that file as. Deriving it
from the path relative to pytest's rootdir only holds for a single-distribution
project. In a workspace the import root is the distribution directory, not
rootdir, so the derived name picks up the directories above it::

    packages/my-package/my_package/service.py
      -> packages.my-package.my_package.service   (never importable)
      -> my_package.service                       (the import name)

A name no import can produce means the finder never fires, the mutation never
activates, and the gremlin is scored against pristine code — reported as
survived when its own tests would have zapped it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pytest_gremlins.instrumentation.gremlin import Gremlin
from pytest_gremlins.plugin import _build_gremlin_module_map, _path_to_module_name


@pytest.fixture
def flat_project(tmp_path: Path) -> Path:
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "flat"\nversion = "0"\n')
    (tmp_path / 'my_package').mkdir()
    return tmp_path


@pytest.fixture
def src_project(tmp_path: Path) -> Path:
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "srcy"\nversion = "0"\n')
    (tmp_path / 'src' / 'my_package').mkdir(parents=True)
    return tmp_path


@pytest.fixture
def workspace_project(tmp_path: Path) -> Path:
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "workspace"\nversion = "0"\n')
    member = tmp_path / 'packages' / 'my-package'
    (member / 'my_package').mkdir(parents=True)
    (member / 'pyproject.toml').write_text('[project]\nname = "my-package"\nversion = "0"\n')
    return tmp_path


@pytest.mark.medium
class DescribePathToModuleName:
    def it_derives_the_import_name_for_a_flat_layout(self, flat_project: Path):
        source = flat_project / 'my_package' / 'service.py'
        assert _path_to_module_name(source, flat_project) == 'my_package.service'

    def it_strips_the_src_directory(self, src_project: Path):
        source = src_project / 'src' / 'my_package' / 'service.py'
        assert _path_to_module_name(source, src_project) == 'my_package.service'

    def it_stops_at_the_distribution_root_in_a_workspace(self, workspace_project: Path):
        source = workspace_project / 'packages' / 'my-package' / 'my_package' / 'service.py'
        assert _path_to_module_name(source, workspace_project) == 'my_package.service'

    def it_strips_the_src_directory_inside_a_workspace_member(self, workspace_project: Path):
        member = workspace_project / 'packages' / 'my-package'
        source = member / 'src' / 'my_package' / 'service.py'
        source.parent.mkdir(parents=True)
        assert _path_to_module_name(source, workspace_project) == 'my_package.service'

    def it_names_a_package_by_its_directory_not_its_dunder_init(self, flat_project: Path):
        source = flat_project / 'my_package' / '__init__.py'
        assert _path_to_module_name(source, flat_project) == 'my_package'

    def it_never_produces_a_name_no_import_could_match(self, workspace_project: Path):
        source = workspace_project / 'packages' / 'my-package' / 'my_package' / 'service.py'
        assert '-' not in _path_to_module_name(source, workspace_project)


@pytest.mark.medium
class DescribeGremlinModuleMap:
    """The in-process executor derives the same names as the import hook."""

    def it_agrees_with_path_to_module_name_in_a_workspace(self, workspace_project: Path):
        source = workspace_project / 'packages' / 'my-package' / 'my_package' / 'service.py'
        gremlin = Gremlin(
            gremlin_id='g1',
            file_path=str(source),
            line_number=1,
            original_node=ast.parse('a < b', mode='eval').body,
            mutated_node=ast.parse('a <= b', mode='eval').body,
            operator_name='comparison',
            description='< to <=',
        )
        module_map = _build_gremlin_module_map([gremlin], workspace_project)
        assert module_map['g1'] == _path_to_module_name(source, workspace_project)

    def it_agrees_with_path_to_module_name_for_a_src_layout(self, src_project: Path):
        source = src_project / 'src' / 'my_package' / 'service.py'
        gremlin = Gremlin(
            gremlin_id='g1',
            file_path=str(source),
            line_number=1,
            original_node=ast.parse('a < b', mode='eval').body,
            mutated_node=ast.parse('a <= b', mode='eval').body,
            operator_name='comparison',
            description='< to <=',
        )
        module_map = _build_gremlin_module_map([gremlin], src_project)
        assert module_map['g1'] == _path_to_module_name(source, src_project)
