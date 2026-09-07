"""문서 목록과 디렉터리 구조를 가볍게 점검하는 도구입니다."""

__version__ = "0.2.0"

from .core import (
    DirectoryEntry,
    DirectoryReport,
    FileComparison,
    NumberAnalysis,
    analyze_directory,
    analyze_numbers,
    compare_file_names,
    duplicate_names,
    format_report,
    write_parent_report,
    write_report,
)

__all__ = [
    "DirectoryEntry",
    "DirectoryReport",
    "FileComparison",
    "NumberAnalysis",
    "__version__",
    "analyze_directory",
    "analyze_numbers",
    "compare_file_names",
    "duplicate_names",
    "format_report",
    "write_parent_report",
    "write_report",
]
