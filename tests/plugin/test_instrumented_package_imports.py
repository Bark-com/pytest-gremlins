"""An instrumented ``__init__.py`` must stay a package.

The generated import hook builds ``ModuleSpec(fullname, loader)`` with no
``submodule_search_locations``, and that attribute is what marks a module as a
package. Instrumenting a package's ``__init__.py`` therefore makes it a plain
module, and importing anything beneath it fails with::

    ModuleNotFoundError: No module named 'pkg.sub'; 'pkg' is not a package

Every gremlin in such a file is then scored against an import error rather than
against its mutation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pytest_gremlins.plugin import _get_lightweight_runner_script

PACKAGE_INIT = 'VALUE = 1\n'
PACKAGE_SUBMODULE = 'from pkg import VALUE\n\nRESULT = VALUE + 1\n'
TEST_IMPORTING_SUBMODULE = """
def test_imports_from_an_instrumented_package():
    from pkg.sub import RESULT

    assert RESULT == 2
"""


@pytest.fixture
def instrumented_package_project(tmp_path: Path) -> Path:
    """A project whose package ``__init__`` is served by the gremlin import hook."""
    package = tmp_path / 'pkg'
    package.mkdir()
    (package / '__init__.py').write_text(PACKAGE_INIT)
    (package / 'sub.py').write_text(PACKAGE_SUBMODULE)
    (tmp_path / 'test_package_import.py').write_text(TEST_IMPORTING_SUBMODULE)
    (tmp_path / 'sources.json').write_text(json.dumps({'pkg': PACKAGE_INIT}))
    return tmp_path


@pytest.mark.medium
class DescribeImportingBeneathAnInstrumentedPackage:
    def it_imports_a_submodule_of_an_instrumented_package(self, instrumented_package_project: Path):
        runner = instrumented_package_project / 'gremlin_lightweight_runner.py'
        runner.write_text(_get_lightweight_runner_script())

        completed = subprocess.run(
            [sys.executable, str(runner), 'test_package_import.py::test_imports_from_an_instrumented_package'],
            cwd=instrumented_package_project,
            env={
                'GREMLIN_ROOTDIR': str(instrumented_package_project),
                'PYTEST_GREMLINS_SOURCES_FILE': str(instrumented_package_project / 'sources.json'),
                'PATH': '',
                'PYTHONPATH': str(instrumented_package_project),
            },
            capture_output=True,
            timeout=30,
            check=False,
        )

        assert completed.returncode == 0
