"""합성 파일 목록 비교 결과를 소비하는 자동화 예제입니다."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCHEMA_VERSION = "1.0"


def main() -> int:
    """비교 결과를 읽고 사람이 확인할 짧은 상태로 변환합니다."""
    examples = Path(__file__).resolve().parent
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    try:
        completed = subprocess.run(
            [
                "doc-utils",
                "compare",
                str(examples / "expected-files.txt"),
                str(examples / "documents"),
                "--ignore",
                "*.tmp",
                "--json",
            ],
            capture_output=True,
            check=False,
            env=environment,
            encoding="utf-8",
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"명령 실행 실패: {error}", file=sys.stderr)
        return 2
    if completed.returncode == 2:
        print(completed.stderr.rstrip(), file=sys.stderr)
        return 2
    if completed.returncode not in {0, 1}:
        print(f"예상하지 못한 종료 코드: {completed.returncode}", file=sys.stderr)
        return 2

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        print(f"JSON 해석 실패: {error}", file=sys.stderr)
        return 2
    if result.get("schema_version") != SCHEMA_VERSION or result.get("command") != "compare":
        print("지원하지 않는 JSON 계약입니다.", file=sys.stderr)
        return 2

    missing = result.get("missing")
    if not isinstance(missing, list) or not all(isinstance(path, str) for path in missing):
        print("누락 파일 필드의 형식이 올바르지 않습니다.", file=sys.stderr)
        return 2
    if missing:
        print(f"검증 실패: 누락 파일 {len(missing)}개")
        for path in missing:
            print(f"- {path}")
        return 1

    print("검증 성공: 기대한 파일이 모두 있습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
