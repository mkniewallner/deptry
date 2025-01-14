from __future__ import annotations

import pytest
from click.testing import CliRunner

from deptry.cli import cli


@pytest.mark.benchmark
def test_cli() -> None:
    result = CliRunner().invoke(cli, "tests/fixtures/project_with_uv")
    assert result.exit_code is True
