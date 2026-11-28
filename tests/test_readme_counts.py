"""Check the README refresh against a changing, indexed corpus."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from test_build_foundation import SynthCorpus, minimal_project

from os_optics_lens.errors import LensError
from scripts.update_readme_counts import update_readme


class ReadmeCountsTest(unittest.TestCase):
    def test_refresh_after_corpus_change(self):
        with TemporaryDirectory() as scratch:
            root = Path(scratch)
            corpus = SynthCorpus(root)
            readme = root / "README.md"
            before = b"# Lens\r\n\r\n<!-- BEGIN INDEX COUNTS -->\r\n"
            after = b"\r\n<!-- END INDEX COUNTS -->\r\n\r\nOther README text.\r\n"
            readme.write_bytes(before + b"old counts" + after)

            configurations = [{"configuration_id": "Wide"}, {"configuration_id": "Tele"}]

            def add_configurations(record):
                record["record_schema_version"] = "1.1"
                record["design"]["configuration_count"] = 2
                shared = {name: record.pop(name) for name in ("first_order", "aperture", "field", "performance")}
                shared["conjugate"] = record["design"].pop("conjugate")
                record["configurations"] = [{**configuration, **shared} for configuration in configurations]

            corpus.add("zoom", project=minimal_project(configurations), mutate=add_configurations)
            self.assertEqual(update_readme(root), "1 searchable record · 2 configurations")
            self.assertEqual(readme.read_bytes(), before + "**1 searchable record · 2 configurations**".encode() + after)

            corpus.add("prime")
            self.assertEqual(update_readme(root), "2 searchable records · 3 configurations")
            expected = before + "**2 searchable records · 3 configurations**".encode() + after
            self.assertEqual(readme.read_bytes(), expected)
            update_readme(root)
            self.assertEqual(readme.read_bytes(), expected)

            (corpus.record_dir("synth", "prime") / "project.json").write_bytes(b"invalid JSON")
            with self.assertRaises(LensError):
                update_readme(root)
            self.assertEqual(readme.read_bytes(), expected)
