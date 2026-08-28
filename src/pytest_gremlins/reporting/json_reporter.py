"""JSON reporter for gremlin mutation testing results.

Produces machine-readable JSON output for CI integration
and automated analysis of mutation testing results.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_gremlins.reporting.results import GremlinResult
    from pytest_gremlins.reporting.score import MutationScore
    from pytest_gremlins.reporting.types import (
        JsonFileStats,
        JsonReport,
        JsonResultEntry,
        JsonSummary,
    )


# Statuses whose entries keep `selected_tests`. A surviving, timed-out or
# errored mutant is one somebody will open and debug, and the covering tests are
# what they need. A zapped mutant is a line in a rollup.
_DEBUGGABLE_STATUSES = frozenset({'survived', 'timeout', 'error'})


class JsonReporter:
    """Reporter that produces JSON output for CI integration.

    JSON structure:
        {
            "summary": {
                "total": 10,
                "zapped": 8,
                "survived": 2,
                "timeout": 0,
                "error": 0,
                "percentage": 80.0
            },
            "files": {
                "auth.py": {"total": 5, "zapped": 4, "survived": 1, "percentage": 80.0},
                "utils.py": {"total": 5, "zapped": 4, "survived": 1, "percentage": 80.0}
            },
            "results": [
                {
                    "gremlin_id": "g001",
                    "file_path": "auth.py",
                    "line_number": 42,
                    "status": "zapped",
                    "operator": "comparison",
                    "description": ">= to >",
                    "killing_test": "test_auth"
                },
                ...
            ]
        }
    """

    def __init__(self, *, selected_tests_for_all_results: bool = False) -> None:
        """Create a reporter.

        Args:
            selected_tests_for_all_results: Keep `selected_tests` on every
                result, including zapped ones. Off by default: coverage-guided
                selection picks thousands of tests for a widely covered line, so
                on a large suite that list dominates the document and the report
                runs to gigabytes.
        """
        self._selected_tests_for_all_results = selected_tests_for_all_results

    def to_json(self, score: MutationScore) -> str:
        """Convert mutation score to JSON string.

        Args:
            score: The MutationScore to convert.

        Returns:
            Pretty-printed JSON string.
        """
        data = self._build_report_data(score)
        return json.dumps(data, indent=2)

    def write_report(self, score: MutationScore, output_path: Path) -> None:
        """Write mutation report to a JSON file.

        Args:
            score: The MutationScore to write.
            output_path: Path to the output JSON file.
        """
        # Streamed rather than built as one string and handed to write_text:
        # a large report is already a big dict, and rendering it to a single
        # string keeps both resident at the same time.
        with output_path.open('w', encoding='utf-8') as handle:
            json.dump(self._build_report_data(score), handle, indent=2)

    def _build_report_data(self, score: MutationScore) -> JsonReport:
        """Build the complete report data structure.

        Args:
            score: The MutationScore to convert.

        Returns:
            Dictionary suitable for JSON serialization.
        """
        return {
            'summary': self._build_summary(score),
            'files': self._build_file_breakdown(score),
            'results': [self._build_result(r) for r in score.results],
        }

    def _build_summary(self, score: MutationScore) -> JsonSummary:
        """Build the summary section.

        Args:
            score: The MutationScore to summarize.

        Returns:
            Summary dictionary.
        """
        return {
            'total': score.total,
            'zapped': score.zapped,
            'survived': score.survived,
            'timeout': score.timeout,
            'error': score.error,
            'pardoned': score.pardoned,
            'percentage': score.percentage,
        }

    def _build_file_breakdown(self, score: MutationScore) -> dict[str, JsonFileStats]:
        """Build per-file breakdown section.

        Args:
            score: The MutationScore to break down.

        Returns:
            Dictionary mapping file paths to their stats.
        """
        file_scores = score.by_file()
        return {
            file_path: {
                'total': file_score.total,
                'zapped': file_score.zapped,
                'survived': file_score.survived,
                'percentage': file_score.percentage,
            }
            for file_path, file_score in file_scores.items()
        }

    def _build_result(self, result: GremlinResult) -> JsonResultEntry:
        """Build a single result entry.

        Args:
            result: The GremlinResult to convert.

        Returns:
            Dictionary representing this result.
        """
        gremlin = result.gremlin
        entry: JsonResultEntry = {
            'gremlin_id': gremlin.gremlin_id,
            'file_path': gremlin.file_path,
            'line_number': gremlin.line_number,
            'status': result.status.value,
            'operator': gremlin.operator_name,
            'description': gremlin.description,
        }
        if result.killing_test is not None:
            entry['killing_test'] = result.killing_test
        if result.error_output:
            entry['error_output'] = result.error_output
        if result.execution_time_ms is not None:
            entry['execution_time_ms'] = result.execution_time_ms
        if result.selected_tests and (
            self._selected_tests_for_all_results or result.status.value in _DEBUGGABLE_STATUSES
        ):
            entry['selected_tests'] = result.selected_tests
        return entry
