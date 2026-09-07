"""공개된 합성 업무 시나리오가 실제 명령과 함께 동작하는지 검증합니다."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_manifest_workflow_reports_the_synthetic_missing_file() -> None:
    """예제 소비 코드가 검증 실패와 누락 파일을 구분해 보고합니다."""
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"

    result = subprocess.run(
        [sys.executable, PROJECT_ROOT / "examples" / "verify_manifest.py"],
        capture_output=True,
        check=False,
        cwd=PROJECT_ROOT,
        encoding="utf-8",
        env=environment,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert result.stdout == "검증 실패: 누락 파일 1개\n- inbox/report-c.txt\n"
    assert result.stderr == ""
