import difflib
import re
from typing import Dict, List, Any


class DraftComparator:
    """
    Compares two academic manuscript drafts (Draft v1 vs Draft v2) to
    quantify revisions, identify added/removed/altered passages, and track originality drift.
    """

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        raw = re.split(r'(?<=[.!?])\s+|\n{2,}', text)
        return [s.strip() for s in raw if len(s.strip()) > 3]

    @classmethod
    def compare_drafts(cls, draft_v1: str, draft_v2: str) -> Dict[str, Any]:
        s1 = cls.split_sentences(draft_v1)
        s2 = cls.split_sentences(draft_v2)

        w1_count = len(re.findall(r'\b\w+\b', draft_v1))
        w2_count = len(re.findall(r'\b\w+\b', draft_v2))

        matcher = difflib.SequenceMatcher(None, s1, s2)
        
        unchanged_sentences = []
        modified_blocks = []
        added_sentences = []
        deleted_sentences = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for idx in range(i1, i2):
                    unchanged_sentences.append(s1[idx])
            elif tag == 'replace':
                modified_blocks.append({
                    "v1": s1[i1:i2],
                    "v2": s2[j1:j2]
                })
            elif tag == 'insert':
                for idx in range(j1, j2):
                    added_sentences.append(s2[idx])
            elif tag == 'delete':
                for idx in range(i1, i2):
                    deleted_sentences.append(s1[idx])

        similarity_ratio = round(matcher.ratio() * 100.0, 1)
        revision_percent = round((1.0 - matcher.ratio()) * 100.0, 1)

        return {
            "draft_v1_words": w1_count,
            "draft_v2_words": w2_count,
            "words_delta": w2_count - w1_count,
            "draft_v1_sentences": len(s1),
            "draft_v2_sentences": len(s2),
            "similarity_percentage": similarity_ratio,
            "revision_percentage": revision_percent,
            "unchanged_count": len(unchanged_sentences),
            "added_count": len(added_sentences),
            "deleted_count": len(deleted_sentences),
            "modified_blocks_count": len(modified_blocks),
            "added_sentences": added_sentences,
            "deleted_sentences": deleted_sentences,
            "modified_blocks": modified_blocks,
        }
