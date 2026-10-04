"""Maps internal exceptions to fixed, client-safe messages.

Responses never echo exception text. A message is shown only if it is one of
the application's own validation messages below; anything else (library
errors, paths, parser internals) becomes a generic message and is logged.
"""

PUBLIC_MESSAGES = (
    "Document text must be a string.",
    "Document exceeds the 100,000 character analysis limit.",
    "A passage exceeds 500 words. Split long passages into sentences.",
    "Document exceeds the 8 MB file limit.",
    "Filename or extension must be provided.",
    "Invalid file input type.",
    "DOCX expanded content exceeds extraction limits.",
    "Failed to read DOCX file. It may be corrupt, encrypted, or unsupported.",
    "Failed to read PDF file. It may be corrupt, encrypted, or unsupported.",
    "Archive contains too many entries (maximum 100).",
    "Archive expanded size exceeds 32 MB.",
    "Archive contains an oversized or encrypted entry.",
    "Too many documents (maximum 100).",
    "Invalid source filename.",
    "No sources directory configured.",
    "Unsupported content type for source file.",
    "Source contains no extractable text.",
    "Enter a valid email address.",
    "Sentence text must be a string.",
    "Report data must be an object.",
    "Invalid sentence text or offset.",
    "Invalid matched spans.",
    "Scores must be finite numbers between 0 and 100.",
)
_REPORT_SHAPE = "Report data has an invalid structure."
_UNSUPPORTED_FORMAT = "Unsupported file format."
_BAD_ZIP = "The uploaded file is not a valid ZIP archive."
GENERIC = "The request could not be processed."


def public_message(error: BaseException, default: str = GENERIC) -> str:
    """Return a constant, client-safe message for `error` (never the raw text)."""
    text = str(error)
    for known in PUBLIC_MESSAGES:
        if text == known:
            return known
    if text.endswith((" must be an object.", " must be an array of objects.")):
        return _REPORT_SHAPE
    if text.startswith("Unsupported file format"):
        return _UNSUPPORTED_FORMAT
    if type(error).__name__ == "BadZipFile":
        return _BAD_ZIP
    return default
