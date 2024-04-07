from __future__ import annotations

from pathlib import Path

import pytest

from deptry.python_file_finder import get_all_python_files_in
from tests.utils import run_within_dir


def _get_test_data_directory() -> Path:
    return Path.cwd() / "tests/data/file_finder"


def test_simple() -> None:
    with run_within_dir(_get_test_data_directory()):
        files = get_all_python_files_in(
            (Path(),),
            exclude=(".venv",),
            extend_exclude=("other_dir",),
            using_default_exclude=False,
        )

        assert sorted(files) == [
            Path(".cache/file1.py"),
            Path(".cache/file2.py"),
            Path("another_dir/subdir/file1.py"),
            Path("dir/subdir/file1.ipynb"),
            Path("dir/subdir/file1.py"),
            Path("dir/subdir/file2.py"),
            Path("dir/subdir/file3.py"),
            Path("subdir/file1.py"),
        ]


def test_only_matches_start() -> None:
    """
    Test that adding 'subdir' as exclude argument does not also exclude dir/subdir.
    """
    with run_within_dir(_get_test_data_directory()):
        files = get_all_python_files_in(
            (Path(),), exclude=("foo",), extend_exclude=("subdir",), using_default_exclude=False
        )

        assert sorted(files) == [
            Path(".cache/file1.py"),
            Path(".cache/file2.py"),
            Path("another_dir/subdir/file1.py"),
            Path("dir/subdir/file1.ipynb"),
            Path("dir/subdir/file1.py"),
            Path("dir/subdir/file2.py"),
            Path("dir/subdir/file3.py"),
            Path("other_dir/subdir/file1.py"),
        ]


def test_ignore_notebooks() -> None:
    with run_within_dir(_get_test_data_directory()):
        files = get_all_python_files_in(
            (Path(),), exclude=(), extend_exclude=(), using_default_exclude=False, ignore_notebooks=True
        )

        assert sorted(files) == [
            Path(".cache/file1.py"),
            Path(".cache/file2.py"),
            Path("another_dir/subdir/file1.py"),
            Path("dir/subdir/file1.py"),
            Path("dir/subdir/file2.py"),
            Path("dir/subdir/file3.py"),
            Path("other_dir/subdir/file1.py"),
            Path("subdir/file1.py"),
        ]


@pytest.mark.parametrize(
    ("exclude", "expected"),
    [
        (
            (".*file1",),
            [
                Path(".cache/file2.py"),
                Path("dir/subdir/file2.py"),
                Path("dir/subdir/file3.py"),
            ],
        ),
        (
            (".cache|other.*subdir",),
            [
                Path("another_dir/subdir/file1.py"),
                Path("dir/subdir/file1.ipynb"),
                Path("dir/subdir/file1.py"),
                Path("dir/subdir/file2.py"),
                Path("dir/subdir/file3.py"),
                Path("subdir/file1.py"),
            ],
        ),
        (
            (".*/subdir/",),
            [
                Path(".cache/file1.py"),
                Path(".cache/file2.py"),
                Path("subdir/file1.py"),
            ],
        ),
    ],
)
def test_regex_argument(exclude: tuple[str], expected: list[Path]) -> None:
    with run_within_dir(_get_test_data_directory()):
        files = get_all_python_files_in((Path(),), exclude=exclude, extend_exclude=(), using_default_exclude=False)

        assert sorted(files) == expected


@pytest.mark.parametrize(
    ("exclude", "expected"),
    [
        (
            (".*file1",),
            [
                Path("dir/subdir/file2.py"),
                Path("dir/subdir/file3.py"),
            ],
        ),
        (
            (".*file1|.*file2",),
            [Path("dir/subdir/file3.py")],
        ),
        (
            (".*/subdir/",),
            [],
        ),
    ],
)
def test_multiple_source_directories(exclude: tuple[str], expected: list[Path]) -> None:
    with run_within_dir(_get_test_data_directory()):
        files = get_all_python_files_in(
            (Path("dir"), Path("other_dir")), exclude=exclude, extend_exclude=(), using_default_exclude=False
        )

        assert sorted(files) == expected


def test_duplicates_are_removed() -> None:
    with run_within_dir(_get_test_data_directory()):
        files = get_all_python_files_in((Path(), Path()), exclude=(), extend_exclude=(), using_default_exclude=False)

        assert sorted(files) == [
            Path(".cache/file1.py"),
            Path(".cache/file2.py"),
            Path("another_dir/subdir/file1.py"),
            Path("dir/subdir/file1.ipynb"),
            Path("dir/subdir/file1.py"),
            Path("dir/subdir/file2.py"),
            Path("dir/subdir/file3.py"),
            Path("other_dir/subdir/file1.py"),
            Path("subdir/file1.py"),
        ]
