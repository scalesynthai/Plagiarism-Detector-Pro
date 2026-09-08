import io
import os
import zipfile
import concurrent.futures
from typing import Dict, List, Any
from core.extractor import extract_text_from_file, is_allowed_file


class BatchProcessor:
    """
    Processes multi-file and ZIP archive submissions for class assignments,
    generating an aggregated SafeAssign & AI originality gradebook.
    """

    def __init__(self, checker):
        self.checker = checker

    def process_zip_archive(self, zip_stream_or_path, include_web: bool = True, exclude_quotes: bool = False) -> Dict[str, Any]:
        """
        Unpacks a ZIP archive and analyzes all contained documents.
        """
        submissions = []
        if isinstance(zip_stream_or_path, str):
            with open(zip_stream_or_path, 'rb') as f:
                stream = io.BytesIO(f.read())
        elif isinstance(zip_stream_or_path, (bytes, bytearray)):
            stream = io.BytesIO(zip_stream_or_path)
        elif hasattr(zip_stream_or_path, 'read'):
            if hasattr(zip_stream_or_path, 'seek'):
                try:
                    zip_stream_or_path.seek(0)
                except Exception:
                    pass
            content = zip_stream_or_path.read()
            stream = io.BytesIO(content) if isinstance(content, bytes) else io.BytesIO(content.encode('utf-8'))
        else:
            stream = zip_stream_or_path

        with zipfile.ZipFile(stream, 'r') as zf:
            for info in zf.infolist():
                if info.is_dir() or info.filename.startswith('__MACOSX') or os.path.basename(info.filename).startswith('.'):
                    continue
                fname = os.path.basename(info.filename)
                if is_allowed_file(fname):
                    file_bytes = zf.read(info.filename)
                    submissions.append((fname, io.BytesIO(file_bytes)))

        return self.process_multiple_files(submissions, include_web=include_web, exclude_quotes=exclude_quotes)

    def process_multiple_files(self, file_tuples: List[tuple], include_web: bool = True, exclude_quotes: bool = False) -> Dict[str, Any]:
        """
        Processes a list of (filename, file_stream_or_path) concurrently.
        """
        results = []

        def analyze_single(name, stream_or_path):
            try:
                text = extract_text_from_file(stream_or_path, filename=name)
                if not text.strip():
                    return {
                        "filename": name,
                        "status": "error",
                        "error": "Empty document",
                    }

                analysis = self.checker.analyze(text, include_web_sources=include_web, exclude_quotes=exclude_quotes)
                return {
                    "filename": name,
                    "status": "success",
                    "overall_similarity": analysis["overall_similarity"],
                    "ai_probability": analysis.get("ai_analysis", {}).get("ai_probability", 0.0),
                    "ai_risk_level": analysis.get("ai_analysis", {}).get("ai_risk_level", "Unknown"),
                    "safeassign_risk": analysis["safeassign_risk"],
                    "status_class": analysis["status_class"],
                    "highest_matching_source": analysis.get("highest_matching_source"),
                    "total_words": analysis["total_words"],
                    "citations_count": analysis.get("citation_analysis", {}).get("in_text_citations_count", 0),
                    "analysis": analysis,
                }
            except Exception as e:
                return {
                    "filename": name,
                    "status": "error",
                    "error": str(e),
                }

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(analyze_single, name, fstream) for name, fstream in file_tuples]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        # Sort by similarity descending (highest risk first)
        results.sort(key=lambda x: x.get("overall_similarity", 0), reverse=True)

        # Compute batch summary statistics
        success_results = [r for r in results if r.get("status") == "success"]
        avg_plag = round(sum(r["overall_similarity"] for r in success_results) / max(len(success_results), 1), 2)
        avg_ai = round(sum(r["ai_probability"] for r in success_results) / max(len(success_results), 1), 2)

        high_risk_count = sum(1 for r in success_results if r.get("safeassign_risk") == "High Risk")
        med_risk_count = sum(1 for r in success_results if r.get("safeassign_risk") == "Medium Risk")
        low_risk_count = sum(1 for r in success_results if r.get("safeassign_risk") == "Low Risk")

        return {
            "total_submissions": len(results),
            "processed_successfully": len(success_results),
            "average_plagiarism": avg_plag,
            "average_ai_probability": avg_ai,
            "high_risk_count": high_risk_count,
            "medium_risk_count": med_risk_count,
            "low_risk_count": low_risk_count,
            "gradebook": results,
        }
