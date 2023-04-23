from __future__ import annotations

import ast
import itertools
import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from deptry.imports.extractors.base import ImportExtractor

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class NotebookImportExtractor(ImportExtractor):
    """Extract import statements from a Jupyter notebook."""

    def extract_imports(self) -> set[str]:
        """Extract the imported top-level modules from all code cells in the Jupyter Notebook."""
        notebook = self._read_ipynb_file(self.file)
        if not notebook:
            return set()

        cells = self._keep_code_cells(notebook)
        import_statements = [self._extract_import_statements_from_cell(cell) for cell in cells]
        tree = ast.parse("\n".join(itertools.chain.from_iterable(import_statements)), str(self.file))
        return self._extract_imports_from_ast(tree)

    @classmethod
    def _read_ipynb_file(cls, path_to_ipynb: Path) -> dict[str, Any] | None:
        try:
            with open(path_to_ipynb) as ipynb_file:
                notebook: dict[str, Any] = json.load(ipynb_file)
        except (UnicodeDecodeError, ValueError):
            try:
                with open(path_to_ipynb, encoding=cls._get_file_encoding(path_to_ipynb)) as ipynb_file:
                    notebook = json.load(ipynb_file, strict=False)
            except UnicodeDecodeError:
                logging.warning(f"Warning: File {path_to_ipynb} could not be decoded. Skipping...")
                return None
        return notebook

    @staticmethod
    def _keep_code_cells(notebook: dict[str, Any]) -> list[dict[str, Any]]:
        return [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]

    @staticmethod
    def _contains_import_statements(line: str) -> bool:
        return re.search(r"^(?:from\s+(\w+)(?:\.\w+)?\s+)?import\s+([^\s,.]+)(?:\.\w+)?", line) is not None

    @classmethod
    def _extract_import_statements_from_cell(cls, cell: dict[str, Any]) -> list[str]:
        return [line for line in cell["source"] if cls._contains_import_statements(line)]
