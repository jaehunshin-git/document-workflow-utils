"""`doc-utils` 명령행 인터페이스입니다."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import (
    analyze_directory,
    analyze_numbers,
    compare_file_names,
    duplicate_names,
    format_report,
    write_parent_report,
    write_report,
)

JSON_SCHEMA_VERSION = "1.0"


def build_parser() -> argparse.ArgumentParser:
    """명령행 인자 파서를 구성합니다."""
    parser = argparse.ArgumentParser(prog="doc-utils", description="문서 목록과 디렉터리를 분석합니다.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    numbers = commands.add_parser("numbers", help="숫자 파일을 분석합니다.")
    numbers.add_argument("input", type=Path, metavar="INPUT")
    numbers.add_argument("--json", action="store_true", dest="as_json", help="결과를 JSON으로 출력합니다.")

    duplicates = commands.add_parser("duplicates", help="중복 이름을 찾습니다.")
    duplicates.add_argument("input", type=Path, metavar="INPUT")
    duplicates.add_argument("--json", action="store_true", dest="as_json", help="결과를 JSON으로 출력합니다.")

    compare = commands.add_parser("compare", help="기대 파일 목록을 디렉터리와 비교합니다.")
    compare.add_argument("expected", type=Path, metavar="EXPECTED")
    compare.add_argument("directory", type=Path, metavar="DIRECTORY")
    compare.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="PATTERN",
        help="상대 경로 또는 디렉터리를 무시합니다. 반복해서 지정할 수 있습니다.",
    )
    compare.add_argument(
        "--strict",
        action="store_true",
        help="누락 파일뿐 아니라 예기치 않은 파일도 오류로 처리합니다.",
    )
    compare.add_argument("--json", action="store_true", dest="as_json", help="결과를 JSON으로 출력합니다.")

    tree = commands.add_parser("tree", help="디렉터리 트리 보고서를 만듭니다.")
    tree.add_argument("directory", type=Path, metavar="DIRECTORY")
    tree.add_argument(
        "--mode",
        choices=("text", "emoji"),
        default="text",
        metavar="{text,emoji}",
        help="트리 출력 형식입니다. 기본값은 text입니다.",
    )
    tree.add_argument("--output", type=Path, metavar="PATH")
    tree.add_argument("--csv-output", type=Path, metavar="PATH")
    tree.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="PATTERN",
        help="상대 경로 또는 디렉터리를 무시합니다. 반복해서 지정할 수 있습니다.",
    )
    tree.add_argument("--json", action="store_true", dest="as_json", help="결과를 JSON으로 출력합니다.")
    return parser


def _print_json(command: str, value: dict[str, object]) -> None:
    """사람이 읽기 쉬운 정렬된 UTF-8 JSON을 표준 출력으로 보냅니다."""
    print(
        json.dumps(
            {"schema_version": JSON_SCHEMA_VERSION, "command": command, **value},
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


def main(argv: list[str] | None = None) -> int:
    """명령을 실행하고 종료 코드를 반환합니다."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "numbers":
            result = analyze_numbers(args.input)
            if args.as_json:
                _print_json(
                    args.command,
                    {
                        "duplicates": list(result.duplicates),
                        "invalid_count": result.invalid_count,
                        "invalid_lines": [
                            {"line": line, "value": value} for line, value in result.invalid_lines
                        ],
                        "maximum": result.maximum,
                        "minimum": result.minimum,
                        "missing": list(result.missing),
                        "valid_count": result.valid_count,
                    }
                )
            else:
                print(f"유효 정수: {result.valid_count}")
                print(f"비정상 행: {result.invalid_count}")
                print(f"누락 값 수: {len(result.missing)}")
                print(f"중복 값 수: {len(result.duplicates)}")
                print(f"범위: {result.minimum} ~ {result.maximum}" if result.has_numbers else "범위: 없음")
                print(f"누락 값: {', '.join(map(str, result.missing)) or '없음'}")
                print(f"중복 값: {', '.join(map(str, result.duplicates)) or '없음'}")
            return 0 if result.has_numbers else 1

        if args.command == "duplicates":
            result = duplicate_names(args.input)
            if args.as_json:
                _print_json(args.command, {"duplicate_count": len(result), "duplicates": result})
            else:
                for name, count in result.items():
                    print(f"{name}\t{count}")
                print(f"중복 이름 수: {len(result)}")
            return 0

        if args.command == "compare":
            result = compare_file_names(args.expected, args.directory, tuple(args.ignore))
            if args.as_json:
                _print_json(
                    args.command,
                    {
                        "actual_count": len(result.actual),
                        "expected_count": len(result.expected),
                        "matches": result.matches,
                        "missing": list(result.missing),
                        "unexpected": list(result.unexpected),
                    }
                )
            else:
                print(f"기대 파일 수: {len(result.expected)}")
                print(f"실제 파일 수: {len(result.actual)}")
                print(f"누락 파일 수: {len(result.missing)}")
                print("누락 파일:")
                for name in result.missing:
                    print(name)
                print(f"예기치 않은 파일 수: {len(result.unexpected)}")
                print("예기치 않은 파일:")
                for name in result.unexpected:
                    print(name)
            return 1 if result.missing or (args.strict and result.unexpected) else 0

        report = analyze_directory(args.directory, args.mode, tuple(args.ignore))
        if args.output:
            write_report(report, args.output)
        if args.as_json:
            _print_json(
                args.command,
                {
                    "directory_count": report.directory_count,
                    "entries": [
                        {
                            "depth": entry.depth,
                            "path": entry.path,
                            "type": "directory" if entry.is_directory else "file",
                        }
                        for entry in report.entries
                    ],
                    "file_count": report.file_count,
                    "extension_counts": dict(report.extension_counts),
                    "mode": report.mode,
                    "root": report.root.resolve().name or report.root.anchor,
                }
            )
        else:
            if not args.output:
                sys.stdout.write(format_report(report))
            print(f"요약: 디렉터리 {report.directory_count}개, 파일 {report.file_count}개")
            extension_summary = ", ".join(
                f"{extension or '[확장자 없음]'} {count}개"
                for extension, count in report.extension_counts.items()
            )
            print(f"확장자: {extension_summary or '없음'}")
        if args.csv_output:
            write_parent_report(report, args.csv_output)
        return 0
    except (OSError, ValueError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
