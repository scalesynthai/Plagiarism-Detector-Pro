import io
import json
import unittest

import docx
from pypdf import PdfWriter

from core.citation_quality import CitationQualityReviewer
from core.extractor import extract_document, normalize_with_offset_map
from core.style_review import WritingStyleReviewer


class WritingStyleReviewTests(unittest.TestCase):
    def setUp(self):
        self.reviewer = WritingStyleReviewer()

    def test_registry_is_versioned_and_complete(self):
        registry = self.reviewer.registry
        self.assertEqual(registry["ruleset_version"], "1.0.0")
        self.assertEqual(registry["review_date"], "2026-10-03")
        required = {"id", "category", "display_name", "description", "examples", "detector_type", "applicable_block_types", "language", "patterns", "minimum_occurrences", "frequency_per_1000", "evidence_strength", "category_contribution_cap", "contextual_exclusions", "source", "review_date", "enabled"}
        for rule in registry["rules"]:
            self.assertFalse(required - set(rule), rule["id"])

    def test_unicode_dash_types_are_distinct(self):
        text = ("The interval was 2019–2021. The result—after review—was retained. A well-tested method used ISO-8601. ") * 14
        result = self.reviewer.analyze(text)
        metrics = result["punctuation_metrics"]
        self.assertEqual(metrics["em_dash_count"], 28)
        self.assertEqual(metrics["en_dash_count"], 14)
        self.assertGreaterEqual(metrics["hyphen_minus_count"], 28)
        self.assertLessEqual(next(row for row in result["category_breakdown"] if row["category"] == "punctuation")["cap"], 4)

    def test_word_boundaries_inflections_and_overlap_deduplication(self):
        text = ("The authors delved into a robust model. The model is pivotal. ") * 8 + "Undelved strings should remain unflagged."
        result = self.reviewer.analyze(text)
        metrics = result["rule_metrics"]["inflated_vocabulary"]
        self.assertEqual(metrics["eligible_count"], 24)
        keys = {(row["rule_id"], row["block_id"], row["start_offset"], row["end_offset"]) for row in result["findings"]}
        self.assertEqual(len(keys), len(result["findings"]))

    def test_normalization_maps_back_to_original(self):
        original = "Office ﬁles use a ligature."
        normalized, offsets = normalize_with_offset_map(original)
        self.assertIn("files", normalized)
        start = normalized.index("files")
        self.assertEqual(original[offsets[start]], "ﬁ")
        self.assertEqual(len(normalized), len(offsets))

    def test_quotation_reference_and_code_findings_are_inspectable_but_excluded(self):
        blocks = [
            {"id": "q", "type": "quotation", "text": "As an AI language model, I hope this helps.", "start_offset": 0, "end_offset": 45, "page": None, "metadata": {}},
            {"id": "c", "type": "code", "text": "turn0search0", "start_offset": 47, "end_offset": 59, "page": None, "metadata": {}},
            {"id": "r", "type": "reference", "text": "Robust Methods. 2024.", "start_offset": 61, "end_offset": 82, "page": None, "metadata": {}},
        ]
        text = "As an AI language model, I hope this helps.\n\nturn0search0\n\nRobust Methods. 2024."
        result = self.reviewer.analyze(text, {"blocks": blocks, "extraction_status": "ok"})
        self.assertTrue(result["findings"])
        self.assertTrue(all(row["excluded_from_score"] for row in result["findings"]))

    def test_repeated_rhetoric_contributes_but_single_em_dash_does_not_drive_index(self):
        human = "The archival record—although incomplete—supports the stated date. " + "The report identifies a source and explains the limitation. " * 20
        human_result = self.reviewer.analyze(human)
        punctuation = next(row for row in human_result["category_breakdown"] if row["category"] == "punctuation")
        self.assertLessEqual(punctuation["points"], 4)
        repeated = ("The result is not just useful, but also transformative. ") * 8 + ("It offers clarity, consistency, and control. ") * 8
        repeated_result = self.reviewer.analyze(repeated)
        self.assertTrue(repeated_result["rule_metrics"]["negative_parallelism"]["threshold_met"])
        self.assertEqual(repeated_result["rule_metrics"]["negative_parallelism"]["eligible_count"], 8)
        self.assertTrue(repeated_result["rule_metrics"]["rule_of_three"]["threshold_met"])

    def test_short_and_unsupported_language_reports_are_not_clean_scores(self):
        short = self.reviewer.analyze("A short human sentence—with one dash.")
        self.assertIsNone(short["style_pattern_index"])
        self.assertIn("Insufficient text", short["recommendation"])
        non_english = self.reviewer.analyze("这是一个中文段落，用于验证有限覆盖范围。" * 20)
        self.assertEqual(non_english["language_coverage"]["coverage"], "limited")
        self.assertTrue(non_english["extraction_warnings"])

    def test_category_caps_and_no_authorship_verdict(self):
        result = self.reviewer.analyze(("Furthermore, this robust and transformative system is a vibrant testament to progress. ") * 100)
        self.assertTrue(all(row["points"] <= row["cap"] for row in result["category_breakdown"]))
        serialized = json.dumps(result).lower()
        self.assertNotIn("misconduct verdict", serialized)
        self.assertIn("do not establish authorship", result["disclaimer"].lower())

    def test_docx_blocks_preserve_formatting_without_claiming_pages(self):
        document = docx.Document()
        document.add_heading("Results", level=2)
        paragraph = document.add_paragraph()
        paragraph.add_run("Important").bold = True
        paragraph.add_run(" evidence remains contextual.").italic = True
        stream = io.BytesIO()
        document.save(stream)
        stream.seek(0)
        extracted = extract_document(stream, "sample.docx")
        self.assertEqual(extracted["extraction_status"], "ok")
        self.assertFalse(extracted["pagination_available"])
        self.assertTrue(any(block["type"] == "heading" for block in extracted["blocks"]))
        self.assertTrue(any(block["metadata"].get("bold_spans") for block in extracted["blocks"]))
        self.assertFalse(any("pagination" in warning.lower() for warning in extracted["warnings"]))

    def test_scanned_pdf_requires_ocr(self):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        stream = io.BytesIO()
        writer.write(stream)
        stream.seek(0)
        extracted = extract_document(stream, "scan.pdf")
        self.assertEqual(extracted["extraction_status"], "empty_requires_ocr")
        self.assertIn("OCR", " ".join(extracted["warnings"]))

    def test_invalid_isbn_and_network_failure_distinction(self):
        self.assertTrue(CitationQualityReviewer.valid_isbn("978-0-306-40615-7"))
        self.assertFalse(CitationQualityReviewer.valid_isbn("978-0-306-40615-8"))
        result = CitationQualityReviewer.analyze("ISBN 978-0-306-40615-8", {"bibliography_entries": []})
        self.assertTrue(any(row["code"] == "invalid_isbn_checksum" for row in result["issues"]))
        self.assertEqual(result["network_verification"]["status"], "not_requested")
        self.assertIn("unreachable", result["network_verification"]["available_states"])


if __name__ == "__main__":
    unittest.main()
