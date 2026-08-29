"""Consistency checks for the manufacturing handoff dossier."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BASELINE_PATH = ROOT / "manufacturing" / "baseline.json"
CANDIDATE_PATH = ROOT / "manufacturing" / "candidate-n16.json"
CITATION_PATH = ROOT / "CITATION.cff"
REQUIREMENT_PATTERN = re.compile(r"REQ-[A-Z]+-\d{3}")
LOCAL_LINK_PATTERN = re.compile(r"\[[^]]+\]\((?!https?://|#)([^)]+)\)")


class ManufacturingDocsTests(unittest.TestCase):
    def test_required_handoff_documents_exist(self) -> None:
        required = {
            "README.md",
            "01-product-requirements.md",
            "02-numerical-specification.md",
            "03-architecture-and-interfaces.md",
            "04-memory-streaming-and-dma.md",
            "05-clock-reset-power-dft.md",
            "06-physical-design.md",
            "07-verification-and-signoff.md",
            "08-manufacturing-handoff.md",
            "09-risk-register.md",
            "10-traceability-matrix.md",
            "11-release-and-git.md",
            "12-magic-tech-selection.md",
            "13-design-space-exploration.md",
        }
        self.assertEqual(required, {path.name for path in DOCS.glob("*.md")})

    def test_baseline_architecture_is_self_consistent(self) -> None:
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        architecture = baseline["architecture"]
        data_format = baseline["data_format"]
        unique_reads = architecture["lanes"] + architecture["taps"] - 1
        self.assertEqual(2 * unique_reads, architecture["banks"])
        self.assertEqual(
            architecture["lanes"] * data_format["sample_bits"],
            architecture["input_stream_bits"],
        )
        self.assertEqual(
            architecture["lanes"] * data_format["sample_bits"],
            architecture["output_stream_bits"],
        )
        self.assertEqual(data_format["sample_bits"], architecture["bank_word_bits"])
        self.assertEqual("pre-tapeout", baseline["release_status"])

    def test_n16_candidate_is_self_consistent(self) -> None:
        candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
        architecture = candidate["architecture"]
        sizing = candidate["sizing_assumptions"]
        unique_reads = architecture["lanes"] + architecture["taps"] - 1
        self.assertEqual(unique_reads, architecture["unique_reads_per_issue"])
        self.assertEqual(2 * unique_reads, architecture["single_port_banks"])
        self.assertEqual(
            architecture["single_port_banks"]
            - unique_reads
            - architecture["prefetch_writes_per_cycle"],
            architecture["idle_banks_per_cycle"],
        )
        self.assertEqual(
            architecture["lanes"] * architecture["taps"],
            architecture["multicast_endpoints"],
        )
        self.assertEqual(144, sizing["capacity_kib_total_ab"])

    def test_citation_file_has_repository_identity(self) -> None:
        citation = CITATION_PATH.read_text(encoding="utf-8")
        for field in (
            "cff-version: 1.2.0",
            "title: \"Banked Stencil Multicast\"",
            "repository-code: \"https://github.com/HN19781124/banked-stencil-multicast\"",
            "family-names: Namiki",
        ):
            self.assertIn(field, citation)

    def test_every_requirement_has_traceability(self) -> None:
        requirements = (DOCS / "01-product-requirements.md").read_text(encoding="utf-8")
        traceability = (DOCS / "10-traceability-matrix.md").read_text(encoding="utf-8")
        requirement_ids = set(REQUIREMENT_PATTERN.findall(requirements))
        traced_ids = set(REQUIREMENT_PATTERN.findall(traceability))
        self.assertGreaterEqual(len(requirement_ids), 40)
        self.assertEqual(requirement_ids, traced_ids)

    def test_local_markdown_links_resolve(self) -> None:
        documents = [
            ROOT / "README.md",
            ROOT / "VALIDATION.md",
            ROOT / "LICENSE-DOCUMENTATION.md",
            *DOCS.rglob("*.md"),
            *(ROOT / "manufacturing").rglob("*.md"),
            *(ROOT / "physical").rglob("*.md"),
        ]
        for document in documents:
            content = document.read_text(encoding="utf-8")
            for target in LOCAL_LINK_PATTERN.findall(content):
                path = (document.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(path.exists(), f"broken link in {document}: {target}")

    def test_release_automation_is_present(self) -> None:
        workflow = ROOT / ".github" / "workflows" / "verify.yml"
        self.assertTrue(workflow.is_file())
        content = workflow.read_text(encoding="utf-8")
        self.assertIn("tools/verify.py --bootstrap --require-rtl", content)
        self.assertIn("verification-report.json", content)


if __name__ == "__main__":
    unittest.main()
