"""명령행 인터페이스의 표준 출력과 종료 코드를 검증합니다."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from document_workflow_utils.cli import main

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, name: str, content: str = "") -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def run_command(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(arguments)
        return result, stdout.getvalue(), stderr.getvalue()

    def run_module(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        """현재 소스 트리를 사용해 모듈 CLI를 별도 프로세스에서 실행합니다."""
        environment = os.environ.copy()
        source_directory = str(PROJECT_ROOT / "src")
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(None, (source_directory, environment.get("PYTHONPATH")))
        )
        return subprocess.run(
            [sys.executable, "-m", "document_workflow_utils", *arguments],
            capture_output=True,
            check=False,
            cwd=PROJECT_ROOT,
            env=environment,
            text=True,
            timeout=30,
        )

    def test_numbers_prints_result_and_returns_zero_when_numbers_exist(self) -> None:
        source = self.write("numbers.txt", "10\n12\n12\nwrong\n")

        status, output, _ = self.run_command(["numbers", str(source)])

        self.assertEqual(status, 0)
        self.assertIn("유효 정수: 3", output)
        self.assertIn("범위: 10 ~ 12", output)
        self.assertIn("누락 값: 11", output)
        self.assertIn("중복 값: 12", output)
        self.assertIn("비정상 행: 1", output)
        self.assertIn("누락 값 수: 1", output)
        self.assertIn("중복 값 수: 1", output)

    def test_numbers_returns_one_without_valid_numbers(self) -> None:
        source = self.write("numbers.txt", "wrong\n")

        status, _, _ = self.run_command(["numbers", str(source)])

        self.assertEqual(status, 1)

    def test_numbers_returns_two_when_range_is_too_wide(self) -> None:
        source = self.write("numbers.txt", "-1000000000000\n1000000000000\n")

        status, stdout, stderr = self.run_command(["numbers", str(source)])

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("정수 범위", stderr)

    def test_duplicates_writes_to_stdout(self) -> None:
        source = self.write("names.txt", "a\na\nb\n")

        status, output, _ = self.run_command(["duplicates", str(source)])

        self.assertEqual(status, 0)
        self.assertEqual(output, "a\t2\n중복 이름 수: 1\n")

    def test_global_version_displays_public_package_version(self) -> None:
        with self.assertRaises(SystemExit) as captured, contextlib.redirect_stdout(io.StringIO()) as stdout:
            main(["--version"])

        self.assertEqual(captured.exception.code, 0)
        self.assertEqual(stdout.getvalue(), "0.3.0\n")

    def test_json_output_uses_documented_schemas(self) -> None:
        numbers = self.write("numbers.txt", "1\n3\nwrong\n")
        names = self.write("names.txt", "가\n가\n나\n")
        directory = self.root / "directory"
        self.write("directory/actual.txt")
        self.write("directory/folder/file.txt")
        expected = self.write("expected.txt", "wanted.txt\n")

        status, output, _ = self.run_command(["numbers", str(numbers), "--json"])
        self.assertEqual(status, 0)
        self.assertEqual(
            json.loads(output),
            {
                "command": "numbers",
                "duplicates": [],
                "invalid_count": 1,
                "invalid_lines": [{"line": 3, "value": "wrong"}],
                "maximum": 3,
                "minimum": 1,
                "missing": [2],
                "schema_version": "1.0",
                "valid_count": 2,
            },
        )

        status, output, _ = self.run_command(["duplicates", str(names), "--json"])
        self.assertEqual(status, 0)
        self.assertEqual(
            json.loads(output),
            {
                "command": "duplicates",
                "duplicate_count": 1,
                "duplicates": {"가": 2},
                "schema_version": "1.0",
            },
        )
        self.assertIn('  "duplicate_count": 1', output)

        status, output, _ = self.run_command(["compare", str(expected), str(directory), "--json"])
        self.assertEqual(status, 1)
        self.assertEqual(
            json.loads(output),
            {
                "actual_count": 2,
                "command": "compare",
                "expected_count": 1,
                "matches": False,
                "missing": ["wanted.txt"],
                "schema_version": "1.0",
                "unexpected": ["actual.txt", "folder/file.txt"],
            },
        )

        status, output, _ = self.run_command(["tree", str(directory), "--json"])
        self.assertEqual(status, 0)
        self.assertEqual(
            json.loads(output),
            {
                "command": "tree",
                "directory_count": 1,
                "entries": [
                    {"depth": 0, "path": "actual.txt", "type": "file"},
                    {"depth": 0, "path": "folder", "type": "directory"},
                    {"depth": 1, "path": "folder/file.txt", "type": "file"},
                ],
                "extension_counts": {".txt": 2},
                "file_count": 2,
                "mode": "text",
                "root": "directory",
                "schema_version": "1.0",
            },
        )

    def test_compare_returns_one_for_missing_expected_file(self) -> None:
        directory = self.root / "directory"
        self.write("directory/actual.txt")
        expected = self.write("expected.txt", "wanted.txt\n")

        status, output, _ = self.run_command(["compare", str(expected), str(directory)])

        self.assertEqual(status, 1)
        self.assertIn("wanted.txt", output)
        self.assertIn("actual.txt", output)
        self.assertIn("기대 파일 수: 1", output)
        self.assertIn("실제 파일 수: 1", output)

    def test_compare_returns_zero_when_only_unexpected_files_exist(self) -> None:
        directory = self.root / "directory"
        self.write("directory/actual.txt")
        expected = self.write("expected.txt", "")

        status, output, _ = self.run_command(["compare", str(expected), str(directory)])

        self.assertEqual(status, 0)
        self.assertIn("actual.txt", output)
        self.assertIn("누락 파일 수: 0", output)

    def test_compare_strict_returns_one_when_only_unexpected_files_exist(self) -> None:
        directory = self.root / "directory"
        self.write("directory/actual.txt")
        expected = self.write("expected.txt", "")

        status, output, _ = self.run_command(["compare", str(expected), str(directory), "--strict"])

        self.assertEqual(status, 1)
        self.assertIn("예기치 않은 파일 수: 1", output)

    def test_compare_and_tree_ignore_repeatable_patterns(self) -> None:
        directory = self.root / "directory"
        self.write("directory/keep.txt")
        self.write("directory/skip/value.txt")
        self.write("directory/cache/deep/item.txt")
        expected = self.write("expected.txt", "keep.txt\nskip/value.txt\ncache/deep/item.txt\n")

        status, output, _ = self.run_command(
            [
                "compare",
                str(expected),
                str(directory),
                "--ignore",
                "skip",
                "--ignore",
                "cache/*",
            ]
        )
        self.assertEqual(status, 0)
        self.assertIn("기대 파일 수: 1", output)

        status, output, _ = self.run_command(
            ["tree", str(directory), "--ignore", "skip", "--ignore", "cache/*"]
        )
        self.assertEqual(status, 0)
        self.assertIn("keep.txt", output)
        self.assertNotIn("skip", output)
        self.assertNotIn("cache", output)
        self.assertIn("요약: 디렉터리 0개, 파일 1개", output)

    def test_compare_returns_two_when_directory_does_not_exist(self) -> None:
        expected = self.write("expected.txt", "wanted.txt\n")

        status, stdout, stderr = self.run_command(
            ["compare", str(expected), str(self.root / "does-not-exist")]
        )

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("비교할 디렉터리를 찾을 수 없습니다", stderr)

    def test_tree_writes_stdout_or_requested_files(self) -> None:
        directory = self.root / "directory"
        self.write("directory/folder/a.txt")

        status, stdout, _ = self.run_command(["tree", str(directory), "--mode", "emoji"])
        self.assertEqual(status, 0)
        self.assertIn("📁 folder", stdout)
        self.assertIn("요약: 디렉터리 1개, 파일 1개", stdout)
        self.assertIn("확장자: .txt 1개", stdout)

        text_output = self.root / "reports" / "tree.txt"
        csv_output = self.root / "reports" / "tree.csv"
        status, stdout, _ = self.run_command(
            ["tree", str(directory), "--output", str(text_output), "--csv-output", str(csv_output)]
        )
        self.assertEqual(status, 0)
        self.assertEqual(stdout, "요약: 디렉터리 1개, 파일 1개\n확장자: .txt 1개\n")
        self.assertTrue(text_output.exists())
        self.assertTrue(csv_output.exists())

    def test_argparse_errors_use_exit_code_two(self) -> None:
        with self.assertRaises(SystemExit) as captured, contextlib.redirect_stderr(io.StringIO()) as stderr:
            main(["tree"])
        self.assertEqual(captured.exception.code, 2)
        self.assertIn("the following arguments are required", stderr.getvalue())

    def test_operating_system_error_is_printed_to_stderr_with_exit_code_two(self) -> None:
        missing = self.root / "does-not-exist"

        status, stdout, stderr = self.run_command(["tree", str(missing)])

        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("오류:", stderr)

    def test_invalid_mode_is_rejected_by_argparse_with_exit_code_two(self) -> None:
        directory = self.root / "directory"
        directory.mkdir()

        with (
            self.assertRaises(SystemExit) as captured,
            contextlib.redirect_stdout(io.StringIO()) as stdout,
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            main(["tree", str(directory), "--mode", "wrong"])

        self.assertEqual(captured.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("invalid choice", stderr.getvalue())
        self.assertIn("text", stderr.getvalue())
        self.assertIn("emoji", stderr.getvalue())

    def test_help_lists_strict_and_mode_choices(self) -> None:
        with (
            self.assertRaises(SystemExit) as captured,
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            main(["tree", "--help"])

        self.assertEqual(captured.exception.code, 0)
        self.assertIn("--mode {text,emoji}", stdout.getvalue())
        self.assertIn("트리 출력 형식", stdout.getvalue())

        with (
            self.assertRaises(SystemExit) as captured,
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            main(["compare", "--help"])

        self.assertEqual(captured.exception.code, 0)
        self.assertIn("--strict", stdout.getvalue())

    def test_module_cli_uses_current_source_and_json_contract(self) -> None:
        source = self.write("numbers.txt", "1\n3\n")

        version = self.run_module(["--version"])
        result = self.run_module(["numbers", str(source), "--json"])

        self.assertEqual(version.returncode, 0)
        self.assertEqual(version.stdout, "0.3.0\n")
        self.assertEqual(version.stderr, "")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["command"], "numbers")
        self.assertEqual(json.loads(result.stdout)["schema_version"], "1.0")

    def test_script_entrypoint_uses_current_source_when_available(self) -> None:
        entrypoint = shutil.which("doc-utils")
        if entrypoint is None:
            self.skipTest("현재 환경에 doc-utils 엔트리포인트가 없습니다.")

        environment = os.environ.copy()
        source_directory = str(PROJECT_ROOT / "src")
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(None, (source_directory, environment.get("PYTHONPATH")))
        )
        result = subprocess.run(
            [entrypoint, "--version"],
            capture_output=True,
            check=False,
            cwd=PROJECT_ROOT,
            env=environment,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "0.3.0\n")
        self.assertEqual(result.stderr, "")
