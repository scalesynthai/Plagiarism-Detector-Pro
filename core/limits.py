import re

MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 100_000
MAX_SENTENCE_WORDS = 500


def validate_text(text):
    if not isinstance(text, str):
        raise ValueError('Document text must be a string.')
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError('Document exceeds the 100,000 character analysis limit.')
    for sentence in re.split(r'(?<=[.!?])\s+|\n{2,}', text):
        if len(sentence.split()) > MAX_SENTENCE_WORDS:
            raise ValueError('A passage exceeds 500 words. Split long passages into sentences.')
    return text
