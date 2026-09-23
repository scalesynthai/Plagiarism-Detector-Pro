"""Conservative section selection for writing diagnostics (not semantic grading)."""
import re

OPENING = re.compile(r'^\s*(?:#+\s*|\d+\.?\s*)?(abstract|introduction)\s*:?[ \t]*$', re.I | re.M)
NEXT = re.compile(r'^\s*(?:#+\s*|\d+\.?\s*)?(?:keywords|introduction|background|related work|modeling approach|methods?|methodology|results(?: and comparison)?|discussion|conclusion|references)\s*:?[ \t]*$', re.I | re.M)
PROSE = re.compile(r'\b(?:this (?:paper|study|work)|we (?:hypothesi[sz]e|argue|propose|evaluate|investigate)|the central (?:claim|hypothesis|question)|model selection is)\b', re.I)


def select_opening(text):
    heading = OPENING.search(text)
    if heading:
        start = heading.end()
        label = heading.group(1).lower()
    else:
        prose = PROSE.search(text)
        if prose:
            start, label = prose.start(), 'opening prose'
        else:
            # Skip short title/author/affiliation lines; retain the first prose paragraph.
            start, label = 0, 'first substantial paragraph'
            offset = 0
            found = False
            for paragraph in re.split(r'\n\s*\n', text):
                position = text.find(paragraph, offset)
                offset = position + len(paragraph)
                if len(paragraph.split()) >= 20 and re.search(r'[.!?]', paragraph):
                    start, found = position, True
                    break
            if not found:
                return '', 'not located', 0
    rest = text[start:]
    stop = NEXT.search(rest)
    if stop:
        rest = rest[:stop.start()]
    return rest.strip()[:5000], label, start


def front_matter(text):
    heading = OPENING.search(text)
    prose = PROSE.search(text)
    stops = [m.start() for m in (heading, prose) if m]
    return text[:min(stops) if stops else min(len(text), 1500)]
