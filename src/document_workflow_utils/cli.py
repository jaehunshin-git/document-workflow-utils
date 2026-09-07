"""`doc-utils` 명령행 인터페이스입니다."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import (
    analyze_directory,
    analyze_numbers,
    compare_file_names,
    duplicate_names,
    format_report,
    write_parent_report,
    write_report,
)


def build_parser() -> argparse.ArgumentParser:
    """명령행 인자 파서를 구성합니다."""
    parser = argparse.ArgumentParser(prog="doc-utils", description="문서 목록과 디렉터리를 분석합니다.")
    commands = parser.add_subparsers(dest="command", required=True)

    numbers = commands.add_parser("numbers", help="숫자 파일을 분석합니다.")
    numbers.add_argument("input", type=Path, metavar="INPUT")

    duplicates = commands.add_parser("duplicates", help="중복 이름을 찾습니다.")
    duplicates.add_argument("input", type=Path, metavar="INPUT")

    compare = commands.add_parser("compare", help="기대 파일 목록을 디렉터리와 비교합니다.")
    compare.add_argument("expected", type=Path, metavar="EXPECTED")
    compare.add_argument("directory", type=Path, metavar="DIRECTORY")

    tree = commands.add_parser("tree", help="디렉터리 트리 보고서를 만듭니다.")
    tree.add_argument("directory", type=Path, metavar="DIRECTORY")
    tree.add_argument("--mode", default="text", metavar="{text,emoji}")
    tree.add_argument("--output", type=Path, metavar="PATH")
    tree.add_argument("--csv-output", type=Path, metavar="PATH")
    return parser


def main(argv: list[str] | None = None) -> int:
    """명령을 실행하고 종료 코드를 반환합니다."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "numbers":
            result = analyze_numbers(args.input)
            print(f"유효 정수: {result.valid_count}")
            print(f"범위: {result.minimum} ~ {result.maximum}" if result.has_numbers else "범위: 없음")
            print(f"누락 값: {', '.join(map(str, result.missing)) or '없음'}")
            print(f"중복 값: {', '.join(map(str, result.duplicates)) or '없음'}")
            print(f"비정상 행: {result.invalid_count}")
            return 0 if result.has_numbers else 1

        if args.command == "duplicates":
            result = duplicate_names(args.input)
            for name, count in result.items():
                print(f"{name}\t{count}")
            return 0

        if args.command == "compare":
            result = compare_file_names(args.expected, args.directory)
            print("누락 파일:")
            for name in result.missing:
                print(name)
            print("예기치 않은 파일:")
            for name in result.unexpected:
                print(name)
            return 1 if result.missing else 0

        report = analyze_directory(args.directory, args.mode)
        if args.output:
            write_report(report, args.output)
        else:
            sys.stdout.write(format_report(report))
        if args.csv_output:
            write_parent_report(report, args.csv_output)
        return 0
    except (OSError, ValueError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
