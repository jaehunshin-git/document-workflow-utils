"""핵심 분석 기능의 동작을 검증합니다."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from document_workflow_utils import (
    analyze_directory,
    analyze_numbers,
    compare_file_names,
    duplicate_names,
    format_report,
    write_parent_report,
    write_report,
)


class CoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, name: str, content: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_numbers_finds_range_missing_duplicates_and_invalid_lines(self) -> None:
        source = self.write("numbers.txt", "-2\n\n0\n2\n0\n2.5\n잘못됨\n")

        result = analyze_numbers(source)

        self.assertEqual(result.valid_count, 4)
        self.assertEqual(result.invalid_count, 2)
        self.assertEqual(result.minimum, -2)
        self.assertEqual(result.maximum, 2)
        self.assertEqual(result.missing, (-1, 1))
        self.assertEqual(result.duplicates, (0,))
        self.assertEqual(result.invalid_lines, ((6, "2.5"), (7, "잘못됨")))

    def test_empty_number_input_has_no_range_or_anomalies(self) -> None:
        result = analyze_numbers(self.write("numbers.txt", "\n  \n"))

        self.assertFalse(result.has_numbers)
        self.assertEqual(result.valid_count, 0)
        self.assertIsNone(result.minimum)
        self.assertIsNone(result.maximum)
        self.assertEqual(result.missing, ())
        self.assertEqual(result.duplicates, ())
        self.assertEqual(result.invalid_lines, ())

    def test_duplicate_names_returns_only_repeated_names_in_stable_order(self) -> None:
        result = duplicate_names(self.write("names.txt", "B\na\nB\n\na\na\n"))

        self.assertEqual(result, {"a": 3, "B": 2})

    def test_compare_is_recursive_and_excludes_desktop_ini(self) -> None:
        directory = self.root / "files"
        self.write("files/a.txt", "")
        self.write("files/sub/b.txt", "")
        self.write("files/desktop.ini", "")
        expected = self.write("expected.txt", "a.txt\nsub/b.txt\nmissing.txt\ndesktop.ini\n")

        result = compare_file_names(expected, directory)

        self.assertEqual(result.actual, ("a.txt", "sub/b.txt"))
        self.assertEqual(result.missing, ("missing.txt",))
        self.assertEqual(result.unexpected, ())
        self.assertFalse(result.matches)

    def test_directory_report_formats_and_writes_both_reports(self) -> None:
        directory = self.root / "tree"
        self.write("tree/z.txt", "")
        self.write("tree/alpha/x.txt", "")
        self.write("tree/desktop.ini", "")
        report = analyze_directory(directory)

        self.assertEqual([entry.path for entry in report.entries], ["alpha", "alpha/x.txt", "z.txt"])
        self.assertEqual(format_report(report), "tree\n[D] alpha\n  [F] x.txt\n[F] z.txt\n")
        self.assertIn("📁 alpha", format_report(analyze_directory(directory, "emoji")))

        text_output = self.root / "out" / "tree.txt"
        csv_output = self.root / "out" / "parents.csv"
        self.assertEqual(write_report(report, text_output), text_output)
        self.assertEqual(text_output.read_text(encoding="utf-8"), format_report(report))
        write_parent_report(report, csv_output)
        with csv_output.open(encoding="utf-8", newline="") as file:
            self.assertEqual(list(csv.reader(file)), [["이름", "상위_경로"], ["x.txt", "alpha"], ["z.txt", ""]])

    def test_invalid_tree_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            analyze_directory(self.root, "invalid")
