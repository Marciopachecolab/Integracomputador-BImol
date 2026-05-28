from __future__ import annotations

import os
from typing import Protocol


class SupportsFlushAndFsync(Protocol):
    def flush(self) -> None: ...

    def fileno(self) -> int: ...


def flush_and_fsync(handle: SupportsFlushAndFsync) -> None:
    """Force buffered writes to disk before atomic replace operations."""
    handle.flush()
    os.fsync(handle.fileno())


__all__ = ["SupportsFlushAndFsync", "flush_and_fsync"]
