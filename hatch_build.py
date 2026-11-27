"""Hatchling build hook: bundle the corpus and its index into the wheel (spec §8, amendment 10.20).

For a standard wheel build only (target ``wheel``, version ``standard``) the hook:

1. imports the index builder from this project's ``src/`` (never from an installed copy);
2. loads and validates the source corpus at the project root strictly; any error finding fails the
   wheel build with the findings listed;
3. writes a bundled corpus into a temporary directory: an LF-normalized, hash-verified copy of every
   indexed ``record.json`` and ``project.json``, every verified evidence extract, every batch manifest
   (``records/*/batch-*.json``), ``LICENSE``, ``licenses/*`` and ``acceptance/*.json``, each at its
   repository-relative path;
4. builds ``index.sqlite`` from that bundled corpus with ``os_optics_lens.build.build_index`` and
   checks that its snapshot_id equals the snapshot_id of an index built from the source tree, so the
   bundle provably holds everything the index reads;
5. adds the files through ``build_data["force_include"]`` as ``os_optics_lens/_data/index.sqlite`` and
   ``os_optics_lens/_data/corpus/<repository-relative path>``.

``finalize`` removes the temporary directory. Editable installs and the sdist get no ``_data``; they
use ``--index`` or ``OS_OPTICS_LENS_INDEX``.

The bundling functions do not need hatchling: ``python hatch_build.py --out DIR`` writes
``DIR/corpus/**`` and ``DIR/index.sqlite`` and prints a JSON summary.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

try:
    from hatchling.builders.hooks.plugin.interface import BuildHookInterface
except ImportError:  # standalone use (`python hatch_build.py`) without hatchling installed
    BuildHookInterface = object  # type: ignore[assignment,misc]

PACKAGE = "os_optics_lens"
DATA_DIR = f"{PACKAGE}/_data"
CORPUS_DIR = f"{DATA_DIR}/corpus"
INDEX_FILE = f"{DATA_DIR}/index.sqlite"
MAX_REPORTED_FINDINGS = 25


class BundleError(Exception):
    """The corpus cannot be bundled; the message names every cause."""


class BundleResult:
    """A bundled corpus and the index built from it.

    `files` maps each bundled repository-relative POSIX path to the SHA-256 of its LF-normalized
    bytes; `corpus_dir` holds them at those paths. `snapshot_id` is the snapshot of `index_path`,
    which equals the snapshot of an index built from the source tree.

    (Plain classes, not dataclasses: hatchling loads this file without registering it in
    sys.modules, which dataclasses require.)
    """

    def __init__(self, corpus_dir: Path, index_path: Path, snapshot_id: str, records: int,
                 configurations: int, files: dict[str, str]) -> None:
        self.corpus_dir = corpus_dir
        self.index_path = index_path
        self.snapshot_id = snapshot_id
        self.records = records
        self.configurations = configurations
        self.files = files

    def summary(self) -> dict[str, Any]:
        """JSON-serializable summary (counts by top-level directory, no absolute paths except outputs)."""
        groups: dict[str, int] = {}
        for path in self.files:
            top = path.split("/", 1)[0] if "/" in path else path
            groups[top] = groups.get(top, 0) + 1
        return {
            "snapshot_id": self.snapshot_id,
            "records": self.records,
            "configurations": self.configurations,
            "bundled_files": len(self.files),
            "bundled_files_by_top_level": dict(sorted(groups.items())),
            "corpus_dir": str(self.corpus_dir),
            "index_path": str(self.index_path),
        }


class _Builder:
    """The project's own builder modules, imported from `src/`."""

    def __init__(self, build: ModuleType, corpus: ModuleType, canonical: ModuleType, errors: ModuleType) -> None:
        self.build = build
        self.corpus = corpus
        self.canonical = canonical
        self.errors = errors


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _import_builder(project_root: Path) -> _Builder:
    """Import `os_optics_lens.{build,corpus,canonical,errors}` from `<project_root>/src`.

    Any already-imported `os_optics_lens` modules that do not come from that directory are dropped
    first, so the bundle is always built by the code being packaged.
    """
    src = (project_root / "src").resolve()
    package_dir = src / PACKAGE
    if not (package_dir / "__init__.py").is_file():
        raise BundleError(f"{package_dir} is not the {PACKAGE} package source")
    for name in [n for n in sys.modules if n == PACKAGE or n.startswith(PACKAGE + ".")]:
        origin = getattr(sys.modules[name], "__file__", None)
        if origin is None or package_dir not in Path(origin).resolve().parents:
            del sys.modules[name]
    sys.path.insert(0, str(src))
    try:
        modules = {name: importlib.import_module(f"{PACKAGE}.{name}")
                   for name in ("build", "corpus", "canonical", "errors")}
    finally:
        sys.path.remove(str(src))
    return _Builder(**modules)


