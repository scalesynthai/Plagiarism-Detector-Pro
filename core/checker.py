import math
import os
import re
import io
import tempfile
import threading
from typing import Dict, List, Tuple, Any, Optional, Set
from core.limits import validate_text
from core.matching import match_document
from core.extractor import extract_text_from_file, is_allowed_file
from core.web_searcher import LiveWebSearcher
from core.ai_detector import AIDetector
from core.citation_validator import CitationValidator
from core.vector_engine import VectorSearchEngine
from core.sanitizer import TextSanitizer
from core.phd_auditor import PhdResearchAuditor


class PlagiarismChecker:
    """Lexical-overlap analysis plus advisory writing diagnostics."""

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
        self._source_lock = threading.RLock()
        self._source_signature = None
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
        sources = {}
        vector_engine = VectorSearchEngine(vector_dim=128)
        if not self.sources_dir:
            return

        # Auto-seed missing default sources if a default_sources directory exists (e.g. inside Docker)
        seed_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "default_sources")
        if os.path.isdir(seed_dir) and not os.path.exists(os.path.join(self.sources_dir, ".seeded")):
            os.makedirs(self.sources_dir, exist_ok=True)
            for seed_file in os.listdir(seed_dir):
                target_file = os.path.join(self.sources_dir, seed_file)
                if not os.path.exists(target_file):
                    try:
                        import shutil
                        shutil.copy2(os.path.join(seed_dir, seed_file), target_file)
                    except Exception:
                        pass

            open(os.path.join(self.sources_dir, ".seeded"), "a").close()

        if not os.path.exists(self.sources_dir):
            self.sources = {}
            self.vector_engine = vector_engine
            return

        for fname in os.listdir(self.sources_dir):
            fpath = os.path.join(self.sources_dir, fname)
            if not os.path.islink(fpath) and os.path.isfile(fpath) and is_allowed_file(fname):
                try:
                    text = extract_text_from_file(fpath)
                    if text.strip():
                        words = self.tokenize(text)
                        sentences = self.split_into_sentences(text)
                        sources[fname] = {
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
                        vector_engine.add_document(fname, text, {"filename": fname})
                except Exception as e:
                    print(f"Warning: Could not index source '{fname}': {e}")

        self.sources = sources
        self.vector_engine = vector_engine

    def refresh_sources(self):
        """Refresh each worker's snapshot when persisted corpus files change."""
        if not self.sources_dir:
            return
        with self._source_lock:
            if not os.path.isdir(self.sources_dir):
                self.sources = {}
                self.vector_engine = VectorSearchEngine(vector_dim=128)
                self._source_signature = None
                return
            signature = []
            for entry in os.scandir(self.sources_dir):
                if entry.is_file(follow_symlinks=False) and is_allowed_file(entry.name):
                    try:
                        stat = entry.stat()
                        signature.append((entry.name, stat.st_mtime_ns, stat.st_size))
                    except FileNotFoundError:
                        continue
            signature = tuple(sorted(signature))
            if signature != self._source_signature:
                self.reload_sources()
                self._source_signature = signature

    @staticmethod
    def _validate_source_name(filename):
        if (not filename or os.path.basename(filename) != filename or
                "\\" in filename or not is_allowed_file(filename)):
            raise ValueError("Invalid source filename.")

    def add_source(self, filename: str, content_or_stream) -> Dict[str, Any]:
        """Validate first, then publish a complete file without overwriting sources."""
        self._validate_source_name(filename)
        if not self.sources_dir:
            raise ValueError("No sources directory configured.")
        os.makedirs(self.sources_dir, exist_ok=True)
        if hasattr(content_or_stream, 'read'):
            content_or_stream.seek(0)
            content = content_or_stream.read()
        elif isinstance(content_or_stream, str):
            content = content_or_stream.encode('utf-8')
        elif isinstance(content_or_stream, (bytes, bytearray)):
            content = bytes(content_or_stream)
        else:
            raise ValueError("Unsupported content type for source file.")
        text = extract_text_from_file(io.BytesIO(content), filename)
        if not text.strip():
            raise ValueError("Source contains no extractable text.")
        target = os.path.join(self.sources_dir, filename)
        with self._source_lock:
            fd, temporary = tempfile.mkstemp(dir=self.sources_dir, prefix='.upload-')
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(content)
                os.link(temporary, target)  # Atomic and fails if target already exists.
            finally:
                os.unlink(temporary)
            self.refresh_sources()
            return self.sources[filename]

    def delete_source(self, filename: str) -> bool:
        self._validate_source_name(filename)
        if not self.sources_dir:
            return False
        with self._source_lock:
            try:
                os.remove(os.path.join(self.sources_dir, filename))
            except FileNotFoundError:
                return False
            self.refresh_sources()
            return True

    def list_sources(self) -> List[Dict[str, Any]]:
        """Returns metadata for all indexed institutional reference sources."""
        self.refresh_sources()
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
        result = match_document(s1, {"reference": {"filename": "reference", "text": s2}})
        return result["overall_similarity"]

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

    def analyze(self, query_text: str, include_web_sources: bool = True, exclude_quotes: bool = False, private_draft: bool = False, exclude_bibliography: bool = False) -> Dict[str, Any]:
        """
        Analyze exact lexical overlap and attach advisory writing diagnostics.
        """
        validate_text(query_text)
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
        
        # 2. Run the uncalibrated writing-pattern heuristic
        ai_analysis = self.ai_detector.analyze(cleaned_text)

        # 3. Run PhD Conference & Double-Blind Anonymity Auditor
        phd_audit = PhdResearchAuditor.audit_manuscript(cleaned_text)

        # Build candidate pool: Local Institutional Corpus + Real-Time Global Repositories
        self.refresh_sources()
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

        matching = match_document(cleaned_text, {key: dict(value) for key, value in active_pool.items()},
                                  exclude_quotes, exclude_bibliography)
        for row in matching["sources_breakdown"]:
            row["smart_citations"] = self.generate_smart_citations(row["filename"], row.get("url"))
        for row in matching["highlighted_sentences"]:
            row["smart_citations"] = self.generate_smart_citations(row["source"], row.get("url")) if row["source"] else None
            row["paraphrase_advice"] = self.generate_paraphrase_advice(row["text"], row["similarity"]) if row["is_plagiarized"] else None
        for row in matching["diff_matches"]:
            row["smart_citations"] = self.generate_smart_citations(row["source_name"], row.get("source_url"))
            row["paraphrase_advice"] = self.generate_paraphrase_advice(row["student_sentence"], row["similarity"])
        overall_sim = matching["overall_similarity"]

        # 4. Advisory similarity tier
        if overall_sim < 15.0:
            safeassign_risk = "Low Risk"
            verdict = "Low Observed Similarity"
            status_class = "success"
            verdict_description = "Little lexical overlap was found in the sources searched. Unretrieved sources and paraphrases are not ruled out."
        elif overall_sim < 40.0:
            safeassign_risk = "Medium Risk"
            verdict = "Medium Risk / Moderate Similarity"
            status_class = "warning"
            verdict_description = "Matching text was found in the searched sources. Review the passages and their attribution."
        else:
            safeassign_risk = "High Risk"
            verdict = "High Risk / Critical Similarity"
            status_class = "danger"
            verdict_description = "Substantial matching text was found. Review the passages and their attribution; similarity alone does not establish plagiarism."

        return {
            **matching,
            "safeassign_risk": safeassign_risk,
            "verdict": verdict,
            "verdict_description": verdict_description,
            "status_class": status_class,
            "live_sources_queried": live_sources_count,
            "total_corpus_searched": len(active_pool),
            "ai_analysis": ai_analysis,
            "citation_analysis": citation_analysis,
            "readability": readability,
            "obfuscation_info": obfuscation_info,
            "phd_audit": phd_audit,
            "is_private_draft": private_draft,
        }
