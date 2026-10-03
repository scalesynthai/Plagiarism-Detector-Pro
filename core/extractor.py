import io
import os
import re
import json
import zipfile
import unicodedata
from datetime import datetime, timezone
from core.limits import MAX_DOCUMENT_BYTES, validate_text
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
            stream = io.BytesIO(f.read(MAX_DOCUMENT_BYTES + 1))
    elif hasattr(file_input, 'read'):
        # Reset stream position if possible
        if hasattr(file_input, 'seek'):
            file_input.seek(0)
        content = file_input.read(MAX_DOCUMENT_BYTES + 1)
        stream = io.BytesIO(content) if isinstance(content, bytes) else io.BytesIO(content.encode('utf-8'))
    else:
        raise ValueError("Invalid file input type.")

    if stream.getbuffer().nbytes > MAX_DOCUMENT_BYTES:
        raise ValueError('Document exceeds the 8 MB file limit.')

    if ext in {'.txt', '.md', '.csv', '.rtf', '.bib'}:
        return validate_text(_extract_plain_text(stream))
    elif ext == '.docx':
        return validate_text(_extract_docx(stream))
    elif ext == '.pdf':
        return validate_text(_extract_pdf(stream))
    elif ext == '.tex':
        return validate_text(_extract_latex(stream))
    elif ext == '.ipynb':
        return validate_text(_extract_jupyter_notebook(stream))
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}")


def normalize_with_offset_map(text: str):
    """NFKC-normalize text while mapping every normalized character to its source offset."""
    normalized = []
    offsets = []
    for original_offset, character in enumerate(text):
        value = unicodedata.normalize('NFKC', character)
        normalized.append(value)
        offsets.extend([original_offset] * len(value))
    return "".join(normalized), offsets


def _block(block_id, block_type, text, page=None, metadata=None):
    return {
        "id": block_id,
        "type": block_type,
        "text": text,
        "page": page,
        "start_offset": 0,
        "end_offset": 0,
        "metadata": metadata or {},
    }


def _classify_plain_blocks(text: str, extension: str):
    blocks = []
    in_code = False
    reference_mode = False
    for index, raw in enumerate(re.split(r'\n\s*\n', text)):
        value = raw.strip()
        if not value:
            continue
        block_type = "paragraph"
        metadata = {}
        if extension == '.md' and value.startswith('```'):
            block_type = "code"
            in_code = not (value.count('```') % 2 == 0)
        elif in_code:
            block_type = "code"
            if '```' in value:
                in_code = False
        elif re.fullmatch(r'(?:#{1,6}\s*)?(?:references|works cited|bibliography)[:#*\s]*', value, re.I):
            block_type = "heading"
            reference_mode = True
            metadata["heading_level"] = len(value) - len(value.lstrip('#')) or 1
        elif reference_mode:
            block_type = "reference"
        elif extension == '.md' and re.match(r'^#{1,6}\s+', value):
            block_type = "heading"
            metadata["heading_level"] = len(value) - len(value.lstrip('#'))
        elif re.match(r'^(?:[-*+] |\d+[.)] )', value):
            block_type = "list_item"
        elif re.match(r'^>\s', value):
            block_type = "quotation"
        elif value.startswith('```') or (extension in {'.tex', '.ipynb'} and '[Mathematical Formula]' in value):
            block_type = "code"
        blocks.append(_block(f"block-{index + 1}", block_type, value, metadata=metadata))
    return blocks


def _docx_blocks(stream: io.BytesIO):
    stream.seek(0)
    doc = docx.Document(stream)
    blocks = []
    index = 0
    for paragraph in doc.paragraphs:
        if not paragraph.text.strip():
            continue
        index += 1
        style = paragraph.style.name if paragraph.style else ""
        block_type = "heading" if style.lower().startswith('heading') else "list_item" if 'list' in style.lower() else "paragraph"
        heading_match = re.search(r'(\d+)', style)
        metadata = {
            "style": style,
            "heading_level": int(heading_match.group(1)) if block_type == "heading" and heading_match else None,
            "bold_spans": [],
            "italic_spans": [],
        }
        cursor = 0
        for run in paragraph.runs:
            start, end = cursor, cursor + len(run.text)
            if run.bold and run.text:
                metadata["bold_spans"].append([start, end])
            if run.italic and run.text:
                metadata["italic_spans"].append([start, end])
            cursor = end
        blocks.append(_block(f"block-{index}", block_type, paragraph.text, metadata=metadata))
    for table_index, table in enumerate(doc.tables, 1):
        for row_index, row in enumerate(table.rows, 1):
            for cell_index, cell in enumerate(row.cells, 1):
                value = cell.text.strip()
                if value:
                    index += 1
                    blocks.append(_block(f"block-{index}", "table_cell", value, metadata={"table": table_index, "row": row_index, "column": cell_index}))
    return blocks