def _describe_build_error(exc: Exception) -> str:
    """One readable message for a LensError raised by the builder (BUILD_FAILED lists findings)."""
    code = getattr(exc, "code", type(exc).__name__)
    lines = [f"{code}: {exc}"]
    hint = getattr(exc, "hint", None)
    if hint:
        lines.append(f"hint: {hint}")
    details = getattr(exc, "details", None) or {}
    findings = details.get("findings") or []
    for item in findings[:MAX_REPORTED_FINDINGS]:
        lines.append(f"  {item.get('severity')} {item.get('code')} {item.get('file')} "
                     f"{item.get('field') or '-'}: {item.get('message')}")
    if len(findings) > MAX_REPORTED_FINDINGS:
        lines.append(f"  ... and {len(findings) - MAX_REPORTED_FINDINGS} more finding(s)")
    return "\n".join(lines)


def _collect(project_root: Path, builder: _Builder) -> dict[str, bytes]:
    """The bundled corpus: repository-relative POSIX path -> LF-normalized, verified bytes.

    Raises BundleError when the corpus has an error finding or a copied file fails verification.
    """
    corpus = builder.corpus.load_corpus(project_root)
    if corpus.errors:
        lines = [f"the corpus has {len(corpus.errors)} error finding(s):"]
        lines.extend(f"  {e.code} {e.file} {e.field or '-'}: {e.message}"
                     for e in corpus.errors[:MAX_REPORTED_FINDINGS])
        raise BundleError("\n".join(lines))

    canonical = builder.canonical
    files: dict[str, bytes] = {}
    problems: list[str] = []

    for record in corpus.records:
        data = _lf((project_root / record.file).read_bytes())
        parsed = canonical.loads_strict(data)
        if canonical.record_hash(parsed) != parsed.get("record_hash") or parsed.get("record_id") != record.record_id:
            problems.append(f"{record.file}: record_hash or record_id changed while bundling")
        files[record.file] = data
        project = _lf((project_root / record.project_path).read_bytes())
        if _sha256(project) != record.project_sha256 or project != record.project_bytes:
            problems.append(f"{record.project_path}: native Project changed while bundling")
        files[record.project_path] = project

    for path, (digest, content) in corpus.evidence_files.items():
        if _sha256(content) != digest:
            problems.append(f"{path}: evidence bytes do not match their verified SHA-256")
        files[path] = content

    for path, text in corpus.licenses.items():
        files[path] = text.encode("utf-8")

    extra: list[Path] = []
    extra.extend(sorted((project_root / "records").glob("*/batch-*.json")))
    licenses_dir = project_root / "licenses"
    if licenses_dir.is_dir():
        extra.extend(sorted(p for p in licenses_dir.iterdir() if p.is_file()))
    acceptance_dir = project_root / "acceptance"
    if acceptance_dir.is_dir():
        extra.extend(sorted(acceptance_dir.glob("*.json")))
    for path in extra:
        if not path.is_file():
            continue
        rel = path.relative_to(project_root).as_posix()
        content = _lf(path.read_bytes())
        if rel in files and files[rel] != content:
            problems.append(f"{rel}: bytes differ from the copy the index verified")
        files.setdefault(rel, content)

    if problems:
        raise BundleError("bundle verification failed:\n" + "\n".join(f"  {p}" for p in problems))
    return dict(sorted(files.items()))


