import math
import os
import re
from typing import Dict, List, Tuple, Any, Optional, Set
from core.extractor import extract_text_from_file, is_allowed_file
from core.web_searcher import LiveWebSearcher
from core.ai_detector import AIDetector
from core.citation_validator import CitationValidator
from core.vector_engine import VectorSearchEngine
from core.sanitizer import TextSanitizer
from core.phd_auditor import PhdResearchAuditor


class PlagiarismChecker:
    """
    Enterprise & University-grade Academic Originality Platform.
    Integrates:
      - SafeAssign & Turnitin Multi-Layer Plagiarism Engine (LCS, Shingling, TF-IDF Cosine)
      - Statistical AI-Generated Content & LLM Likelihood Detection
      - Citation & Bibliography Integrity Validator
      - Semantic Vector Indexing
      - Global Internet & Academic Database Crawler (Wikipedia, arXiv, CrossRef, OpenAlex)
      - Side-by-Side Synchronized Diff Alignment
    """

    STOPWORDS = {
        'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'as', 'at',
        'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'could', 'did',
        'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'has', 'have',
        'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into',
        'is', 'it', 'its', 'itself', 'just', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 'of', 'off',
        'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same',
        'she', 'should', 'so', 'some', 'such', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves',
        'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very',
        'was', 'we', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'with', 'would',
        'you', 'your', 'yours', 'yourself', 'yourselves'
    }

    def __init__(self, sources_dir: Optional[str] = None, search_timeout: int = 4):
        self.sources_dir = sources_dir
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.web_searcher = LiveWebSearcher(timeout=search_timeout)
        self.ai_detector = AIDetector()
        self.citation_validator = CitationValidator()
        self.vector_engine = VectorSearchEngine(vector_dim=128)

        if sources_dir:
            self.reload_sources()

    def reload_sources(self):
        """Loads and indexes all documents from the institutional corpus directory."""
        self.sources.clear()
        if not self.sources_dir:
            return

        # Auto-seed missing default sources if a default_sources directory exists (e.g. inside Docker)
        seed_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "default_sources")
        if os.path.exists(seed_dir) and os.path.isdir(seed_dir):
            os.makedirs(self.sources_dir, exist_ok=True)
            for seed_file in os.listdir(seed_dir):
                target_file = os.path.join(self.sources_dir, seed_file)
                if not os.path.exists(target_file):
                    try:
                        import shutil
                        shutil.copy2(os.path.join(seed_dir, seed_file), target_file)
                    except Exception:
                        pass

        if not os.path.exists(self.sources_dir):
            return

        for fname in os.listdir(self.sources_dir):
            fpath = os.path.join(self.sources_dir, fname)
            if os.path.isfile(fpath) and is_allowed_file(fname):
                try:
                    text = extract_text_from_file(fpath)
                    if text.strip():
                        words = self.tokenize(text)
                        sentences = self.split_into_sentences(text)
                        self.sources[fname] = {
                            "filename": fname,
                            "filepath": fpath,
                            "text": text,
                            "words": words,
                            "word_count": len(words),
                            "sentences": sentences,
                            "tf": self.compute_tf(words),
                            "source_type": "institutional_corpus",
                            "badge": "🏛️ Institutional Repository",
                            "url": None,
                        }
                        self.vector_engine.add_document(fname, text, {"filename": fname})
                except Exception as e:
                    print(f"Warning: Could not index source '{fname}': {e}")

    def add_source(self, filename: str, content_or_stream) -> Dict[str, Any]:
        """Saves a new source to the institutional repository and indexes it."""
        if not self.sources_dir:
            raise ValueError("No sources directory configured.")
        os.makedirs(self.sources_dir, exist_ok=True)
        
        target_path = os.path.join(self.sources_dir, filename)
        if hasattr(content_or_stream, 'save'):
            content_or_stream.save(target_path)
        elif isinstance(content_or_stream, (bytes, bytearray)):
            with open(target_path, 'wb') as f:
                f.write(content_or_stream)
        elif isinstance(content_or_stream, str):
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content_or_stream)
        else:
            raise ValueError("Unsupported content type for source file.")

        self.reload_sources()
        return self.sources.get(filename, {})

    def delete_source(self, filename: str) -> bool:
        """Deletes a source file from the repository."""
        if not self.sources_dir:
            return False
        fpath = os.path.join(self.sources_dir, filename)
        if os.path.exists(fpath):
            os.remove(fpath)
            self.reload_sources()
            return True
        return False

    def list_sources(self) -> List[Dict[str, Any]]:
        """Returns metadata for all indexed institutional reference sources."""
        result = []
        for name, data in sorted(self.sources.items()):
            preview = data["text"][:160].replace("\n", " ")
            if len(data["text"]) > 160:
                preview += "..."
            result.append({
                "filename": name,
                "word_count": data["word_count"],
                "sentence_count": len(data["sentences"]),
                "preview": preview,
                "source_type": data.get("source_type", "institutional_corpus"),
                "badge": data.get("badge", "🏛️ Institutional Repository"),
            })
        return result

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return re.sub(r"[^\w\s]", " ", text.lower()).split()

    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        raw_sentences = re.split(r'(?<=[.!?])\s+|\n{2,}', text)
        return [s.strip() for s in raw_sentences if len(s.strip()) > 3]

    @staticmethod
    def extract_quotations(text: str) -> List[str]:
        quotes = re.findall(r'["“«]([^"”»]+)["”»]', text)
        return [q.strip() for q in quotes if len(q.strip()) > 10]

    @staticmethod
    def compute_tf(words: List[str]) -> Dict[str, int]:
        tf = {}
        for w in words:
            tf[w] = tf.get(w, 0) + 1
        return tf

    @staticmethod
    def get_shingles(words: List[str], n: int = 4) -> Set[Tuple[str, ...]]:
        if len(words) < n:
            return {tuple(words)} if words else set()
        return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}

    @staticmethod
    def longest_common_subsequence(w1: List[str], w2: List[str]) -> int:
        m, n = len(w1), len(w2)
        if m == 0 or n == 0:
            return 0
        dp = [0] * (n + 1)
        for i in range(1, m + 1):
            prev = 0
            for j in range(1, n + 1):
                temp = dp[j]
                if w1[i - 1] == w2[j - 1]:
                    dp[j] = prev + 1
                else:
                    dp[j] = max(dp[j], dp[j - 1])
                prev = temp
        return dp[n]

    def compute_cosine_similarity(self, words1: List[str], words2: List[str]) -> float:
        if not words1 or not words2:
            return 0.0

        unique_words = set(words1).union(set(words2))
        tf1 = self.compute_tf(words1)
        tf2 = self.compute_tf(words2)

        dot_product = 0.0
        for w in unique_words:
            weight = 0.4 if w in self.STOPWORDS else 1.0
            dot_product += (tf1.get(w, 0) * weight) * (tf2.get(w, 0) * weight)

        mag1 = math.sqrt(sum(((tf1.get(w, 0) * (0.4 if w in self.STOPWORDS else 1.0))**2) for w in tf1))
        mag2 = math.sqrt(sum(((tf2.get(w, 0) * (0.4 if w in self.STOPWORDS else 1.0))**2) for w in tf2))

        if mag1 == 0 or mag2 == 0:
            return 0.0

        return (dot_product / (mag1 * mag2)) * 100.0

    def compute_sentence_similarity(self, s1: str, s2: str) -> float:
        s1_clean = re.sub(r'[^\w\s]', '', s1.lower()).strip()
        s2_clean = re.sub(r'[^\w\s]', '', s2.lower()).strip()
        
        # Exact match fast path
        if s1_clean and s2_clean and s1_clean == s2_clean:
            return 100.0

        w1 = self.tokenize(s1)
        w2 = self.tokenize(s2)
        if not w1 or not w2:
            return 0.0

        # Substring exact containment (for phrases of at least 4 words)
        if len(w1) >= 4 and (s1_clean in s2_clean or s2_clean in s1_clean):
            return 100.0

        # Shingling: 3-grams and 4-grams require sequential phrase matching
        shingles1_3 = self.get_shingles(w1, 3)
        shingles2_3 = self.get_shingles(w2, 3)
        shingle_score_3 = (len(shingles1_3.intersection(shingles2_3)) / max(min(len(shingles1_3), len(shingles2_3)), 1) * 100.0) if (shingles1_3 and shingles2_3) else 0.0

        shingles1_4 = self.get_shingles(w1, 4)
        shingles2_4 = self.get_shingles(w2, 4)
        shingle_score_4 = (len(shingles1_4.intersection(shingles2_4)) / max(min(len(shingles1_4), len(shingles2_4)), 1) * 100.0) if (shingles1_4 and shingles2_4) else 0.0

        lcs_len = self.longest_common_subsequence(w1, w2)
        lcs_score = (lcs_len / max(min(len(w1), len(w2)), 1)) * 100.0

        # Sequential structural overlap must be present to consider text matching.
        # If there are no contiguous 3-grams and LCS is under 4 words, this is domain vocabulary, not plagiarism.
        if shingle_score_3 == 0.0 and lcs_len < 4:
            return 0.0

        cosine = self.compute_cosine_similarity(w1, w2)

        # Composite score heavily weighting sequential phrase preservation
        composite = (shingle_score_3 * 0.40) + (shingle_score_4 * 0.20) + (lcs_score * 0.25) + (cosine * 0.15)
        
        return min(100.0, max(composite, shingle_score_3, shingle_score_4, lcs_score))

    @staticmethod
    def generate_smart_citations(source_name: str, source_url: Optional[str] = None) -> Dict[str, str]:
        """Generates ready-to-copy APA 7th, MLA 9th, and IEEE formatted citations."""
        clean_name = re.sub(r'\.(txt|pdf|docx|md)$', '', source_name)
        clean_title = clean_name.replace('_', ' ').replace('-', ' ').title()
        url_text = f", {source_url}" if source_url else ""
        year = "2024"

        if source_url and "arxiv.org" in source_url:
            apa = f"Author et al. ({year}). {clean_title}. arXiv preprint {source_url}."
            mla = f'"{clean_title}." arXiv, {year}, {source_url}.'
            ieee = f'[1] "{clean_title}," arXiv preprint, {year}, {source_url}.'
        elif source_url and "wikipedia.org" in source_url:
            apa = f"Wikipedia contributors. ({year}). {clean_title}. In Wikipedia, The Free Encyclopedia."
            mla = f'"{clean_title}." Wikipedia, Wikimedia Foundation, 2024, {source_url}.'
            ieee = f'[1] "{clean_title}," Wikipedia, The Free Encyclopedia, 2024. [Online]. Available: {source_url}.'
        else:
            apa = f"{clean_title}. ({year}). Institutional Scholarly Archive{url_text}."
            mla = f'"{clean_title}." Institutional Repository, {year}{url_text}.'
            ieee = f'[1] "{clean_title}," Institutional Academic Database, {year}.'

        return {
            "apa": apa,
            "mla": mla,
            "ieee": ieee,
            "source_title": clean_title,
        }

    @staticmethod
    def generate_paraphrase_advice(student_sentence: str, similarity_score: float) -> str:
        """Provides student coaching advice on ethical synthesis and rephrasing."""
        if similarity_score >= 80.0:
            return "Verbatim or near-identical phrasing. Synthesize the finding in your own words and introduce with an attribution clause (e.g. 'Researchers demonstrate that...')."
        elif similarity_score >= 60.0:
            return "Substantial syntax overlap. Invert sentence structure, emphasize your argument's perspective, and insert the parenthetical citation."
        else:
            return "Moderate terminology overlap. If keeping specialized phrasing, place quotation marks or cite the source authority."

    def analyze(self, query_text: str, include_web_sources: bool = True, exclude_quotes: bool = False, private_draft: bool = False) -> Dict[str, Any]:
        """
        Executes complete academic plagiarism, AI content, obfuscation defense, and citation analysis.
        Strictly enforces continuous passage verification and proportional SafeAssign overlap scoring.
        """
        # 0. Adversarial Obfuscation & Readability Pre-Check
        sanitization = TextSanitizer.analyze_and_sanitize(query_text)
        cleaned_text = sanitization["sanitized_text"]
        readability = sanitization["readability"]
        obfuscation_info = {
            "has_obfuscation": sanitization["has_obfuscation"],
            "homoglyphs_detected": sanitization["homoglyphs_detected"],
            "zero_width_chars_detected": sanitization["zero_width_chars_detected"],
            "details": sanitization["obfuscation_details"]
        }

        # 1. Run Citation and Bibliography Validator
        citation_analysis = self.citation_validator.validate_citations(cleaned_text)
        
        # 2. Run AI-Generated Content & LLM Detector
        ai_analysis = self.ai_detector.analyze(cleaned_text)

        # 3. Run PhD Conference & Double-Blind Anonymity Auditor
        phd_audit = PhdResearchAuditor.audit_manuscript(cleaned_text)

        query_words = self.tokenize(cleaned_text)
        query_sentences = self.split_into_sentences(cleaned_text)
        extracted_quotes = self.extract_quotations(cleaned_text)

        if not query_words:
            return {
                "overall_similarity": 0.0,
                "safeassign_risk": "Low Risk",
                "verdict": "Empty or Invalid Input",
                "status_class": "success",
                "highest_matching_source": None,
                "highest_similarity": 0.0,
                "sources_breakdown": [],
                "highlighted_sentences": [],
                "diff_matches": [],
                "total_words": 0,
                "total_sentences": 0,
                "plagiarized_sentences_count": 0,
                "flagged_word_count": 0,
                "quotes_count": 0,
                "live_sources_queried": 0,
                "total_corpus_searched": 0,
                "ai_analysis": ai_analysis,
                "citation_analysis": citation_analysis,
                "readability": readability,
                "obfuscation_info": obfuscation_info,
                "phd_audit": phd_audit,
                "is_private_draft": private_draft,
            }

        # Build candidate pool: Local Institutional Corpus + Real-Time Global Repositories
        active_pool: Dict[str, Dict[str, Any]] = dict(self.sources)
        live_sources_count = 0

        if include_web_sources:
            live_sources = self.web_searcher.search_live_sources(cleaned_text)
            live_sources_count = len(live_sources)
            for idx, live_s in enumerate(live_sources):
                s_name = live_s["filename"]
                s_text = live_s["text"]
                s_words = self.tokenize(s_text)
                s_sentences = self.split_into_sentences(s_text)
                active_pool[f"global_{idx}_{s_name}"] = {
                    "filename": s_name,
                    "filepath": None,
                    "text": s_text,
                    "words": s_words,
                    "word_count": len(s_words),
                    "sentences": s_sentences,
                    "tf": self.compute_tf(s_words),
                    "source_type": live_s.get("source_type", "global_academic"),
                    "badge": live_s.get("badge", "🌐 Global Web"),
                    "url": live_s.get("url"),
                }

        # 1. Sentence-Level Deep Matching & Side-by-Side Diff Assembly
        highlighted_sentences = []
        diff_matches = []
        plagiarized_count = 0
        flagged_word_count = 0
        
        # Track word-level matches per source to compute true proportional overlap
        source_matched_words: Dict[str, int] = {}
        source_max_similarity: Dict[str, float] = {}
        source_match_sentences: Dict[str, int] = {}

        total_words_count = max(len(query_words), 1)

        for s in query_sentences:
            s_words = self.tokenize(s)
            s_len = len(s_words)
            is_quoted = any(s in q or q in s for q in extracted_quotes)
            has_citation, citation_str = self.citation_validator.has_in_text_citation(s)

            best_match_score = 0.0
            best_match_src = None
            best_match_url = None
            best_match_badge = None
            best_match_src_sentence = None
            best_source_key = None

            for key, sdata in active_pool.items():
                for src_s in sdata["sentences"]:
                    score = self.compute_sentence_similarity(s, src_s)
                    if score > best_match_score:
                        best_match_score = score
                        best_match_src = sdata["filename"]
                        best_match_url = sdata.get("url")
                        best_match_badge = sdata.get("badge")
                        best_match_src_sentence = src_s
                        best_source_key = key

            # Academic threshold: 52% similarity with sequential match indicates overlapping material
            is_plagiarized = (best_match_score >= 52.0) and not (exclude_quotes and (is_quoted or has_citation))

            smart_cite = self.generate_smart_citations(best_match_src or "Reference Source", best_match_url) if best_match_src else None
            paraphrase_tip = self.generate_paraphrase_advice(s, best_match_score) if is_plagiarized else None

            if is_plagiarized and best_source_key:
                plagiarized_count += 1
                flagged_word_count += s_len
                
                source_matched_words[best_source_key] = source_matched_words.get(best_source_key, 0) + s_len
                source_match_sentences[best_source_key] = source_match_sentences.get(best_source_key, 0) + 1
                source_max_similarity[best_source_key] = max(source_max_similarity.get(best_source_key, 0.0), best_match_score)

                # Append to side-by-side diff matches
                diff_matches.append({
                    "student_sentence": s,
                    "matched_sentence": best_match_src_sentence,
                    "source_name": best_match_src,
                    "source_url": best_match_url,
                    "badge": best_match_badge,
                    "similarity": round(best_match_score, 1),
                    "is_quoted": is_quoted,
                    "has_citation": has_citation,
                    "citation": citation_str,
                    "smart_citations": smart_cite,
                    "paraphrase_advice": paraphrase_tip,
                })

            highlighted_sentences.append({
                "text": s,
                "is_plagiarized": is_plagiarized,
                "is_quoted": is_quoted,
                "has_citation": has_citation,
                "similarity": round(best_match_score, 1),
                "source": best_match_src if is_plagiarized else None,
                "url": best_match_url if is_plagiarized else None,
                "badge": best_match_badge if is_plagiarized else None,
                "matched_source_sentence": best_match_src_sentence if is_plagiarized else None,
                "smart_citations": smart_cite,
                "paraphrase_advice": paraphrase_tip,
            })

        # 2. Build Sources Breakdown
        # Only sources that have actual verified sentence matches appear with positive percentages
        sources_breakdown = []
        highest_similarity = 0.0
        highest_matching_source = None
        highest_matching_url = None

        for key, sdata in active_pool.items():
            matched_w = source_matched_words.get(key, 0)
            
            # If it's a web/global source with 0 matched sentences, completely discard to prevent false positives
            if key.startswith("global_") and matched_w == 0:
                continue

            # Proportional SafeAssign similarity: percentage of the submission's words matched in this source
            prop_sim = min(100.0, (matched_w / total_words_count) * 100.0)
            
            smart_cite = self.generate_smart_citations(sdata["filename"], sdata.get("url"))

            source_entry = {
                "filename": sdata["filename"],
                "similarity": round(prop_sim, 2),
                "max_passage_similarity": round(source_max_similarity.get(key, 0.0), 1),
                "matched_sentences_count": source_match_sentences.get(key, 0),
                "common_words_count": matched_w,
                "source_word_count": sdata["word_count"],
                "badge": sdata.get("badge", "🏛️ Institutional"),
                "source_type": sdata.get("source_type", "institutional"),
                "url": sdata.get("url"),
                "smart_citations": smart_cite,
            }
            sources_breakdown.append(source_entry)

            if prop_sim > highest_similarity:
                highest_similarity = prop_sim
                highest_matching_source = sdata["filename"]
                highest_matching_url = sdata.get("url")

        sources_breakdown.sort(key=lambda x: x["similarity"], reverse=True)

        # 3. SafeAssign Overall Overlap Ratio
        # Overall similarity is strictly the ratio of flagged passage words to total submission words
        overall_sim = min(100.0, (flagged_word_count / total_words_count) * 100.0)

        # 4. SafeAssign Risk Level
        if overall_sim < 15.0:
            safeassign_risk = "Low Risk"
            verdict = "Low / Unique Content (Acceptable)"
            status_class = "success"
            verdict_description = "The submission contains minimal common phrasing typical of original academic writing."
        elif overall_sim < 40.0:
            safeassign_risk = "Medium Risk"
            verdict = "Medium Risk / Moderate Similarity"
            status_class = "warning"
            verdict_description = "Substantial citations, paraphrasing, or matching phrases detected. Review source attribution."
        else:
            safeassign_risk = "High Risk"
            verdict = "High Risk / Critical Similarity"
            status_class = "danger"
            verdict_description = "High probability of uncredited material, verbatim duplication, or significant academic overlap."

        return {
            "overall_similarity": round(overall_sim, 2),
            "safeassign_risk": safeassign_risk,
            "verdict": verdict,
            "verdict_description": verdict_description,
            "status_class": status_class,
            "highest_similarity": round(highest_similarity, 2),
            "highest_matching_source": highest_matching_source,
            "highest_matching_url": highest_matching_url,
            "sources_breakdown": sources_breakdown[:15],
            "highlighted_sentences": highlighted_sentences,
            "diff_matches": diff_matches,
            "total_words": len(query_words),
            "total_sentences": len(query_sentences),
            "plagiarized_sentences_count": plagiarized_count,
            "flagged_word_count": flagged_word_count,
            "quotes_count": len(extracted_quotes),
            "live_sources_queried": live_sources_count,
            "total_corpus_searched": len(active_pool),
            "ai_analysis": ai_analysis,
            "citation_analysis": citation_analysis,
            "readability": readability,
            "obfuscation_info": obfuscation_info,
            "phd_audit": phd_audit,
            "is_private_draft": private_draft,
        }
