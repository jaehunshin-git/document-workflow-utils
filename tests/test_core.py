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

    def test_number_span_is_limited(self) -> None:
        source = self.write("numbers.txt", "-1000000000000\n1000000000000\n")

        with self.assertRaisesRegex(ValueError, "정수 범위"):
            analyze_numbers(source)

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

    def test_compare_excludes_windows_style_desktop_ini_and_symlinks(self) -> None:
        directory = self.root / "files"
        self.write("files/a.txt", "")
        self.write("outside.txt", "")
        try:
            (directory / "external-link").symlink_to(self.root / "outside.txt")
        except OSError as error:
            self.skipTest(f"현재 환경에서 심볼릭 링크를 만들 수 없습니다: {error}")
        expected = self.write("expected.txt", "a.txt\nsub\\desktop.ini\n")

        result = compare_file_names(expected, directory)

        self.assertEqual(result.expected, ("a.txt",))
        self.assertEqual(result.actual, ("a.txt",))
        self.assertTrue(result.matches)

    def test_compare_normalizes_expected_posix_relative_paths(self) -> None:
        directory = self.root / "files"
        self.write("files/a.txt", "")
        self.write("files/sub/nested/b.txt", "")
        expected = self.write(
            "expected.txt",
            "./a.txt\nsub\\nested//./b.txt\n./\n.\n\n",
        )

        result = compare_file_names(expected, directory)

        self.assertEqual(result.expected, ("a.txt", "sub/nested/b.txt"))
        self.assertEqual(result.actual, ("a.txt", "sub/nested/b.txt"))
        self.assertTrue(result.matches)

    def test_compare_rejects_absolute_and_parent_expected_paths(self) -> None:
        directory = self.root / "files"
        self.write("files/a.txt", "")

        for invalid_path in (
            "/tmp/a.txt",
            r"C:\\tmp\\a.txt",
            "C:drive-relative.txt",
            "sub/../a.txt",
            "../a.txt",
        ):
            with self.subTest(invalid_path=invalid_path):
                expected = self.write("expected.txt", f"{invalid_path}\n")
                with self.assertRaises(ValueError):
                    compare_file_names(expected, directory)

    def test_compare_ignores_matching_paths_and_directory_prefixes(self) -> None:
        directory = self.root / "files"
        self.write("files/keep.txt", "")
        self.write("files/ignored/direct.txt", "")
        self.write("files/cache/nested/value.txt", "")
        expected = self.write("expected.txt", "keep.txt\nignored/direct.txt\ncache/nested/value.txt\n")

        result = compare_file_names(expected, directory, ignore_patterns=("ignored", "cache/*"))

        self.assertEqual(result.expected, ("keep.txt",))
        self.assertEqual(result.actual, ("keep.txt",))
        self.assertTrue(result.matches)

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

    def test_directory_report_counts_extensions_with_documented_rules(self) -> None:
        directory = self.root / "tree"
        self.write("tree/README", "")
        self.write("tree/.env", "")
        self.write("tree/.config.JSON", "")
        self.write("tree/archive.tar.GZ", "")
        self.write("tree/report.TXT", "")
        self.write("tree/another.txt", "")
        self.write("tree/final.", "")

        report = analyze_directory(directory)

        self.assertEqual(
            report.extension_counts,
            {"": 3, ".gz": 1, ".json": 1, ".txt": 2},
        )
        self.assertEqual(tuple(report.extension_counts), ("", ".gz", ".json", ".txt"))

    def test_invalid_tree_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            analyze_directory(self.root, "invalid")

    def test_directory_report_skips_symbolic_links(self) -> None:
        directory = self.root / "tree"
        directory.mkdir()
        try:
            (directory / "loop").symlink_to(directory, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"현재 환경에서 심볼릭 링크를 만들 수 없습니다: {error}")
        self.write("tree/visible.txt", "")

        report = analyze_directory(directory)

        self.assertEqual([entry.path for entry in report.entries], ["visible.txt"])

    def test_directory_report_ignores_paths_and_does_not_descend_into_ignored_directory(self) -> None:
        directory = self.root / "tree"
        self.write("tree/keep.txt", "")
        self.write("tree/skip/hidden.txt", "")
        self.write("tree/cache/deep/item.txt", "")

        report = analyze_directory(directory, ignore_patterns=("skip", "cache/*"))

        self.assertEqual([entry.path for entry in report.entries], ["keep.txt"])