def bundle_corpus(project_root: Path | str, out_dir: Path | str) -> BundleResult:
    """Write the bundled corpus to `out_dir/corpus` and its index to `out_dir/index.sqlite`.

    The source corpus is validated strictly; the index is built from the bundled copy and must have
    the same snapshot_id as an index built from the source tree. Raises BundleError otherwise.
    `out_dir` must not exist or be empty.
    """
    root = Path(project_root).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise BundleError(f"{out} must be empty")
    builder = _import_builder(root)
    lens_error = builder.errors.LensError

    reference_dir = Path(tempfile.mkdtemp(prefix="os-optics-lens-reference-"))
    try:
        try:
            reference = builder.build.build_index(root, reference_dir / "source.sqlite")
        except lens_error as exc:
            raise BundleError("the source corpus does not build:\n" + _describe_build_error(exc)) from None
    finally:
        shutil.rmtree(reference_dir, ignore_errors=True)

    files = _collect(root, builder)
    corpus_dir = out / "corpus"
    digests: dict[str, str] = {}
    for rel, content in files.items():
        target = corpus_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        written = target.read_bytes()
        if written != content:
            raise BundleError(f"{rel}: bundled copy differs from the verified bytes")
        digests[rel] = _sha256(written)

    index_path = out / "index.sqlite"
    try:
        result = builder.build.build_index(corpus_dir, index_path)
    except lens_error as exc:
        raise BundleError("the bundled corpus does not build:\n" + _describe_build_error(exc)) from None
    if result.snapshot_id != reference.snapshot_id:
        raise BundleError(
            f"the bundled index snapshot {result.snapshot_id} differs from the source-tree snapshot "
            f"{reference.snapshot_id}: the bundle is missing or alters a file the index reads")
    return BundleResult(corpus_dir, index_path, result.snapshot_id, result.records, result.configurations, digests)


class CustomBuildHook(BuildHookInterface):  # type: ignore[misc,valid-type]
    """Adds the bundled corpus and index to standard wheels; does nothing for other targets."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Build the bundle into a temporary directory and force-include it under `_data/`."""
        self._temp_dir: str | None = None
        if self.target_name != "wheel" or version != "standard":
            return
        self._temp_dir = tempfile.mkdtemp(prefix="os-optics-lens-wheel-")
        try:
            result = bundle_corpus(self.root, Path(self._temp_dir) / "bundle")
        except BundleError as exc:
            self._cleanup()
            raise RuntimeError(f"os-optics-lens wheel build failed:\n{exc}") from None
        except BaseException:
            self._cleanup()
            raise
        force_include = build_data.setdefault("force_include", {})
        force_include[str(result.index_path)] = INDEX_FILE
        for rel in result.files:
            force_include[str(result.corpus_dir / rel)] = f"{CORPUS_DIR}/{rel}"
        self.app.display_info(
            f"os-optics-lens: bundled {result.records} records, {len(result.files)} corpus files, "
            f"index snapshot {result.snapshot_id}")

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        """Remove the temporary bundle directory."""
        self._cleanup()

    def _cleanup(self) -> None:
        temp_dir = getattr(self, "_temp_dir", None)
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
            self._temp_dir = None


def main(argv: list[str] | None = None) -> int:
    """`python hatch_build.py --out DIR [--root DIR]`: write the bundle and print a JSON summary."""
    import argparse

    parser = argparse.ArgumentParser(description="Write the wheel's bundled corpus and index to a directory.")
    parser.add_argument("--out", required=True, help="empty or new output directory")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent),
                        help="project root containing records/ and src/ (default: this file's directory)")
    args = parser.parse_args(argv)
    try:
        result = bundle_corpus(args.root, args.out)
    except BundleError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps({"ok": True, **result.summary()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
