"""Configurable, evidence-first writing-style review.

The rules describe patterns that can occur in both human and AI-assisted text.
They are not an authorship classifier and must not be used as a misconduct verdict.
"""

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


RULES_PATH = Path(__file__).resolve().parents[1] / "config" / "writing_style_rules.v1.json"
ELIGIBLE_BLOCKS = {"paragraph", "heading", "list_item", "table_cell", "caption"}
EXCLUDED_BLOCKS = {"quotation", "reference", "code", "template"}


def _words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?", text)


def _sentences(text: str) -> List[Tuple[int, int, str]]:
    output = []
    for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|(?=\n|$))", text):
        value = match.group(0).strip()
        if value:
            leading = len(match.group(0)) - len(match.group(0).lstrip())
            output.append((match.start() + leading, match.start() + len(match.group(0).rstrip()), value))
    return output


def _context(text: str, start: int, end: int, radius: int = 90) -> str:
    return text[max(0, start - radius):min(len(text), end + radius)].replace("\n", " ").strip()


class WritingStyleReviewer:
    """Apply versioned deterministic and heuristic rules with visible evidence."""

    STRENGTH_POINTS = {"weak": 2.0, "moderate": 5.0, "stronger": 8.0}

    COVERAGE_MATRIX = [
        ("significance_legacy", "Undue significance, legacy, and broader trends", "Implemented heuristic check"),
        ("notability_media", "Canned notability, attribution, and media coverage", "Requires human review"),
        ("superficial_analysis", "Superficial analysis and participial clauses", "Implemented heuristic check"),
        ("promotional_language", "Promotional or advertisement-like language", "Implemented deterministic check"),
        ("vague_association", "Vague connection or association", "Implemented heuristic check"),
        ("vague_authority", "Vague attribution and consensus", "Implemented heuristic check"),
        ("future_outlook", "Generic challenges and future outlook", "Implemented heuristic check"),
        ("awards_recognition", "Awards and recognition section", "Requires human review"),
        ("ai_vocabulary", "High density of starter vocabulary", "Implemented deterministic check"),
        ("copulative_avoidance", "Avoidance of basic copulatives", "Requires human review"),
        ("negative_parallelism", "Repeated negative parallelism", "Implemented deterministic check"),
        ("proper_noun_leads", "List or broad title treated as a proper noun", "Not applicable to uploaded documents"),
        ("rule_of_three", "Repeated three-part enumeration", "Implemented heuristic check"),
        ("headings", "Heading hierarchy and repetition", "Implemented deterministic check"),
        ("boldface", "Excessive boldface and inline bold labels", "Implemented deterministic check"),
        ("em_dash", "Em-dash usage and spacing", "Implemented deterministic check"),
        ("emoji", "Emoji used as section formatting", "Implemented deterministic check"),
        ("tables", "Unusual or repetitive tables", "Requires human review"),
        ("smart_punctuation", "Curly quotes and apostrophes", "Implemented deterministic check"),
        ("thematic_breaks", "Decorative thematic breaks", "Implemented deterministic check"),
        ("collaborative_residue", "Assistant-to-user communication", "Implemented deterministic check"),
        ("cutoff_disclaimer", "Knowledge-cutoff or source disclaimer", "Implemented deterministic check"),
        ("placeholder", "Template and placeholder text", "Implemented deterministic check"),
        ("markdown", "Accidental Markdown syntax", "Implemented deterministic check"),
        ("broken_wikitext", "Broken or internal reference markup", "Implemented deterministic check"),
        ("citation_links", "Broken URLs, DOI, ISBN, and reference linkage", "Implemented deterministic check"),
        ("network_citations", "Network DOI, URL, and metadata verification", "Optional external verification"),
        ("claim_support", "Whether a citation supports a claim", "Requires human review"),
        ("comment_indicators", "Comment-specific indicators", "Not applicable to uploaded documents"),
        ("edit_summaries", "Wikipedia edit-summary behavior", "Not applicable to uploaded documents"),
        ("account_history", "Account history and style shifts", "Not applicable to uploaded documents"),
        ("bias", "Political or cultural bias", "Requires human review"),
        ("external_semantics", "Semantic similarity or external model classification", "Optional external verification"),
    ]

    def __init__(self, rules_path: Optional[str] = None):
        path = Path(rules_path) if rules_path else RULES_PATH
        with path.open(encoding="utf-8") as handle:
            self.registry = json.load(handle)
        self.compiled = {}
        for rule in self.registry["rules"]:
            if not rule.get("enabled", True):
                continue
            compiled = []
            for pattern in rule.get("patterns", []):
                if len(pattern) > 300:
                    raise ValueError(f"Unsafe oversized rule pattern: {rule['id']}")
                compiled.append(re.compile(r"(?<![A-Za-z0-9_])(?:" + pattern + r")(?![A-Za-z0-9_])", re.I))
            self.compiled[rule["id"]] = compiled

    @staticmethod
    def _plain_blocks(text: str) -> List[Dict[str, Any]]:
        blocks, cursor = [], 0
        for index, match in enumerate(re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", text, re.S), 1):
            value = match.group(0)
            block_type = "quotation" if re.match(r"^\s*[>\"“]", value) else "reference" if re.match(r"^\s*(?:references|works cited|bibliography)\b", value, re.I) else "paragraph"
            blocks.append({"id": f"block-{index}", "type": block_type, "text": value, "start_offset": match.start(), "end_offset": match.end(), "page": None, "metadata": {}})
            cursor = match.end()
        if not blocks and text:
            blocks.append({"id": "block-1", "type": "paragraph", "text": text, "start_offset": 0, "end_offset": len(text), "page": None, "metadata": {}})
        return blocks

    @staticmethod
    def _language_coverage(text: str) -> Dict[str, Any]:
        letters = [char for char in text if char.isalpha()]
        ascii_letters = sum(1 for char in letters if ord(char) < 128)
        ratio = ascii_letters / max(1, len(letters))
        return {"language": "en" if ratio >= 0.85 else "unknown", "english_character_ratio": round(ratio, 3), "coverage": "standard" if ratio >= 0.85 else "limited"}

    @staticmethod
    def _finding(rule: Dict[str, Any], block: Dict[str, Any], start: int, end: int, matched: str, text: str, excluded: bool, reason: Optional[str], strength: Optional[str] = None, detector: Optional[str] = None, explanation: Optional[str] = None) -> Dict[str, Any]:
        absolute_start = block["start_offset"] + start
        absolute_end = block["start_offset"] + end
        digest = hashlib.sha1(f"{rule['id']}:{block['id']}:{absolute_start}:{absolute_end}".encode()).hexdigest()[:12]
        return {
            "id": f"finding-{digest}", "rule_id": rule["id"], "category": rule["category"],
            "evidence_strength": strength or rule["evidence_strength"], "detector_type": detector or rule["detector_type"],
            "block_id": block["id"], "page": block.get("page"), "start_offset": absolute_start, "end_offset": absolute_end,
            "matched_text": matched, "explanation": explanation or rule["description"], "context": _context(text, absolute_start, absolute_end),
            "excluded_from_score": excluded, "exclusion_reason": reason,
        }

    def _registry_findings(self, text: str, blocks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        findings, rule_metrics = [], {}
        for rule in self.registry["rules"]:
            if not rule.get("enabled", True):
                continue
            matches = []
            affected = set()
            for block in blocks:
                if block["type"] not in rule["applicable_block_types"]:
                    continue
                for pattern in self.compiled.get(rule["id"], []):
                    for match in pattern.finditer(block["text"]):
                        key = (block["id"], match.start(), match.end())
                        if any(row[0] == key for row in matches):
                            continue
                        matches.append((key, block, match))
                        affected.add(block["id"])
            # Collapse overlapping alternatives from the same rule so one
            # passage cannot become several independent findings.
            deduped = []
            for row in sorted(matches, key=lambda item: (item[1]["id"], item[2].start(), item[2].end() - item[2].start())):
                if deduped and row[1]["id"] == deduped[-1][1]["id"] and row[2].start() < deduped[-1][2].end():
                    if (row[2].end() - row[2].start()) < (deduped[-1][2].end() - deduped[-1][2].start()):
                        deduped[-1] = row
                    continue
                deduped.append(row)
            matches = deduped
            eligible_matches = [row for row in matches if row[1]["type"] not in EXCLUDED_BLOCKS]
            eligible_words = sum(len(_words(block["text"])) for block in blocks if block["type"] in ELIGIBLE_BLOCKS)
            frequency = len(eligible_matches) / max(1, eligible_words) * 1000
            threshold_met = len(eligible_matches) >= int(rule["minimum_occurrences"]) and frequency >= float(rule["frequency_per_1000"])
            paragraph_counts = Counter(row[1]["id"] for row in eligible_matches)
            local_concentration = max(paragraph_counts.values(), default=0)
            rule_metrics[rule["id"]] = {
                "count": len(matches), "eligible_count": len(eligible_matches), "per_1000_eligible_words": round(frequency, 2),
                "affected_blocks": len(affected), "local_concentration": local_concentration, "threshold_met": threshold_met,
            }
            for _, block, match in matches:
                excluded = block["type"] in EXCLUDED_BLOCKS or not threshold_met
                reason = f"{block['type']} blocks are inspectable but excluded from the default index." if block["type"] in EXCLUDED_BLOCKS else "Reported below the configured repetition or frequency threshold." if not threshold_met else None
                findings.append(self._finding(rule, block, match.start(), match.end(), match.group(0), text, excluded, reason))
        return findings, rule_metrics

    def _punctuation_findings(self, text: str, blocks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        findings = []
        pseudo = {"id": "em_dash_usage", "category": "punctuation", "evidence_strength": "weak", "detector_type": "exact", "description": "Em-dash use is descriptive and has minimal index influence."}
        smart = {"id": "smart_punctuation", "category": "punctuation", "evidence_strength": "weak", "detector_type": "exact", "description": "Smart quotes and apostrophes are reported with zero score because editors introduce them automatically."}
        em_count = en_count = hyphen_count = smart_count = paired = multiple_sentences = 0
        eligible_words = 0
        eligible_sentences = em_sentences = 0
        spacing = Counter()
        for block in blocks:
            eligible = block["type"] in ELIGIBLE_BLOCKS
            if eligible:
                eligible_words += len(_words(block["text"]))
            for start, end, sentence in _sentences(block["text"]):
                if eligible:
                    eligible_sentences += 1
                    if '—' in sentence:
                        em_sentences += 1
                    if sentence.count('—') > 1:
                        multiple_sentences += 1
                    if re.search(r"—[^—\n]{2,120}—", sentence):
                        paired += 1
            for match in re.finditer('—', block["text"]):
                em_count += 1
                before = block["text"][match.start() - 1] if match.start() else ''
                after = block["text"][match.end()] if match.end() < len(block["text"]) else ''
                spacing['spaced_both' if before.isspace() and after.isspace() else 'unspaced' if not before.isspace() and not after.isspace() else 'mixed'] += 1
                excluded = not eligible
                findings.append(self._finding(pseudo, block, match.start(), match.end(), match.group(0), text, excluded, f"{block['type']} blocks are excluded from the default index." if excluded else None))
            en_count += block["text"].count('–')
            hyphen_count += block["text"].count('-')
            for match in re.finditer(r"[“”‘’]", block["text"]):
                smart_count += 1
                findings.append(self._finding(smart, block, match.start(), match.end(), match.group(0), text, True, "Zero default score; normal editors introduce smart punctuation."))
        return findings, {
            "em_dash_count": em_count, "en_dash_count": en_count, "hyphen_minus_count": hyphen_count,
            "em_dashes_per_1000_eligible_words": round(em_count / max(1, eligible_words) * 1000, 2),
            "sentences_with_em_dashes_pct": round(em_sentences / max(1, eligible_sentences) * 100, 2),
            "sentences_with_multiple_em_dashes": multiple_sentences, "paired_parenthetical_em_dashes": paired,
            "spacing": dict(spacing), "smart_quote_or_apostrophe_count": smart_count,
        }

    def _formatting_findings(self, text: str, blocks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        findings, unavailable = [], []
        has_formatting = any(block.get("metadata", {}).get("bold_spans") is not None for block in blocks)
        if not has_formatting:
            unavailable.append("Bold and italic checks are unavailable for this extraction format.")
        pseudo = {"category": "formatting", "evidence_strength": "weak", "detector_type": "exact"}
        headings = [block for block in blocks if block["type"] == "heading"]
        last_level = None
        for block in headings:
            level = block.get("metadata", {}).get("heading_level")
            if level and last_level and level > last_level + 1:
                rule = {**pseudo, "id": "skipped_heading_level", "description": "Heading hierarchy skips a level."}
                findings.append(self._finding(rule, block, 0, len(block["text"]), block["text"], text, False, None))
            last_level = level or last_level
        for block in blocks:
            value = block["text"]
            checks = [
                ("emoji_section_marker", r"^\s*[\U0001F300-\U0001FAFF]", "Emoji used as a section marker."),
                ("decorative_separator", r"^\s*(?:[-*_]\s*){3,}$", "Decorative horizontal separator."),
                ("leftover_markdown", r"(?:^|\s)(?:#{1,6}\s+|\*\*[^*]+\*\*|```)", "Markdown syntax remains in extracted prose."),
                ("bold_label_bullet", r"^\s*(?:[-*+]\s+)?\*\*[^*]{1,60}:\*\*", "Bold label plus colon in a list item."),
            ]
            for rule_id, pattern, description in checks:
                for match in re.finditer(pattern, value, re.M):
                    rule = {**pseudo, "id": rule_id, "description": description}
                    findings.append(self._finding(rule, block, match.start(), match.end(), match.group(0), text, block["type"] in EXCLUDED_BLOCKS, "Excluded block type." if block["type"] in EXCLUDED_BLOCKS else None))
            bold_spans = block.get("metadata", {}).get("bold_spans", [])
            bold_chars = sum(end - start for start, end in bold_spans)
            if value and bold_chars / len(value) > 0.35:
                rule = {**pseudo, "id": "excessive_bold", "description": "More than 35% of this block is bold."}
                findings.append(self._finding(rule, block, 0, len(value), value[:160], text, False, None))
        return findings, unavailable

    def analyze(self, text: str, document: Optional[Dict[str, Any]] = None, profile: str = "academic_report", numeric_index: bool = True) -> Dict[str, Any]:
        document = document or {}
        blocks = document.get("blocks") or self._plain_blocks(text)
        language = self._language_coverage(text)
        profile_config = self.registry["profiles"].get(profile, self.registry["profiles"][self.registry["default_profile"]])
        findings, rule_metrics = self._registry_findings(text, blocks)
        punctuation_findings, punctuation = self._punctuation_findings(text, blocks)
        formatting_findings, unavailable = self._formatting_findings(text, blocks)
        findings.extend(punctuation_findings)
        findings.extend(formatting_findings)
        findings.sort(key=lambda row: (row["start_offset"], row["end_offset"], row["rule_id"]))

        eligible_words = sum(len(_words(block["text"])) for block in blocks if block["type"] in ELIGIBLE_BLOCKS)
        excluded_words = sum(len(_words(block["text"])) for block in blocks if block["type"] in EXCLUDED_BLOCKS)
        category_points = defaultdict(float)
        category_caps = defaultdict(float)
        rule_lookup = {rule["id"]: rule for rule in self.registry["rules"]}
        for rule_id, metrics in rule_metrics.items():
            rule = rule_lookup[rule_id]
            category_caps[rule["category"]] = max(category_caps[rule["category"]], float(rule["category_contribution_cap"]))
            if metrics["threshold_met"]:
                repetition = min(2.0, metrics["eligible_count"] / max(1, rule["minimum_occurrences"]))
                points = self.STRENGTH_POINTS[rule["evidence_strength"]] * repetition
                if rule["category"] == "promotional_language":
                    points *= profile_config["promotional_weight"]
                category_points[rule["category"]] += points
        em_contribution = min(4.0, max(0.0, punctuation["em_dashes_per_1000_eligible_words"] - 2.0) * 0.25)
        category_points["punctuation"] += em_contribution
        category_caps["punctuation"] = 4.0
        for row in formatting_findings:
            if not row["excluded_from_score"]:
                category_points["formatting"] += 1.5
        category_caps["formatting"] = 8.0
        category_breakdown = []
        for category in sorted(set(category_caps) | set(category_points)):
            cap = category_caps[category]
            points = round(min(cap, category_points[category]), 1)
            category_breakdown.append({"category": category, "points": points, "cap": cap, "finding_count": sum(1 for row in findings if row["category"] == category and not row["excluded_from_score"])})
        raw_points = sum(row["points"] for row in category_breakdown)
        max_points = sum(row["cap"] for row in category_breakdown) or 1
        index = round(raw_points / max_points * 100, 1) if numeric_index and eligible_words >= self.registry["minimum_eligible_words"] else None
        active_categories = sum(1 for row in category_breakdown if row["points"] > 0)
        recommendation = "Insufficient text for a document-level index." if eligible_words < self.registry["minimum_eligible_words"] else "Review multiple independent categories and their passages." if active_categories >= self.registry["strong_review_min_categories"] else "Review the listed passages in context; limited categories should not drive an authorship conclusion."
        warnings = list(document.get("warnings", []))
        if language["coverage"] == "limited":
            warnings.append("English rules have limited coverage for this document; the absence of findings is not a clean result.")
        unavailable.extend(["OCR-dependent checks are unavailable." ] if document.get("extraction_status") == "empty_requires_ocr" else [])
        cooccurrence = Counter()
        by_block = defaultdict(set)
        for row in findings:
            if not row["excluded_from_score"]:
                by_block[row["block_id"]].add(row["category"])
        for categories in by_block.values():
            for category in categories:
                if len(categories) > 1:
                    cooccurrence[category] += 1
        return {
            "feature_name": "AI Writing Style Review", "ruleset_version": self.registry["ruleset_version"],
            "ruleset_status": self.registry["status"], "source_review_date": self.registry["review_date"],
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(), "profile": profile,
            "extraction_status": document.get("extraction_status", "text_input"), "extraction_warnings": warnings,
            "language_coverage": language, "eligible_word_count": eligible_words, "excluded_word_count": excluded_words,
            "style_pattern_index": index, "numeric_index_enabled": numeric_index, "category_breakdown": category_breakdown,
            "rule_metrics": rule_metrics, "punctuation_metrics": punctuation, "cooccurrence_by_category": dict(cooccurrence),
            "findings": findings, "finding_count": len(findings), "scored_finding_count": sum(1 for row in findings if not row["excluded_from_score"]),
            "supported_checks": [label for _, label, status in self.COVERAGE_MATRIX if status.startswith("Implemented")],
            "unavailable_checks": sorted(set(unavailable)),
            "coverage_matrix": [{"id": key, "category": label, "status": status} for key, label, status in self.COVERAGE_MATRIX],
            "recommendation": recommendation,
            "disclaimer": "These findings identify writing patterns that can occur in both human and AI-assisted text. They do not establish authorship.",
            "validation": "No authorized genre-balanced human/AI evaluation corpus is bundled; this ruleset is unvalidated and its thresholds are experimental.",
        }
