"""자동화 산출물을 손상 없이 교체하는 공통 파일 유틸리티."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def atomic_json_write(path: str | os.PathLike[str], payload: Any, *, indent: int = 2) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.parent / f".{target.name}.{os.getpid()}.{time.time_ns()}.tmp"
    fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=indent)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, target)
    except Exception:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise
