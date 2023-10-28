from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sys

    if sys.version_info < (3, 12):
        from typing_extensions import override
    else:
        from typing import override
else:

    def override(func):
        return func

    __all__ = ("override",)
