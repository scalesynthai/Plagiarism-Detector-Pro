import math
import re
from typing import Dict, List, Any


class AIDetector:
    """
    Statistical AI Content & LLM Likelihood Engine.
    Analyzes text across:
      - Burstiness (Sentence length & syntactic variance)
      - Perplexity / Transition smoothness approximation
      - Lexical Diversity (Type-Token Ratio & Lexical Entropy)
      - Structural Repetitiveness
    """

    # Common transition phrases heavily favored by LLMs
    AI_MARKER_PHRASES = {
        "furthermore", "in conclusion", "it is important to note", "delve into", "testament to",
        "pivotal role", "beacon of", "tapestry of", "in summary", "moreover", "plays a crucial role",
        "it is worth noting", "shed light on", "foster", "holistic approach", "multifaceted",
        "seamless integration", "realm of", "game changer", "vibrant tapestry", "leverage"
    }

    @staticmethod
    def tokenize_words(text: str) -> List[str]:
        return re.sub(r"[^\w\s]", " ", text.lower()).split()

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+|\n{2,}', text)
        return [s.strip() for s in sentences if len(s.strip()) > 3]

    def compute_burstiness(self, sentences: List[str]) -> float:
        """
        Burstiness measures sentence length variability.
        Human writing exhibits high burstiness (mixing short punchy sentences with long compound ones).
        AI writing tends to have uniform, medium-length sentences (low burstiness).
        """
        if len(sentences) < 2:
            return 50.0  # Neutral default for short text

        lengths = [len(self.tokenize_words(s)) for s in sentences]
        mean_len = sum(lengths) / len(lengths)
        if mean_len == 0:
            return 0.0

        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
        coefficient_of_variation = std_dev / mean_len

        # Normalized burstiness score (0 = extremely uniform/AI-like, 100 = highly varied/human-like)
        burstiness_score = min(100.0, coefficient_of_variation * 100.0)
        return round(burstiness_score, 2)

    def compute_lexical_diversity(self, words: List[str]) -> float:
        """
        Computes Root Type-Token Ratio (RTTR) to measure vocabulary richness.
        """
        if not words:
            return 0.0
        unique_tokens = len(set(words))
        # RTTR = Unique Words / sqrt(Total Words)
        rttr = (unique_tokens / math.sqrt(len(words))) * 10.0
        return min(100.0, round(rttr, 2))

    def compute_lexical_entropy(self, words: List[str]) -> float:
        """
        Computes Shannon entropy across word distribution.
        """
        if not words:
            return 0.0
        tf = {}
        for w in words:
            tf[w] = tf.get(w, 0) + 1

        total = len(words)
        entropy = 0.0
        for count in tf.values():
            p = count / total
            entropy -= p * math.log2(p)

        # Normalize entropy against max possible entropy log2(len(tf))
        max_entropy = math.log2(len(tf)) if len(tf) > 1 else 1.0
        normalized = (entropy / max_entropy) * 100.0 if max_entropy > 0 else 50.0
        return round(normalized, 2)

    def detect_ai_markers(self, text: str) -> int:
        """Counts occurrences of typical LLM boilerplate transition phrases."""
        lower_text = text.lower()
        count = 0
        for phrase in self.AI_MARKER_PHRASES:
            count += len(re.findall(r'\b' + re.escape(phrase) + r'\b', lower_text))
        return count

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Performs comprehensive AI content and LLM likelihood assessment.
        """
        words = self.tokenize_words(text)
        sentences = self.split_sentences(text)

        if not words or not sentences:
            return {
                "ai_probability": 0.0,
                "human_probability": 100.0,
                "ai_risk_level": "Human-Written",
                "status_class": "success",
                "burstiness": 50.0,
                "lexical_diversity": 50.0,
                "entropy": 50.0,
                "ai_marker_count": 0,
                "flagged_ai_sentences": [],
            }

        burstiness = self.compute_burstiness(sentences)
        diversity = self.compute_lexical_diversity(words)
        entropy = self.compute_lexical_entropy(words)
        marker_count = self.detect_ai_markers(text)

        # Baseline AI Score Calculation:
        # Low burstiness (< 35) increases AI probability
        # Low entropy and vocabulary uniformity increases AI probability
        # High marker phrase density increases AI probability
        burstiness_factor = max(0.0, (55.0 - burstiness) * 1.2)
        entropy_factor = max(0.0, (entropy - 75.0) * 1.5)  # Very flat entropy curve is AI-like
        marker_density = (marker_count / max(len(sentences), 1)) * 35.0

        raw_ai_score = (burstiness_factor * 0.45) + (entropy_factor * 0.25) + (marker_density * 0.30)
        
        # Clamp to 0 - 100%
        ai_probability = min(98.0, max(2.0, round(raw_ai_score, 1)))
        human_probability = round(100.0 - ai_probability, 1)

        # Classification
        if ai_probability < 25.0:
            ai_risk_level = "Human-Written Content"
            status_class = "success"
            verdict_desc = "Natural sentence length variance and organic syntax typical of human authorship."
        elif ai_probability < 65.0:
            ai_risk_level = "Mixed / AI-Assisted Content"
            status_class = "warning"
            verdict_desc = "Moderate structural uniformity detected. Text may contain AI-assisted editing or generation."
        else:
            ai_risk_level = "Likely AI-Generated"
            status_class = "danger"
            verdict_desc = "High structural uniformity, low burstiness, and repetitive syntactic patterns typical of LLMs."

        # Sentence-level AI inspection
        flagged_sentences = []
        mean_sentence_len = len(words) / max(len(sentences), 1)

        for s in sentences:
            s_words = self.tokenize_words(s)
            s_len = len(s_words)
            has_marker = any(p in s.lower() for p in self.AI_MARKER_PHRASES)
            
            # Sentence is flagged if it falls near the uniform mean length and contains LLM markers
            is_ai_typical = (abs(s_len - mean_sentence_len) < 4 and s_len > 12) or has_marker
            
            flagged_sentences.append({
                "sentence": s,
                "is_ai_typical": is_ai_typical,
                "word_count": s_len,
                "has_llm_markers": has_marker,
            })

        return {
            "ai_probability": ai_probability,
            "human_probability": human_probability,
            "ai_risk_level": ai_risk_level,
            "status_class": status_class,
            "verdict_description": verdict_desc,
            "burstiness": burstiness,
            "lexical_diversity": diversity,
            "entropy": entropy,
            "ai_marker_count": marker_count,
            "total_sentences": len(sentences),
            "flagged_ai_sentences_count": sum(1 for f in flagged_sentences if f["is_ai_typical"]),
            "flagged_sentences": flagged_sentences,
        }