def _pdf_blocks(stream: io.BytesIO):
    stream.seek(0)
    reader = PdfReader(stream)
    blocks, warnings, index = [], [], 0
    for page_number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if not text.strip():
            warnings.append(f"Page {page_number} contains no extractable text; OCR may be required.")
            continue
        for paragraph in re.split(r'\n\s*\n|(?<=\.)\n(?=[A-Z])', text):
            value = paragraph.strip()
            if value:
                index += 1
                blocks.append(_block(f"block-{index}", "paragraph", value, page=page_number))
    if not blocks:
        warnings.append("No extractable PDF text was found. This may be a scanned document; OCR is required before style review.")
    return blocks, warnings


def extract_document(file_input, filename: str = None):
    """Extract a document into typed blocks while retaining a stable analysis-to-block map."""
    if hasattr(file_input, 'filename') and not filename:
        filename = file_input.filename
    elif isinstance(file_input, str) and not filename:
        filename = os.path.basename(file_input)
    if not filename:
        raise ValueError("Filename or extension must be provided.")
    extension = os.path.splitext(filename)[1].lower()
    if isinstance(file_input, str):
        with open(file_input, 'rb') as handle:
            content = handle.read(MAX_DOCUMENT_BYTES + 1)
    else:
        if hasattr(file_input, 'seek'):
            file_input.seek(0)
        content = file_input.read(MAX_DOCUMENT_BYTES + 1)
        if isinstance(content, str):
            content = content.encode('utf-8')
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError('Document exceeds the 8 MB file limit.')
    stream = io.BytesIO(content)
    warnings = []
    if extension == '.docx':
        blocks = _docx_blocks(stream)
        pagination = False
        warnings.append("DOCX pagination is unavailable without rendering; locations use block IDs.")
    elif extension == '.pdf':
        blocks, warnings = _pdf_blocks(stream)
        pagination = True
    else:
        text = extract_text_from_file(io.BytesIO(content), filename)
        blocks = _classify_plain_blocks(text, extension)
        pagination = False
    original_parts, analysis_parts, offset_map = [], [], []
    cursor = 0
    for block_index, block in enumerate(blocks):
        if block_index:
            original_parts.append("\n\n")
            analysis_parts.append("\n\n")
            offset_map.extend([max(0, cursor - 1), max(0, cursor - 1)])
            cursor += 2
        block["start_offset"] = cursor
        original_parts.append(block["text"])
        normalized, local_map = normalize_with_offset_map(block["text"])
        analysis_parts.append(normalized)
        offset_map.extend(block["start_offset"] + value for value in local_map)
        cursor += len(block["text"])
        block["end_offset"] = cursor
    original_text = "".join(original_parts)
    analysis_text = "".join(analysis_parts)
    status = "empty_requires_ocr" if extension == '.pdf' and not blocks else "ok" if blocks else "empty"
    return {
        "filename": filename,
        "source_format": extension.lstrip('.'),
        "original_text": original_text,
        "analysis_text": analysis_text,
        "analysis_to_original_offsets": offset_map,
        "blocks": blocks,
        "extraction_status": status,
        "warnings": warnings,
        "pagination_available": pagination,
        "formatting_available": extension in {'.docx', '.md'},
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }


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
        with zipfile.ZipFile(stream) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(entry.file_size for entry in entries) > 32 * 1024 * 1024:
                raise ValueError("DOCX expanded content exceeds extraction limits.")
        stream.seek(0)
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
    - Transforms citation keys (\\cite{...}) into academic parentheticals
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
