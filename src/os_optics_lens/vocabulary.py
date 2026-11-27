"""Controlled search vocabulary: facets, canonical terms, aliases, lens-type mapping, stop dependence.

The data lives in `vocabulary.json` next to this module. `load_vocabulary()` returns a cached,
read-only `Vocabulary`. Terms are matched after `normalize_term` (lower case, spaces and hyphens to
underscores). The vocabulary digest is the SHA-256 of its canonical JSON and is part of the index
snapshot identity.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

from .canonical import canonical_json, loads_strict, sha256_text
from .errors import LensError

RECORD_BASIS = "RECORD"
MAPPING_BASIS = "VOCABULARY_MAPPING"


def normalize_term(term: str) -> str:
    """Lower-case `term`, trim it and replace spaces and hyphens with underscores."""
    return term.strip().lower().replace(" ", "_").replace("-", "_")


@dataclass(frozen=True)
class LensTypeMapping:
    """What a source lens type contributes: a design type (or None) and added applications."""

    design_type: str | None
    applications: tuple[str, ...]


class Vocabulary:
    """Read-only view of `vocabulary.json`."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.digest = sha256_text(canonical_json(data))
        self.facets: dict[str, dict[str, Any]] = data["facets"]
        self._terms: dict[str, tuple[str, ...]] = {
            facet: tuple(terms) for facet, terms in data.get("terms", {}).items()
        }
        self._aliases: dict[str, dict[str, str]] = data.get("aliases", {})
        self._ambiguous: dict[str, dict[str, list[str]]] = data.get("ambiguous", {})
        self._lens_types: dict[str, dict[str, Any]] = data.get("lens_type_mapping", {})
        self._design_type_functions: dict[str, list[str]] = data.get("design_type_functions", {})
        stop = data.get("stop_dependent", {})
        self.stop_dependent_sections: frozenset[str] = frozenset(stop.get("sections", []))
        self.stop_dependent_facts: frozenset[str] = frozenset(stop.get("facts", []))
        self.stop_independent: frozenset[str] = frozenset(data.get("stop_independent", []))
        self.fact_extraction: dict[str, Any] = data.get("fact_extraction", {})

    # Facets -------------------------------------------------------------------------------------

    def facet_names(self) -> list[str]:
        """All facet names, sorted."""
        return sorted(self.facets)

    def has_facet(self, facet: str) -> bool:
        """True when `facet` is a known facet name."""
        return facet in self.facets

    def facet_description(self, facet: str) -> str:
        """The one-line English description of `facet`."""
        return self.facets[facet]["description"]

    def facet_level(self, facet: str) -> str:
        """`record` or `configuration`: the scope a facet value applies to."""
        return self.facets[facet]["level"]

    def is_controlled(self, facet: str) -> bool:
        """True when the facet's values come from the vocabulary's canonical terms."""
        return bool(self.facets.get(facet, {}).get("controlled"))

    def warns_unknown(self, facet: str) -> bool:
        """True when a record value outside the vocabulary yields an UNKNOWN_TERM warning."""
        return bool(self.facets.get(facet, {}).get("warn_unknown"))

    def canonical_terms(self, facet: str) -> tuple[str, ...]:
        """The canonical terms of a controlled facet (empty for uncontrolled facets)."""
        return self._terms.get(facet, ())

    def is_known_term(self, facet: str, value: str) -> bool:
        """True when `value` is a canonical term of `facet`."""
        return value in self._terms.get(facet, ())

    def aliases(self, facet: str) -> dict[str, str]:
        """Alias -> canonical term for `facet`."""
        return dict(self._aliases.get(facet, {}))

    def resolve_term(self, facet: str, value: str) -> tuple[str, bool]:
        """Resolve a requested facet value to its canonical form.

        Returns `(term, via_alias)`. The value is normalized first; an alias maps to its canonical
        term; anything else is returned normalized (the caller decides whether it exists). An
        ambiguous phrase raises `AMBIGUOUS_TERM` listing the specific terms to use instead.
        Uncontrolled facets (collection, family, source_lens_type, ...) are matched verbatim.
        """
        if not self.is_controlled(facet) and facet not in self._aliases:
            return value, False
        term = normalize_term(value)
        choices = self._ambiguous.get(facet, {}).get(term)
        if choices:
            raise LensError(
                "AMBIGUOUS_TERM",
                f"{value!r} is ambiguous for facet {facet!r}",
                hint="Use one of the specific terms: " + ", ".join(choices),
                details={"facet": facet, "value": value, "candidates": list(choices)},
            )
        alias = self._aliases.get(facet, {}).get(term)
        if alias is not None:
            return alias, True
        return term, False

    def close_terms(self, facet: str, value: str, present: list[str], limit: int = 5) -> list[str]:
        """Up to `limit` values from `present` and the facet's canonical terms closest to `value`."""
        pool = sorted(set(present) | set(self._terms.get(facet, ())) | set(self._aliases.get(facet, {})))
        return difflib.get_close_matches(normalize_term(value), pool, n=limit, cutoff=0.5)

    # Record mapping ---------------------------------------------------------------------------

    def map_lens_type(self, lens_type: str) -> LensTypeMapping | None:
        """The mapping for a source lens type (matched after normalization), or None if unknown."""
        entry = self._lens_types.get(lens_type)
        if entry is None:
            entry = self._lens_types.get(normalize_term(lens_type))
        if entry is None:
            return None
        return LensTypeMapping(entry.get("design_type"), tuple(entry.get("application", ())))

    def design_type_functions(self, design_type: str) -> tuple[str, ...]:
        """Functions implied by a design type when the record states no function tags."""
        return tuple(self._design_type_functions.get(design_type, ()))

    def canonical_record_term(self, facet: str, value: str) -> tuple[str, str, bool]:
        """Map a record-supplied tag to `(term, basis, known)`.

        A canonical term keeps basis RECORD; an alias maps to its canonical term with basis
        VOCABULARY_MAPPING; an unknown value is kept normalized with basis RECORD and `known` False.
        """
        term = normalize_term(value)
        if term in self._terms.get(facet, ()):
            return term, RECORD_BASIS, True
        alias = self._aliases.get(facet, {}).get(term)
        if alias is not None:
            return alias, MAPPING_BASIS, True
        return term, RECORD_BASIS, False

    # Stop dependence --------------------------------------------------------------------------

    def is_stop_dependent(self, fact_key: str) -> bool:
        """True when the fact (`section.member` or `performance.<metric>`) needs a blocking stop.

        Every member of a stop-dependent section (aperture) is stop-dependent unless listed in
        `stop_independent`; listed performance metrics are stop-dependent. Longer paths are judged
        by their first two segments.
        """
        segments = fact_key.split(".")
        if len(segments) < 2:
            return False
        key = ".".join(segments[:2])
        if key in self.stop_dependent_facts:
            return True
        return segments[0] in self.stop_dependent_sections and key not in self.stop_independent

    def stop_dependent_prefix(self, segments: list[str]) -> str | None:
        """The first prefix of a dotted path (as segments) naming a stop-dependent fact, or None."""
        if len(segments) >= 2 and self.is_stop_dependent(".".join(segments[:2])):
            return ".".join(segments[:2])
        return None

    def stop_dependent_list(self) -> dict[str, list[str]]:
        """The stop-dependence rules as data (sections, facts, stop_independent)."""
        return {
            "sections": sorted(self.stop_dependent_sections),
            "facts": sorted(self.stop_dependent_facts),
            "stop_independent": sorted(self.stop_independent),
        }

    def describe(self) -> dict[str, Any]:
        """Facet descriptions with canonical terms and aliases, for help output."""
        out: dict[str, Any] = {}
        for facet in self.facet_names():
            entry: dict[str, Any] = {
                "level": self.facet_level(facet),
                "description": self.facet_description(facet),
            }
            if self.canonical_terms(facet):
                entry["terms"] = list(self.canonical_terms(facet))
            if self._aliases.get(facet):
                entry["aliases"] = dict(sorted(self._aliases[facet].items()))
            if self._ambiguous.get(facet):
                entry["ambiguous"] = {k: list(v) for k, v in sorted(self._ambiguous[facet].items())}
            out[facet] = entry
        return out


@lru_cache(maxsize=1)
def load_vocabulary() -> Vocabulary:
    """The packaged vocabulary (cached)."""
    data = loads_strict(resources.files(__package__).joinpath("vocabulary.json").read_bytes().replace(b"\r\n", b"\n"))
    return Vocabulary(data)


def vocabulary_digest() -> str:
    """SHA-256 of the canonical JSON of the packaged vocabulary."""
    return load_vocabulary().digest
