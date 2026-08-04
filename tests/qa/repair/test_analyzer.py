from __future__ import annotations

from asep.repair.analyzer import PytestFailureAnalyzer


def test_analyzer_handles_empty_output() -> None:
    analyzer = PytestFailureAnalyzer()

    result = analyzer.analyze("")

    assert result.summary == (
        "Falha de validação sem saída disponível."
    )
    assert result.failure_output == ""
    assert result.affected_paths == ()
    assert result.probable_cause is None


def test_analyzer_extracts_failed_test() -> None:
    output = """
FAILED tests/test_calculator.py::test_add - assert -1 == 5
"""

    analyzer = PytestFailureAnalyzer()

    result = analyzer.analyze(output)

    assert result.summary == (
        "FAILED tests/test_calculator.py::test_add - assert -1 == 5"
    )
    assert result.affected_paths == (
        "tests/test_calculator.py",
    )


def test_analyzer_extracts_probable_cause() -> None:
    output = """
tests/test_calculator.py:8: AssertionError
E assert -1 == 5
FAILED tests/test_calculator.py::test_add
"""

    analyzer = PytestFailureAnalyzer()

    result = analyzer.analyze(output)

    assert result.probable_cause == "assert -1 == 5"


def test_analyzer_extracts_traceback_paths() -> None:
    output = """
calculator.py:4: in add
tests/test_calculator.py:8: in test_add
E assert -1 == 5
FAILED tests/test_calculator.py::test_add
"""

    analyzer = PytestFailureAnalyzer()

    result = analyzer.analyze(output)

    assert result.affected_paths == (
        "tests/test_calculator.py",
        "calculator.py",
    )


def test_analyzer_normalizes_windows_paths() -> None:
    output = (
        "FAILED tests\\test_calculator.py::test_add\n"
        "src\\calculator.py:4: AssertionError\n"
    )

    analyzer = PytestFailureAnalyzer()

    result = analyzer.analyze(output)

    assert result.affected_paths == (
        "tests/test_calculator.py",
        "src/calculator.py",
    )


def test_analyzer_preserves_original_failure_output() -> None:
    output = (
        "E TypeError: unsupported operand type\n"
        "FAILED tests/test_service.py::test_service\n"
    )

    analyzer = PytestFailureAnalyzer()

    result = analyzer.analyze(output)

    assert result.failure_output == output
    assert result.probable_cause == (
        "TypeError: unsupported operand type"
    )


def test_analyzer_uses_generic_summary_without_failed_line() -> None:
    output = """
ERROR collecting tests/test_service.py
E ModuleNotFoundError: No module named 'service'
"""

    analyzer = PytestFailureAnalyzer()

    result = analyzer.analyze(output)

    assert result.summary == (
        "Pytest reportou falha de validação."
    )
    assert result.probable_cause == (
        "ModuleNotFoundError: No module named 'service'"
    )