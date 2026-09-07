"""배포 wheel과 sdist가 독립 환경에서 안전하게 동작하는지 검증합니다."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

EXPECTED_VERSION = "0.3.0"
TYPED_MARKER = "document_workflow_utils/py.typed"
RIGHTS_NOTICE = "모든 권리를 유보합니다"


def isolated_environment() -> dict[str, str]:
    """소스 트리와 사용자 패키지가 설치 검증에 개입하지 않는 환경을 반환합니다."""
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONUTF8"] = "1"
    return environment


def run(command: list[str], *, cwd: Path, expected_status: int = 0) -> subprocess.CompletedProcess[str]:
    """명령 실행 결과와 종료 코드를 검증합니다."""
    result = subprocess.run(
        command,
        cwd=cwd,
        env=isolated_environment(),
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    if result.returncode != expected_status:
        raise RuntimeError(
            f"명령 종료 코드가 {expected_status}여야 합니다: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def executable(environment: Path, name: str) -> Path:
    """운영체제별 가상 환경 실행 파일 경로를 반환합니다."""
    if sys.platform == "win32":
        return environment / "Scripts" / f"{name}.exe"
    return environment / "bin" / name


def verify_wheel(wheel: Path) -> None:
    """wheel의 타입 마커, 설치, CLI와 JSON 종료 코드를 검증합니다."""
    with zipfile.ZipFile(wheel) as archive:
        if TYPED_MARKER not in archive.namelist():
            raise RuntimeError(f"wheel에 {TYPED_MARKER} 파일이 없습니다.")
        metadata_files = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata_files) != 1:
            raise RuntimeError("wheel에서 배포 메타데이터를 하나만 찾을 수 있어야 합니다.")
        metadata = archive.read(metadata_files[0]).decode("utf-8")
        if RIGHTS_NOTICE not in metadata:
            raise RuntimeError("wheel 메타데이터에 권리 유보 안내가 없습니다.")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        environment = root / "venv"
        run([sys.executable, "-m", "venv", str(environment)], cwd=root)
        python = executable(environment, "python")
        cli = executable(environment, "doc-utils")
        run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)], cwd=root)

        for command in ([str(cli), "--version"], [str(python), "-m", "document_workflow_utils", "--version"]):
            result = run(command, cwd=root)
            if result.stdout.strip() != EXPECTED_VERSION:
                raise RuntimeError(f"버전 출력이 {EXPECTED_VERSION}이 아닙니다: {result.stdout!r}")

        numbers = root / "numbers.txt"
        numbers.write_text("1\n3\n", encoding="utf-8")
        result = run([str(cli), "numbers", str(numbers), "--json"], cwd=root)
        payload = json.loads(result.stdout)
        if (
            payload["schema_version"] != "1.0"
            or payload["command"] != "numbers"
            or payload["missing"] != [2]
            or payload["valid_count"] != 2
        ):
            raise RuntimeError(f"예상한 numbers JSON 결과가 아닙니다: {payload!r}")

        empty = root / "empty.txt"
        empty.write_text("\n", encoding="utf-8")
        result = run([str(cli), "numbers", str(empty), "--json"], cwd=root, expected_status=1)
        payload = json.loads(result.stdout)
        if (
            payload["schema_version"] != "1.0"
            or payload["command"] != "numbers"
            or payload["valid_count"] != 0
        ):
            raise RuntimeError("빈 numbers 입력의 JSON 결과가 예상과 다릅니다.")


def verify_sdist(sdist: Path) -> None:
    """sdist에서 템플릿 라이선스를 제외하고 권리 안내를 보존했는지 검증합니다."""
    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()
        if any(name.endswith("/.github/TEMPLATE_LICENSE") for name in names):
            raise RuntimeError("sdist에 템플릿 전용 라이선스 파일이 포함되어 있습니다.")
        metadata_files = [name for name in names if name.endswith("/PKG-INFO")]
        if len(metadata_files) != 1:
            raise RuntimeError("sdist에서 배포 메타데이터를 하나만 찾을 수 있어야 합니다.")
        extracted = archive.extractfile(metadata_files[0])
        if extracted is None or RIGHTS_NOTICE not in extracted.read().decode("utf-8"):
            raise RuntimeError("sdist 메타데이터에 권리 유보 안내가 없습니다.")


def main() -> None:
    """인자를 처리하고 검증을 실행합니다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("distribution_directory", type=Path)
    args = parser.parse_args()
    candidate = args.distribution_directory.resolve()
    if not candidate.is_dir():
        raise SystemExit(f"배포물 디렉터리를 찾을 수 없습니다: {candidate}")
    wheels = sorted(candidate.glob(f"document_workflow_utils-{EXPECTED_VERSION}-*.whl"))
    sdists = sorted(candidate.glob(f"document_workflow_utils-{EXPECTED_VERSION}.tar.gz"))
    if len(wheels) != 1:
        raise SystemExit(f"검증할 wheel은 정확히 하나여야 합니다: {candidate}")
    if len(sdists) != 1:
        raise SystemExit(f"검증할 sdist는 정확히 하나여야 합니다: {candidate}")
    verify_wheel(wheels[0])
    verify_sdist(sdists[0])
    print(f"배포물 검증 완료: {wheels[0].name}, {sdists[0].name}")


if __name__ == "__main__":
    main()
