"""파일 기반 분석 기능의 구현입니다.

입력 텍스트는 UTF-8로 읽고, 비어 있는 행은 모든 분석에서 제외합니다.
"""

from __future__ import annotations

import csv
import fnmatch
from dataclasses import dataclass
from pathlib import Path

MAX_NUMBER_SPAN = 1_000_000


def _sort_key(path: Path | str) -> tuple[str, str]:
    """운영 체제와 무관하게 안정적인 이름순 정렬 키를 반환합니다."""
    text = str(path).replace("\\", "/")
    return (text.casefold(), text)


def _read_lines(input_path: str | Path) -> list[str]:
    return Path(input_path).read_text(encoding="utf-8").splitlines()


def _is_ignored(
    relative_path: str, ignore_patterns: tuple[str, ...], is_directory: bool = False
) -> bool:
    """상대 POSIX 경로나 그 상위 디렉터리가 무시 패턴과 일치하는지 확인합니다."""
    parts = relative_path.split("/")
    prefixes = ["/".join(parts[:index]) for index in range(1, len(parts))]
    candidates = [relative_path, *prefixes]
    if is_directory:
        candidates.append(f"{relative_path}/")
    candidates.extend(f"{prefix}/" for prefix in prefixes)
    return any(
        fnmatch.fnmatchcase(candidate, pattern)
        for candidate in candidates
        for pattern in ignore_patterns
    )


def _normalize_expected_relative_path(value: str) -> str | None:
    """기대 목록의 경로를 비교 가능한 POSIX 상대 경로로 정규화합니다.

    빈 값과 현재 디렉터리를 가리키는 값은 무시합니다. 백슬래시는 POSIX 구분자로
    바꾸고, 중복 구분자와 ``.`` 구성 요소는 제거합니다. 절대 경로와 ``..`` 구성
    요소는 기대 목록이 비교 루트 밖을 가리키지 않도록 거부합니다.
    """
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        return None
    if normalized.startswith("/") or (
        len(normalized) >= 2 and normalized[0].isalpha() and normalized[1] == ":"
    ):
        raise ValueError(f"기대 파일명은 상대 경로여야 합니다: {value!r}")

    parts: list[str] = []
    for part in normalized.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            raise ValueError(f"기대 파일명에 상위 경로를 사용할 수 없습니다: {value!r}")
        parts.append(part)
    return "/".join(parts) or None


@dataclass(frozen=True)
class NumberAnalysis:
    """정수 목록의 범위, 누락, 중복 및 비정상 행 분석 결과입니다."""

    values: tuple[int, ...]
    minimum: int | None
    maximum: int | None
    missing: tuple[int, ...]
    duplicates: tuple[int, ...]
    invalid_lines: tuple[tuple[int, str], ...]

    @property
    def valid_count(self) -> int:
        """유효한 정수 행의 수를 반환합니다."""
        return len(self.values)

    @property
    def invalid_count(self) -> int:
        """비정상 행의 수를 반환합니다."""
        return len(self.invalid_lines)

    @property
    def has_numbers(self) -> bool:
        """하나 이상의 유효 숫자가 있는지 반환합니다."""
        return self.valid_count > 0


def analyze_numbers(input_path: str | Path) -> NumberAnalysis:
    """한 줄에 하나씩 있는 정수 목록을 분석합니다.

    빈 행은 제외합니다. 정수로 변환할 수 없는 행은 원래의 1부터 시작하는 행 번호와
    함께 보존하며, 유효한 정수의 최솟값부터 최댓값 사이의 누락 값을 찾습니다.
    """
    values: list[int] = []
    invalid_lines: list[tuple[int, str]] = []
    for line_number, line in enumerate(_read_lines(input_path), start=1):
        value_text = line.strip()
        if not value_text:
            continue
        try:
            value = int(value_text)
        except ValueError:
            invalid_lines.append((line_number, line))
            continue
        values.append(value)

    if not values:
        return NumberAnalysis((), None, None, (), (), tuple(invalid_lines))
    minimum = min(values)
    maximum = max(values)
    if maximum - minimum > MAX_NUMBER_SPAN:
        raise ValueError(
            f"분석할 정수 범위는 {MAX_NUMBER_SPAN:,} 이하여야 합니다: "
            f"{minimum} ~ {maximum}"
        )
    counts: dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return NumberAnalysis(
        values=tuple(values),
        minimum=minimum,
        maximum=maximum,
        missing=tuple(value for value in range(minimum, maximum + 1) if value not in counts),
        duplicates=tuple(value for value, count in sorted(counts.items()) if count > 1),
        invalid_lines=tuple(invalid_lines),
    )


def duplicate_names(input_path: str | Path) -> dict[str, int]:
    """입력 파일에서 두 번 이상 등장한 이름과 횟수를 반환합니다."""
    counts: dict[str, int] = {}
    for line in _read_lines(input_path):
        name = line.strip()
        if name:
            counts[name] = counts.get(name, 0) + 1
    return {name: counts[name] for name in sorted(counts, key=_sort_key) if counts[name] > 1}


@dataclass(frozen=True)
class FileComparison:
    """기대 파일명 목록과 실제 디렉터리를 비교한 결과입니다."""

    expected: tuple[str, ...]
    actual: tuple[str, ...]
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]

    @property
    def matches(self) -> bool:
        """누락과 예기치 않은 파일이 모두 없는지 반환합니다."""
        return not self.missing and not self.unexpected


