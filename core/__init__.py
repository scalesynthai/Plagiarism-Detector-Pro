"""
ScaleSynthAI Plagiarism Detector Pro - Core Analysis Engine
"""

from core.checker import PlagiarismChecker
from core.ai_detector import AIDetector
from core.citation_validator import CitationValidator
from core.evidence_analyzer import EvidenceAnalyzer
from core.vector_engine import VectorSearchEngine
from core.batch_processor import BatchProcessor
from core.report_generator import ReportGenerator
from core.extractor import extract_text_from_file, is_allowed_file
from core.web_searcher import LiveWebSearcher

__all__ = [
    "PlagiarismChecker",
    "AIDetector",
    "CitationValidator",
    "EvidenceAnalyzer",
    "VectorSearchEngine",
    "BatchProcessor",
    "ReportGenerator",
    "LiveWebSearcher",
    "extract_text_from_file",
    "is_allowed_file",
]
