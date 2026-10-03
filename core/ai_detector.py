"""Explainable deterministic writing-pattern analysis.

This module reports surface patterns for human review. It does not infer
authorship. The signal groups are adapted from the MIT-licensed
``avoid-ai-writing`` and ``humanize`` projects; see THIRD_PARTY_NOTICES.md.
"""

import math
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Pattern, Tuple


class AIDetector:
    """Nine-category writing-pattern review model."""

    PATTERN_VERSION = "2.1.0"
    MIN_RELIABLE_WORDS = 120

    AI_MARKER_PHRASES = {
        "delve", "delve into", "tapestry", "testament to", "pivotal role",
        "seamless integration", "holistic approach", "multifaceted",
        "in the realm of", "the landscape of", "a myriad of", "a plethora of",
        "it is important to note", "it is worth noting", "plays a crucial role",
        "foster innovation", "game changer", "vibrant tapestry", "leverage",
        "utilize", "robust", "comprehensive", "streamline",
    }
    # Plain-language replacements for each marker above, taken directly from the
    # before/after tables the MIT-licensed avoid-ai-writing and humanize projects
    # publish in their own READMEs (avoid-ai-writing's "Language Patterns" table;
    # humanize's Lever 1 word list). A writing suggestion, not a rewrite: the
    # student picks the replacement, nothing is rewritten automatically.
    # See THIRD_PARTY_NOTICES.md.
    SUGGESTED_REPLACEMENTS = {
        "delve": "look into", "delve into": "look into",
        "tapestry": "mix (or cut the word)", "vibrant tapestry": "mix (or cut the phrase)",
        "testament to": "shows", "pivotal role": "important role",
        "seamless integration": "smooth integration", "holistic approach": "overall approach",
        "multifaceted": "complex", "in the realm of": "in", "the landscape of": "the field of",
        "a myriad of": "many", "a plethora of": "many",
        "it is important to note": "(cut the phrase; state the fact directly)",
        "it is worth noting": "(cut the phrase; state the fact directly)",
        "plays a crucial role": "matters for", "foster innovation": "encourage innovation",
        "game changer": "(name the specific effect instead)", "leverage": "use",
        "utilize": "use", "robust": "reliable", "comprehensive": "thorough", "streamline": "simplify",
    }

    HEDGE_PATTERNS: Tuple[Pattern[str], ...] = tuple(re.compile(p, re.I) for p in (
        r"\b(?:often|generally|typically|arguably|potentially|perhaps|possibly)\b",
        r"\bin many cases\b", r"\bit can be argued\b", r"\bone might consider\b",
        r"\bit is (?:important|worthwhile) to (?:note|mention)\b",
        r"\bresults may vary\b", r"\bmay (?:help|lead|result|suggest|indicate)\b",
    ))
    TRANSITION_PATTERNS: Tuple[Pattern[str], ...] = tuple(re.compile(p, re.I | re.M) for p in (
        r"^(?:furthermore|moreover|additionally),",
        r"\b(?:this highlights|this underscores|this demonstrates)\s+the\s+importance\s+of\b",
        r"\bas previously mentioned\b", r"\bin addition to the above\b",
        r"\bit goes without saying\b", r"\bneedless to say\b",
        r"\b(?:in conclusion|to summarize|in summary),?\b",
    ))
    STRUCTURE_PATTERNS: Tuple[Tuple[str, Pattern[str]], ...] = (
        ("formulaic introduction", re.compile(r"\b(?:in this (?:paper|article|section),? (?:we|i) will|this (?:paper|article) (?:aims to|explores|examines))\b", re.I)),
        ("negative parallelism", re.compile(r"\b(?:it(?:'s| is) not|not just)\b[^.!?]{2,100}\b(?:it(?:'s| is)|but)\b", re.I)),
        ("announcement framing", re.compile(r"\b(?:the key (?:insight|point|lesson) is|what (?:surprised|changed|worked|clicked)[^.!?]{0,40} was)\b", re.I)),
        ("generic conclusion", re.compile(r"\b(?:the future looks bright|only time will tell|in conclusion|to summarize|in summary)\b", re.I)),
        ("stock significance frame", re.compile(r"\b(?:is|are) (?:a testament to|pivotal to|crucial to)\b", re.I)),
    )
    CHATBOT_PATTERNS: Tuple[Tuple[str, Pattern[str]], ...] = (
        ("assistant opener", re.compile(r"^\s*(?:certainly|absolutely|great question)[!,.]", re.I)),
        ("assistant closer", re.compile(r"\b(?:i hope this helps|let me know if you have any questions|feel free to reach out)\b", re.I)),
        ("reasoning narration", re.compile(r"\b(?:let me think step by step|let'?s break this down|breaking this down)\b", re.I)),
    )
    RHETORICAL_PATTERNS: Tuple[Tuple[str, Pattern[str]], ...] = (
        ("not-X-but-Y frame", re.compile(r"\bnot\s+(?:just\s+)?[^,.;]{2,70}(?:,|—|–)\s*(?:but\s+)?[^.!?]{2,90}", re.I)),
        ("performed discovery", re.compile(r"\b(?:turns out|what i (?:didn'?t expect|realized|found) was|the thing i realized was)\b", re.I)),
        ("mini-aphorism", re.compile(r"\bthat(?:'s| is) (?:the (?:real|actual|whole) (?:work|cost|point|thing)|what changed|what matters)\b", re.I)),
        ("comparative framing", re.compile(r"\bmore\s+[\w-]+\s+than\s+[\w-]+\b", re.I)),
        ("significance flourish", re.compile(r"\b(?:a testament to|pivotal role|vibrant tapestry)\b", re.I)),
    )
    VAGUE_CLAIM_PATTERNS: Tuple[Pattern[str], ...] = tuple(re.compile(p, re.I) for p in (
        r"\b(?:studies|research|experts|scholars|scientists)\s+(?:show|shows|suggest|suggests|indicate|indicates|found)\b",
        r"\b(?:many|most|numerous)\s+(?:organizations|people|researchers|students|companies|teams)\b",
        r"\b(?:significant|notable|substantial)\s+(?:improvement|progress|impact|effect|increase|decrease)s?\b",
        r"\bit (?:is|has been) (?:widely )?(?:known|accepted|established|shown)\b",
    ))
    CITATION_RE = re.compile(
        r"\((?:[A-Z][\w'’–-]+(?:\s+(?:et\s+al\.|&\s*[A-Z][\w'’–-]+))?,\s*(?:19|20)\d{2}[a-z]?|(?:19|20)\d{2})[^)]*\)|\[\d+(?:\s*[-–,]\s*\d+)*\]"
    )
    # Literal artifacts of copying an AI assistant's output, rather than style inference.
    # Pattern set adapted from the MIT-licensed avoid-ai-writing project's documented
    # "unfilled placeholder" / "chatbot citation markup" / "AI-tool URL parameter" tells;
    # see THIRD_PARTY_NOTICES.md.
    PROVENANCE_PATTERNS: Tuple[Tuple[str, Pattern[str]], ...] = (
        ("unfilled template placeholder", re.compile(
            r"\[(?:your name|insert (?:source|citation|name|date|link|here|[a-z]{3,20})|company name|client name|date here|placeholder|todo|tbd)\]"
            r"|\b(?:19|20)\d{2}-xx-xx\b|\bxx[/-]xx[/-](?:19|20)\d{2}\b", re.I)),
        ("AI-assistant citation markup", re.compile(
            r"\bciteturn\d+search\d+\b|\boai_citation\b|contentreference\[oaicite:\d+\](?:\{index=\d+\})?", re.I)),
        ("AI-tool tracking link", re.compile(
            r"utm_source=(?:chatgpt|copilot|perplexity|openai|claude|gemini|bard)(?:\.\w+)*", re.I)),
    )
    ANCHOR_RE = re.compile(
        r"\b(?:19|20)\d{2}\b|\b\d+(?:\.\d+)?%\b|\b\d+(?:,\d{3})+(?:\.\d+)?\b|\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b"
    )

    CATEGORY_META = (
        ("predictability", "Predictable vocabulary", "Replace stock wording with the precise term your subject requires."),
        ("burstiness", "Sentence rhythm", "Vary sentence length only where it improves emphasis and readability."),
        ("hedging", "Hedge density", "Keep uncertainty that is academically justified; remove reflexive softening."),
        ("structure", "Formulaic structure", "Lead with the actual claim and remove repeated setup or summary frames."),
        ("specificity", "Specificity and grounding", "Attach concrete evidence and a citation to factual or empirical claims."),
        ("transitions", "Transition fingerprint", "Use transitions only when the logical relationship is not already clear."),
        ("punctuation", "Punctuation fingerprint", "Replace unnecessary em dashes with periods, commas, or a direct sentence."),
        ("register", "Assistant-style register", "Remove chatbot framing and keep the voice appropriate for the assignment."),
        ("rhetoric", "Rhetorical scaffolding", "State the conclusion directly instead of announcing or staging it."),
    )

    @staticmethod
    def tokenize_words(text: str) -> List[str]:
        return re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?", text.lower())

    @staticmethod
    def sentence_spans(text: str) -> List[Tuple[int, int, str]]:
        spans: List[Tuple[int, int, str]] = []
        for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|(?=\n|$))", text):
            raw = match.group(0)
            stripped = raw.strip()
            if len(stripped) < 4:
                continue
            left = len(raw) - len(raw.lstrip())
            right = len(raw.rstrip())
            spans.append((match.start() + left, match.start() + right, stripped))
        return spans

    @classmethod
    def split_sentences(cls, text: str) -> List[str]:
        return [sentence for _, _, sentence in cls.sentence_spans(text)]

    @classmethod
    def compute_burstiness(cls, sentences: List[str]) -> float:
        if len(sentences) < 2:
            return 50.0
        lengths = [len(cls.tokenize_words(sentence)) for sentence in sentences]
        mean_len = sum(lengths) / len(lengths)
        if mean_len == 0:
            return 0.0
        variance = sum((length - mean_len) ** 2 for length in lengths) / len(lengths)
        return round(min(100.0, math.sqrt(variance) / mean_len * 100.0), 2)

    @staticmethod
    def compute_lexical_diversity(words: List[str]) -> float:
        if not words:
            return 0.0
        return round(len(set(words)) / len(words) * 100.0, 2)

    @staticmethod
    def compute_lexical_entropy(words: List[str]) -> float:
        if not words:
            return 0.0
        counts = Counter(words)
        total = len(words)
        entropy = -sum((count / total) * math.log2(count / total) for count in counts.values())
        maximum = math.log2(len(counts)) if len(counts) > 1 else 1.0
        return round(entropy / maximum * 100.0, 2)

    @staticmethod
    def _evidence(match: re.Match[str], kind: str) -> Dict[str, Any]:
        return {"text": match.group(0).strip(), "start": match.start(), "end": match.end(), "kind": kind}

    @classmethod
    def _collect(cls, text: str, patterns: Iterable[Pattern[str]], kind: str) -> List[Dict[str, Any]]:
        evidence: List[Dict[str, Any]] = []
        for pattern in patterns:
            evidence.extend(cls._evidence(match, kind) for match in pattern.finditer(text))
        return cls._dedupe_evidence(evidence)

    @staticmethod
    def _dedupe_evidence(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        output = []
        for row in sorted(evidence, key=lambda item: (item["start"], item["end"], item["kind"])):
            key = (row["start"], row["end"], row["kind"])
            if key not in seen:
                seen.add(key)
                output.append(row)
        return output

    @staticmethod
    def _score_count(count: int, moderate: int = 2, strong: int = 4) -> int:
        if count <= 0:
            return 0
        if count >= strong:
            return 3
        if count >= moderate:
            return 2
        return 1

    @classmethod
    def _category(cls, category_id: str, score: int, evidence: List[Dict[str, Any]], metrics: Dict[str, Any] | None = None) -> Dict[str, Any]:
        label, recommendation = next((label, rec) for key, label, rec in cls.CATEGORY_META if key == category_id)
        return {"id": category_id, "label": label, "score": max(0, min(3, int(score))), "max_score": 3, "evidence": evidence[:12], "evidence_count": len(evidence), "metrics": metrics or {}, "recommendation": recommendation}

    @classmethod
    def analyze(cls, text: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Return a nine-category review profile with quoted evidence."""
        text = text or ""
        words = cls.tokenize_words(text)
        sentence_rows = cls.sentence_spans(text)
        sentences = [row[2] for row in sentence_rows]
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        word_count = len(words)
        context = context or {}
        if not words or not sentences:
            return cls._empty_result(word_count)

        burstiness = cls.compute_burstiness(sentences)
        diversity = cls.compute_lexical_diversity(words)
        entropy = cls.compute_lexical_entropy(words)

        vocabulary_evidence: List[Dict[str, Any]] = []
        for phrase in sorted(cls.AI_MARKER_PHRASES, key=len, reverse=True):
            pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.I)
            vocabulary_evidence.extend(cls._evidence(m, "stock vocabulary") for m in pattern.finditer(text))
        vocabulary_evidence = cls._dedupe_evidence(vocabulary_evidence)
        for row in vocabulary_evidence:
            row["suggestion"] = cls.SUGGESTED_REPLACEMENTS.get(row["text"].lower())
        distinct_markers = len({row["text"].lower() for row in vocabulary_evidence})
        predictability_score = cls._score_count(distinct_markers, 2, 5)

        lengths = [len(cls.tokenize_words(sentence)) for sentence in sentences]
        rhythm_evidence: List[Dict[str, Any]] = []
        clustered_runs = 0
        if len(lengths) >= 3:
            for idx in range(len(lengths) - 2):
                window = lengths[idx:idx + 3]
                if max(window) - min(window) <= 5 and min(window) >= 8:
                    clustered_runs += 1
                    rhythm_evidence.append({"text": f"Sentence lengths {window}", "start": sentence_rows[idx][0], "end": sentence_rows[idx + 2][1], "kind": "uniform sentence run"})
        if len(sentences) < 5:
            rhythm_score = 0
        elif burstiness < 18 or clustered_runs >= 3:
            rhythm_score = 3
        elif burstiness < 27 or clustered_runs >= 2:
            rhythm_score = 2
        elif burstiness < 35 or clustered_runs == 1:
            rhythm_score = 1
        else:
            rhythm_score = 0

        hedge_evidence = cls._collect(text, cls.HEDGE_PATTERNS, "hedge")
        hedge_rate = len(hedge_evidence) / max(word_count, 1) * 100
        hedge_score = 3 if hedge_rate >= 3 else 2 if hedge_rate >= 1.5 else 1 if hedge_evidence else 0

        structure_evidence: List[Dict[str, Any]] = []
        for kind, pattern in cls.STRUCTURE_PATTERNS:
            structure_evidence.extend(cls._evidence(m, kind) for m in pattern.finditer(text))
        bullet_count = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", text))
        if bullet_count >= 5:
            structure_evidence.append({"text": f"{bullet_count} list items", "start": 0, "end": 0, "kind": "list-heavy structure"})
        structure_evidence = cls._dedupe_evidence(structure_evidence)
        structure_score = cls._score_count(len(structure_evidence), 2, 4)

        specificity_evidence: List[Dict[str, Any]] = []
        for start, end, sentence in sentence_rows:
            vague = any(pattern.search(sentence) for pattern in cls.VAGUE_CLAIM_PATTERNS)
            if vague and not cls.CITATION_RE.search(sentence) and not cls.ANCHOR_RE.search(sentence):
                specificity_evidence.append({"text": sentence[:220], "start": start, "end": end, "kind": "unanchored claim"})
        for row in context.get("unsupported_claims", []) or []:
            sentence = str(row.get("sentence", "")).strip()
            if sentence and not any(item["text"] == sentence for item in specificity_evidence):
                start = max(0, text.find(sentence))
                specificity_evidence.append({"text": sentence[:220], "start": start, "end": start + len(sentence), "kind": "claim without recognized citation"})
        zero_anchor_paragraphs = 0
        if word_count >= cls.MIN_RELIABLE_WORDS:
            zero_anchor_paragraphs = sum(1 for p in paragraphs if len(cls.tokenize_words(p)) >= 35 and not cls.ANCHOR_RE.search(p) and not cls.CITATION_RE.search(p))
        specificity_score = cls._score_count(len(specificity_evidence) + zero_anchor_paragraphs, 2, 4)

        transition_evidence = cls._collect(text, cls.TRANSITION_PATTERNS, "formulaic transition")
        transition_score = cls._score_count(len(transition_evidence), 2, 4)

        em_dash_matches = list(re.finditer(r"—", text))
        double_dash_matches = list(re.finditer(r"(?<!-)\s--\s(?!-)", text))
        em_dash_rate_300 = len(em_dash_matches) / max(word_count, 1) * 300
        punctuation_evidence = [cls._evidence(m, "em dash") for m in em_dash_matches]
        punctuation_evidence.extend(cls._evidence(m, "spaced double hyphen") for m in double_dash_matches)
        wrapped = re.search(r"—[^—\n]{2,100}—", text)
        if wrapped:
            punctuation_evidence.append(cls._evidence(wrapped, "wrapped em-dash aside"))
        mid_colons = list(re.finditer(r"\b(?:the (?:problem|answer|reason|rule|point)|what matters)\s*:", text, re.I))
        punctuation_evidence.extend(cls._evidence(m, "announcement colon") for m in mid_colons)
        if not em_dash_matches and not double_dash_matches and not mid_colons:
            punctuation_score = 0
        elif wrapped or em_dash_rate_300 > 3 or len(mid_colons) >= 2:
            punctuation_score = 2
        else:
            punctuation_score = 1

        register_evidence: List[Dict[str, Any]] = []
        for kind, pattern in cls.CHATBOT_PATTERNS:
            register_evidence.extend(cls._evidence(m, kind) for m in pattern.finditer(text))
        register_score = 3 if len(register_evidence) >= 2 else 2 if register_evidence else 0

        rhetoric_evidence: List[Dict[str, Any]] = []
        for kind, pattern in cls.RHETORICAL_PATTERNS:
            rhetoric_evidence.extend(cls._evidence(m, kind) for m in pattern.finditer(text))
        rhetoric_evidence = cls._dedupe_evidence(rhetoric_evidence)
        rhetoric_score = cls._score_count(len(rhetoric_evidence), 2, 4)

        provenance_evidence: List[Dict[str, Any]] = []
        for kind, pattern in cls.PROVENANCE_PATTERNS:
            provenance_evidence.extend(cls._evidence(m, kind) for m in pattern.finditer(text))
        provenance_evidence = cls._dedupe_evidence(provenance_evidence)

        categories = [
            cls._category("predictability", predictability_score, vocabulary_evidence, {"distinct_markers": distinct_markers}),
            cls._category("burstiness", rhythm_score, rhythm_evidence, {"sentence_lengths": lengths, "coefficient_of_variation_pct": burstiness}),
            cls._category("hedging", hedge_score, hedge_evidence, {"per_100_words": round(hedge_rate, 2)}),
            cls._category("structure", structure_score, structure_evidence, {"bullet_items": bullet_count}),
            cls._category("specificity", specificity_score, specificity_evidence, {"zero_anchor_paragraphs": zero_anchor_paragraphs}),
            cls._category("transitions", transition_score, transition_evidence),
            cls._category("punctuation", punctuation_score, cls._dedupe_evidence(punctuation_evidence), {"em_dash_count": len(em_dash_matches), "em_dashes_per_300_words": round(em_dash_rate_300, 2), "wrapped_em_dash": bool(wrapped), "announcement_colons": len(mid_colons)}),
            cls._category("register", register_score, register_evidence),
            cls._category("rhetoric", rhetoric_score, rhetoric_evidence),
        ]

        total_points = sum(row["score"] for row in categories)
        pattern_score = round(total_points / 27 * 100, 1)
        if pattern_score < 25:
            risk, status, description = "Low Pattern Score", "success", "Few configured writing patterns were detected."
        elif pattern_score < 65:
            risk, status, description = "Elevated Pattern Score", "warning", "Several writing patterns merit manual review."
        else:
            risk, status, description = "High Pattern Score", "danger", "Many configured writing patterns were detected; this does not establish authorship."

        top_signals = sorted((row for row in categories if row["score"] > 0), key=lambda row: (-row["score"], -row["evidence_count"], row["label"]))[:4]
        flagged_sentences = cls._flagged_sentences(sentence_rows, categories)
        marker_count = len(vocabulary_evidence) + len(transition_evidence)
        reliability = "limited" if word_count < cls.MIN_RELIABLE_WORDS else "standard"

        return {
            "pattern_score": pattern_score,
            "ai_probability": pattern_score,
            "human_probability": round(100.0 - pattern_score, 1),
            "ai_risk_level": risk,
            "status_class": status,
            "verdict_description": description,
            "reliability": reliability,
            "minimum_reliable_words": cls.MIN_RELIABLE_WORDS,
            "pattern_version": cls.PATTERN_VERSION,
            "categories": categories,
            "top_signals": [{"id": row["id"], "label": row["label"], "score": row["score"], "evidence_count": row["evidence_count"], "recommendation": row["recommendation"]} for row in top_signals],
            "provenance_flags": provenance_evidence[:20],
            "provenance_flags_count": len(provenance_evidence),
            "provenance_note": (
                "These are literal artifacts of copying an AI assistant's output (an unfilled template "
                "placeholder, leftover chatbot citation markup, or an AI-tool tracking link), not stylistic "
                "inference. Each flag is a specific, checkable fact and is not folded into the pattern score above."
            ),
            "style_metrics": {"word_count": word_count, "sentence_count": len(sentences), "paragraph_count": len(paragraphs), "em_dash_count": len(em_dash_matches), "em_dashes_per_300_words": round(em_dash_rate_300, 2), "hedge_count": len(hedge_evidence), "transition_count": len(transition_evidence)},
            "burstiness": burstiness,
            "lexical_diversity": diversity,
            "entropy": entropy,
            "ai_marker_count": marker_count,
            "flagged_markers_count": marker_count,
            "total_sentences": len(sentences),
            "flagged_ai_sentences_count": len(flagged_sentences),
            "flagged_sentences": flagged_sentences,
            "flagged_ai_sentences": flagged_sentences,
            "assessment_scope": "Deterministic writing-pattern review; not evidence of AI or human authorship.",
            "score_explanation": f"{total_points} of 27 category points, normalized to 100. Short samples under {cls.MIN_RELIABLE_WORDS} words have limited reliability.",
            "legacy_field_note": "ai_probability and human_probability are compatibility fields; they are complementary heuristic scores, not calibrated probabilities.",
        }

    @classmethod
    def _flagged_sentences(cls, sentence_rows: List[Tuple[int, int, str]], categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        evidence = [(category["label"], row) for category in categories for row in category["evidence"] if row.get("end", 0) > row.get("start", 0)]
        findings = []
        for start, end, sentence in sentence_rows:
            reasons = sorted({label for label, row in evidence if row["start"] < end and row["end"] > start})
            if reasons:
                findings.append({"sentence": sentence, "start": start, "end": end, "word_count": len(cls.tokenize_words(sentence)), "is_ai_typical": True, "has_llm_markers": True, "reasons": reasons})
        return findings

    @classmethod
    def _empty_result(cls, word_count: int = 0) -> Dict[str, Any]:
        categories = [cls._category(category_id, 0, []) for category_id, _, _ in cls.CATEGORY_META]
        return {
            "pattern_score": 0.0, "ai_probability": 0.0, "human_probability": 100.0,
            "ai_risk_level": "Insufficient Text", "status_class": "warning",
            "reliability": "insufficient", "minimum_reliable_words": cls.MIN_RELIABLE_WORDS,
            "pattern_version": cls.PATTERN_VERSION, "categories": categories, "top_signals": [],
            "provenance_flags": [], "provenance_flags_count": 0,
            "provenance_note": (
                "These are literal artifacts of copying an AI assistant's output, not stylistic inference. "
                "Not folded into the pattern score above."
            ),
            "style_metrics": {"word_count": word_count, "sentence_count": 0, "paragraph_count": 0, "em_dash_count": 0, "em_dashes_per_300_words": 0.0, "hedge_count": 0, "transition_count": 0},
            "burstiness": 50.0, "lexical_diversity": 0.0, "entropy": 0.0,
            "ai_marker_count": 0, "flagged_markers_count": 0,
            "flagged_ai_sentences_count": 0, "flagged_sentences": [], "flagged_ai_sentences": [],
            "assessment_scope": "Deterministic writing-pattern review; not evidence of AI or human authorship.",
            "score_explanation": f"At least {cls.MIN_RELIABLE_WORDS} words are recommended for a stable document-level review.",
        }
