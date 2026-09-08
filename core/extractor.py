import io
import os
import re
import json
import docx
from pypdf import PdfReader


ALLOWED_EXTENSIONS = {'.txt', '.md', '.docx', '.pdf', '.rtf', '.csv', '.tex', '.bib', '.ipynb'}


def is_allowed_file(filename: str) -> bool:
    """Check if the filename has a supported extension."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def extract_text_from_file(file_input, filename: str = None) -> str:
    """
    Extracts text content from academic manuscripts across diverse formats
    including LaTeX (.tex, .bib), Jupyter Notebooks (.ipynb), Word (.docx), Adobe PDF (.pdf), and Plain Text.
    
    :param file_input: Either a file path (str), binary stream, or Werkzeug FileStorage.
    :param filename: Optional filename (used to detect extension if file_input is a stream).
    :return: Extracted plain text string.
    """
    if hasattr(file_input, 'filename') and not filename:
        filename = file_input.filename
    elif isinstance(file_input, str) and not filename:
        filename = os.path.basename(file_input)

    if not filename:
        raise ValueError("Filename or extension must be provided.")

    ext = os.path.splitext(filename)[1].lower()

    # If file_input is a path
    if isinstance(file_input, str):
        if not os.path.exists(file_input):
            raise FileNotFoundError(f"File not found: {file_input}")
        with open(file_input, 'rb') as f:
            stream = io.BytesIO(f.read())
    elif hasattr(file_input, 'read'):
        # Reset stream position if possible
        if hasattr(file_input, 'seek'):
            file_input.seek(0)
        content = file_input.read()
        stream = io.BytesIO(content) if isinstance(content, bytes) else io.BytesIO(content.encode('utf-8'))
    else:
        raise ValueError("Invalid file input type.")

    if ext in {'.txt', '.md', '.csv', '.rtf', '.bib'}:
        return _extract_plain_text(stream)
    elif ext == '.docx':
        return _extract_docx(stream)
    elif ext == '.pdf':
        return _extract_pdf(stream)
    elif ext == '.tex':
        return _extract_latex(stream)
    elif ext == '.ipynb':
        return _extract_jupyter_notebook(stream)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}")


def _extract_plain_text(stream: io.BytesIO) -> str:
    """Decodes plain text stream with encoding fallbacks."""
    data = stream.getvalue()
    for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']:
        try:
            return data.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', errors='ignore').strip()


def _extract_docx(stream: io.BytesIO) -> str:
    """Extracts text from Word .docx document stream."""
    try:
        doc = docx.Document(stream)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)
        return "\n\n".join(paragraphs).strip()
    except Exception as e:
        raise ValueError(f"Failed to read DOCX file: {str(e)}")


def _extract_pdf(stream: io.BytesIO) -> str:
    """Extracts text from PDF stream."""
    try:
        reader = PdfReader(stream)
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages_text.append(text.strip())
        return "\n\n".join(pages_text).strip()
    except Exception as e:
        raise ValueError(f"Failed to read PDF file: {str(e)}")


def _extract_latex(stream: io.BytesIO) -> str:
    """
    Intelligently parses academic LaTeX documents (.tex):
    - Strips comments and unrendered TeX boilerplate
    - Isolates mathematical environments from triggering plagiarism false alarms
    - Transforms citation keys (\\cite{...}) into verifiable academic parentheticals
    """
    raw = _extract_plain_text(stream)
    
    # 1. Strip comments (% to end of line, avoiding escaped \%)
    cleaned = re.sub(r'(?<!\\)%.*$', '', raw, flags=re.MULTILINE)
    
    # 2. Map LaTeX citation macros to standard academic citation text
    cleaned = re.sub(r'\\cite[pt]?\{([^}]+)\}', r'(\1, 2024)', cleaned)
    cleaned = re.sub(r'\\parencite\{([^}]+)\}', r'(\1, 2024)', cleaned)
    cleaned = re.sub(r'\\citet\{([^}]+)\}', r'\1 (2024)', cleaned)

    # 3. Isolate math blocks to prevent false formula plagiarism flags
    cleaned = re.sub(r'\\begin\{(equation|align|gather|multline)\*?\}.*?\\end\{\1\*?\}', ' [Mathematical Formula] ', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\$\$.*?\$\$', ' [Math Display] ', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\$.*?\$', ' [Math] ', cleaned)

    # 4. Remove structural formatting macros while keeping text
    cleaned = re.sub(r'\\(section|subsection|subsubsection|paragraph|textbf|textit|emph|underline|caption)\{([^}]+)\}', r'\2', cleaned)

    # 5. Clean LaTeX environments and control sequences
    cleaned = re.sub(r'\\(begin|end)\{[^}]+\}', '', cleaned)
    cleaned = re.sub(r'\\item', '• ', cleaned)
    cleaned = re.sub(r'\\[a-zA-Z]+', ' ', cleaned)
    cleaned = re.sub(r'[{}]', '', cleaned)

    # 6. Normalize whitespace
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def _extract_jupyter_notebook(stream: io.BytesIO) -> str:
    """Extracts research documentation and commentary from Jupyter Notebooks (.ipynb)."""
    raw = _extract_plain_text(stream)
    try:
        nb = json.loads(raw)
        cells = nb.get('cells', [])
        extracted = []
        for cell in cells:
            cell_type = cell.get('cell_type')
            source = "".join(cell.get('source', []))
            if cell_type == 'markdown':
                extracted.append(source)
            elif cell_type == 'code':
                # extract docstrings and comments
                docstrings = re.findall(r'"""(.*?)"""|\'\'\'(.*?)\'\'\'', source, flags=re.DOTALL)
                for ds in docstrings:
                    doc = (ds[0] or ds[1]).strip()
                    if doc:
                        extracted.append(doc)
        return "\n\n".join(extracted).strip() if extracted else raw
    except Exception:
        return raw