def _relative_files(
    directory: str | Path, ignore_patterns: tuple[str, ...] = ()
) -> tuple[str, ...]:
    root = Path(directory)
    if not root.is_dir():
        raise NotADirectoryError(f"비교할 디렉터리를 찾을 수 없습니다: {root}")
    files: list[str] = []

    def visit(current: Path) -> None:
        children = sorted(
            (
                child
                for child in current.iterdir()
                if not child.is_symlink() and child.name.casefold() != "desktop.ini"
            ),
            key=lambda child: _sort_key(child.name),
        )
        for child in children:
            relative = child.relative_to(root).as_posix()
            if _is_ignored(relative, ignore_patterns, child.is_dir()):
                continue
            if child.is_dir():
                visit(child)
            elif child.is_file():
                files.append(relative)

    visit(root)
    return tuple(sorted(files, key=_sort_key))


def compare_file_names(
    expected_path: str | Path,
    directory: str | Path,
    ignore_patterns: tuple[str, ...] = (),
) -> FileComparison:
    """기대 목록의 상대 파일명과 디렉터리의 실제 파일명을 비교합니다."""
    expected: set[str] = set()
    for line in _read_lines(expected_path):
        normalized = _normalize_expected_relative_path(line)
        if (
            normalized
            and normalized.rsplit("/", maxsplit=1)[-1].casefold() != "desktop.ini"
            and not _is_ignored(normalized, ignore_patterns)
        ):
            expected.add(normalized)
    actual = set(_relative_files(directory, ignore_patterns))
    ordered_expected = tuple(sorted(expected, key=_sort_key))
    ordered_actual = tuple(sorted(actual, key=_sort_key))
    return FileComparison(
        expected=ordered_expected,
        actual=ordered_actual,
        missing=tuple(sorted(expected - actual, key=_sort_key)),
        unexpected=tuple(sorted(actual - expected, key=_sort_key)),
    )


@dataclass(frozen=True)
class DirectoryEntry:
    """디렉터리 보고서의 한 항목입니다."""

    path: str
    is_directory: bool
    depth: int


@dataclass(frozen=True)
class DirectoryReport:
    """재귀적으로 수집한 디렉터리 구조입니다."""

    root: Path
    entries: tuple[DirectoryEntry, ...]
    mode: str

    @property
    def file_count(self) -> int:
        return sum(not entry.is_directory for entry in self.entries)

    @property
    def directory_count(self) -> int:
        return sum(entry.is_directory for entry in self.entries)

    @property
    def extension_counts(self) -> dict[str, int]:
        """파일 확장자별 수를 정렬된 사전으로 반환합니다.

        확장자는 마지막 점 뒤의 문자열(점을 포함)이며 대소문자를 구분하지 않습니다.
        ``archive.tar.gz``는 ``.gz``로, ``.env``처럼 점으로만 시작하는 이름과
        확장자가 없는 파일은 빈 문자열 키로 집계합니다. 반환 사전의 삽입 순서는
        확장자 이름순으로 결정되어 동일한 보고서에서 항상 같습니다.
        """
        counts: dict[str, int] = {}
        for entry in self.entries:
            if entry.is_directory:
                continue
            extension = Path(entry.path).suffix.casefold()
            counts[extension] = counts.get(extension, 0) + 1
        return {
            extension: counts[extension]
            for extension in sorted(counts, key=_sort_key)
        }


def analyze_directory(
    directory: str | Path,
    mode: str = "text",
    ignore_patterns: tuple[str, ...] = (),
) -> DirectoryReport:
    """`desktop.ini`를 제외한 재귀 구조를 주어진 모드와 함께 수집합니다."""
    if mode not in {"text", "emoji"}:
        raise ValueError("mode는 'text' 또는 'emoji'여야 합니다.")
    root = Path(directory)
    if not root.is_dir():
        raise NotADirectoryError(f"분석할 디렉터리를 찾을 수 없습니다: {root}")
    entries: list[DirectoryEntry] = []

    def visit(current: Path) -> None:
        children = sorted(
            (
                child
                for child in current.iterdir()
                if not child.is_symlink() and child.name.casefold() != "desktop.ini"
            ),
            key=lambda child: _sort_key(child.name),
        )
        for child in children:
            relative = child.relative_to(root).as_posix()
            if _is_ignored(relative, ignore_patterns, child.is_dir()):
                continue
            entry = DirectoryEntry(relative, child.is_dir(), len(child.relative_to(root).parts) - 1)
            entries.append(entry)
            if child.is_dir():
                visit(child)

    visit(root)
    return DirectoryReport(root=root, entries=tuple(entries), mode=mode)


def format_report(report: DirectoryReport) -> str:
    """디렉터리 보고서에 보존된 모드로 트리를 변환합니다."""
    lines = [report.root.name or str(report.root)]
    for entry in report.entries:
        indent = "  " * entry.depth
        if report.mode == "emoji":
            prefix = "📁 " if entry.is_directory else "📄 "
        else:
            prefix = "[D] " if entry.is_directory else "[F] "
        lines.append(f"{indent}{prefix}{Path(entry.path).name}")
    return "\n".join(lines) + "\n"


def write_report(report: DirectoryReport, output_path: str | Path) -> Path:
    """서식화한 트리 보고서를 UTF-8 파일로 저장합니다."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(format_report(report), encoding="utf-8")
    return output


def write_parent_report(report: DirectoryReport, output_path: str | Path) -> Path:
    """각 파일의 상위 경로를 담은 CSV 보고서를 UTF-8로 저장합니다."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["이름", "상위_경로"])
        for entry in report.entries:
            if not entry.is_directory:
                relative = Path(entry.path)
                parent = relative.parent.as_posix()
                writer.writerow([relative.name, "" if parent == "." else parent])
    return output
