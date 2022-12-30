from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Pattern


@dataclass
class PythonFileFinder:
    """
    Get a list of all .py and .ipynb files recursively within a directory.
    Args:
        exclude: A list of regex patterns of paths to ignore.
        extend_exclude: An additional list of regex patterns of paths to ignore.
        ignore_notebooks: If ignore_notebooks is set to True, .ipynb files are ignored and only .py files are returned.
    """

    exclude: tuple[str, ...]
    extend_exclude: tuple[str, ...]
    ignore_notebooks: bool = False

    def get_all_python_files_in(self, directory: Path) -> list[Path]:
        logging.debug("Collecting Python files to scan...")

        source_files = []

        ignore_regex = re.compile("|".join(self.exclude + self.extend_exclude))
        file_lookup_suffixes = {".py"} if self.ignore_notebooks else {".py", ".ipynb"}

        for root_str, dirs, files in os.walk(directory, topdown=True):
            root = Path(root_str)

            if self._is_directory_ignored(root, ignore_regex):
                dirs[:] = []
                continue

            for file_str in files:
                file = root / file_str
                if not self._is_file_ignored(file, file_lookup_suffixes, ignore_regex):
                    source_files.append(file)

        logging.debug("Python files to scan for imports:\n%s\n", "\n".join([str(file) for file in source_files]))

        return source_files

    def _is_directory_ignored(self, directory: Path, ignore_regex: Pattern[str]) -> bool:
        return bool((self.exclude + self.extend_exclude) and ignore_regex.match(str(directory)))

    def _is_file_ignored(self, file: Path, file_lookup_suffixes: set[str], ignore_regex: Pattern[str]) -> bool:
        return bool(
            file.suffix not in file_lookup_suffixes
            or ((self.exclude + self.extend_exclude) and ignore_regex.match(str(file)))
        )
