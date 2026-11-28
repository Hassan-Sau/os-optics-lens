"""Refresh the README's collection counts from a rebuilt Lens index."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from os_optics_lens.build import build_index  # noqa: E402

START = b"<!-- BEGIN INDEX COUNTS -->"
END = b"<!-- END INDEX COUNTS -->"


def update_readme(root: Path) -> str:
    readme = root / "README.md"
    original = readme.read_bytes()
    before, _, tail = original.partition(START)
    block, end, after = tail.partition(END)
    if original.count(START) != 1 or original.count(END) != 1 or not end:
        raise ValueError("README.md must contain one ordered pair of index count markers")

    with TemporaryDirectory() as scratch:
        result = build_index(root, Path(scratch) / "index.sqlite")

    records = "record" if result.records == 1 else "records"
    configurations = "configuration" if result.configurations == 1 else "configurations"
    summary = f"{result.records:,} searchable {records} · {result.configurations:,} {configurations}"
    newline = b"\r\n" if block.startswith(b"\r\n") else b"\n"
    replacement = before + START + newline + f"**{summary}**".encode("utf-8") + newline + END + after
    if replacement != original:
        readme.write_bytes(replacement)
    return summary


if __name__ == "__main__":
    print(update_readme(ROOT))
