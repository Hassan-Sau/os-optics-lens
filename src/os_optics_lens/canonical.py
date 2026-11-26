"""Canonical serialization, hashing, JSON value equality and corpus-relative paths.

Everything stored in the index is serialized with `canonical_json` so that builds are reproducible.
Byte hashes of committed files are taken over LF-normalized bytes, so a CRLF checkout hashes the same
as the repository's LF form. `record_hash` follows docs/RECORD_FORMAT.md exactly.
"""

from __future__ import annotations

import hashlib
import json
import math
import posixpath
import re
from typing import Any

HEX64 = re.compile(r"[0-9a-f]{64}")


def canonical_json(obj: Any) -> str:
    """Sorted keys, compact separators, non-ASCII kept, non-finite numbers rejected."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def lf(data: bytes) -> bytes:
    """`data` with CRLF line endings replaced by LF."""
    return data.replace(b"\r\n", b"\n")


def sha256_hex(data: bytes) -> str:
    """Lower-case hex SHA-256 of `data`."""
    return hashlib.sha256(data).hexdigest()


def sha256_lf(data: bytes) -> str:
    """Hex SHA-256 of `data` after CRLF -> LF normalization (the repository's committed form)."""
    return sha256_hex(lf(data))


def sha256_text(text: str) -> str:
    """Hex SHA-256 of `text` encoded as UTF-8."""
    return sha256_hex(text.encode("utf-8"))


def record_hash(record: dict[str, Any]) -> str:
    """The record hash defined by docs/RECORD_FORMAT.md.

    SHA-256 over `json.dumps(body, sort_keys=True, ensure_ascii=False)` encoded as UTF-8, where body is
    the record without `record_hash` and `record_hash_method`. Note the default separators.
    """
    body = {key: value for key, value in record.items() if key not in ("record_hash", "record_hash_method")}
    return sha256_hex(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def is_number(value: Any) -> bool:
    """True for a finite int or float that is not a bool."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def json_equal(a: Any, b: Any) -> bool:
    """JSON value equality.

    Numbers compare by value (0 == 0.0), a bool never equals a number, strings compare exactly,
    lists compare in order and objects compare key-wise. Values of other types are never equal.
    """
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, str) or isinstance(b, str):
        return isinstance(a, str) and isinstance(b, str) and a == b
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(json_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(json_equal(a[key], b[key]) for key in a)
    return False


def canonical_value(obj: Any) -> Any:
    """`obj` with integral finite floats replaced by ints, recursively (bools untouched).

    Two values are `json_equal` exactly when their canonical values serialize identically, which makes
    `canonical_key` usable as a grouping key.
    """
    if isinstance(obj, bool) or obj is None or isinstance(obj, (str, int)):
        return obj
    if isinstance(obj, float):
        return int(obj) if math.isfinite(obj) and obj.is_integer() else obj
    if isinstance(obj, (list, tuple)):
        return [canonical_value(item) for item in obj]
    if isinstance(obj, dict):
        return {key: canonical_value(value) for key, value in obj.items()}
    return obj


def canonical_key(obj: Any) -> str:
    """Canonical JSON of `canonical_value(obj)`: equal strings iff `json_equal` values."""
    return canonical_json(canonical_value(obj))


class JsonFormatError(ValueError):
    """Input is not strict JSON. `pointer` is a JSON pointer to a rejected value when known."""

    def __init__(self, message: str, pointer: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.pointer = pointer


class _NonFinite:
    """Placeholder for a NaN/Infinity literal or an overflowing number found while parsing."""

    __slots__ = ("token",)

    def __init__(self, token: str) -> None:
        self.token = token


def _parse_float(token: str) -> Any:
    value = float(token)
    return value if math.isfinite(value) else _NonFinite(token)


def _find_non_finite(obj: Any, pointer: str = "") -> tuple[str, str] | None:
    if isinstance(obj, _NonFinite):
        return pointer, obj.token
    if isinstance(obj, dict):
        for key, value in obj.items():
            escaped = key.replace("~", "~0").replace("/", "~1")
            hit = _find_non_finite(value, f"{pointer}/{escaped}")
            if hit:
                return hit
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            hit = _find_non_finite(value, f"{pointer}/{index}")
            if hit:
                return hit
    return None


def loads_strict(data: bytes | str) -> Any:
    """Parse strict JSON.

    Bytes must be UTF-8 without a byte-order mark. NaN, Infinity, -Infinity and numbers that overflow
    a double are rejected with the JSON pointer of the offending value. Raises `JsonFormatError`.
    """
    if isinstance(data, bytes):
        if data.startswith(b"\xef\xbb\xbf"):
            raise JsonFormatError("file starts with a UTF-8 byte-order mark; save it as UTF-8 without BOM")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise JsonFormatError(f"not valid UTF-8 at byte {exc.start}") from None
    else:
        text = data
    try:
        obj = json.loads(text, parse_constant=_NonFinite, parse_float=_parse_float)
    except json.JSONDecodeError as exc:
        raise JsonFormatError(f"invalid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}") from None
    except (ValueError, RecursionError) as exc:
        raise JsonFormatError(f"invalid JSON: {exc}") from None
    hit = _find_non_finite(obj)
    if hit is not None:
        pointer, token = hit
        raise JsonFormatError(f"non-finite number {token!r} is not allowed at {pointer or '/'}", pointer or "/")
    return obj


WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


def corpus_relative_path(path: Any) -> str | None:
    """The normalized corpus-relative POSIX form of a referenced path, or None if it is not one.

    Rejected: non-strings, empty strings, NUL or backslash characters, absolute paths, Windows drive
    paths, and paths that normalize to the corpus root or outside it (`..`).
    """
    if not isinstance(path, str) or not path or "\x00" in path or "\\" in path:
        return None
    if path.startswith("/") or WINDOWS_DRIVE.match(path):
        return None
    normalized = posixpath.normpath(path)
    if normalized in (".", "..") or normalized.startswith("../"):
        return None
    return normalized
