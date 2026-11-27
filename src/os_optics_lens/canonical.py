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
MAX_JSON_DEPTH = 128
"""Deepest array/object nesting `loads_strict` accepts (the bundled corpus nests at most 8 deep)."""


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
    """True for a finite int or float that is not a bool (an int too large for a double is not)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


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


def _parse_int(token: str) -> Any:
    """An integer literal; one too large for a double (it would overflow every numeric use) is
    rejected like an overflowing float."""
    value = int(token)
    try:
        float(value)
    except OverflowError:
        return _NonFinite(token if len(token) <= 24 else f"{token[:12]}...({len(token)} digits)")
    return value


class _DuplicateKeys(dict):
    """An object that repeated a member name (only built when duplicates are rejected)."""

    duplicate: str = ""


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            marked = _DuplicateKeys(pairs)
            marked.duplicate = key
            return marked
        out[key] = value
    return out


def _has_lone_surrogate(text: str) -> bool:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return True
    return False


def _find_invalid(obj: Any) -> tuple[str, str] | None:
    """(pointer, message) of the first value strict JSON rejects after parsing: a non-finite or
    overflowing number, a string or member name with a lone surrogate (not encodable as UTF-8),
    or nesting deeper than MAX_JSON_DEPTH. Iterative, so any depth is safe to walk."""
    stack: list[tuple[str, Any, int]] = [("", obj, 0)]
    while stack:
        pointer, item, depth = stack.pop()
        if isinstance(item, _NonFinite):
            return pointer, (f"non-finite number {item.token!r} (NaN, Infinity or beyond the double range) "
                             f"is not allowed at {pointer or '/'}")
        if isinstance(item, str):
            if _has_lone_surrogate(item):
                return pointer, f"string at {pointer or '/'} contains a lone surrogate escape (not valid Unicode)"
            continue
        if not isinstance(item, (dict, list)):
            continue
        if isinstance(item, _DuplicateKeys):
            escaped = item.duplicate.replace("~", "~0").replace("/", "~1")
            shown = item.duplicate if len(item.duplicate) <= 80 else item.duplicate[:80] + "..."
            return f"{pointer}/{escaped}", f"duplicate key {shown!r} in the object at {pointer or '/'}"
        if depth >= MAX_JSON_DEPTH:
            return pointer, f"nesting deeper than {MAX_JSON_DEPTH} levels at {pointer or '/'}"
        children: list[tuple[str, Any, int]] = []
        if isinstance(item, dict):
            for key, value in item.items():
                if _has_lone_surrogate(key):
                    return pointer, f"a member name at {pointer or '/'} contains a lone surrogate escape"
                escaped = key.replace("~", "~0").replace("/", "~1")
                children.append((f"{pointer}/{escaped}", value, depth + 1))
        else:
            children = [(f"{pointer}/{index}", value, depth + 1) for index, value in enumerate(item)]
        stack.extend(reversed(children))
    return None


def loads_strict(data: bytes | str, *, reject_duplicate_keys: bool = False) -> Any:
    """Parse strict JSON.

    Bytes must be UTF-8 without a byte-order mark. NaN, Infinity, -Infinity, numbers that overflow
    a double (floats and integers), strings with a lone surrogate escape (`"\\ud800"`) and nesting
    deeper than MAX_JSON_DEPTH are rejected with the JSON pointer of the offending value. With
    `reject_duplicate_keys` (request documents), an object that repeats a member name is rejected
    with the pointer of the repeated member. Raises `JsonFormatError`.
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
        obj = json.loads(text, parse_constant=_NonFinite, parse_float=_parse_float, parse_int=_parse_int,
                         object_pairs_hook=_pairs_without_duplicates if reject_duplicate_keys else None)
    except json.JSONDecodeError as exc:
        raise JsonFormatError(f"invalid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}") from None
    except RecursionError:
        raise JsonFormatError(f"invalid JSON: nesting deeper than {MAX_JSON_DEPTH} levels") from None
    except ValueError as exc:
        raise JsonFormatError(f"invalid JSON: {str(exc)[:200]}") from None
    hit = _find_invalid(obj)
    if hit is not None:
        pointer, message = hit
        raise JsonFormatError(message, pointer or "/")
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
