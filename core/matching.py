"""Deterministic exact-passage coverage; scores describe overlap, not authorship."""
import re
from collections import defaultdict

TOKEN = re.compile(r'\w+', re.UNICODE)
MIN_MATCH_WORDS = 4
COMMON = set('a an the and or but if then of in on at to for from by with as is are was were be been this that these those it its we our they their'.split())
BIB_HEADER = re.compile(r'^\s*(?:#+\s*|\d+\.\s*)?(?:references|bibliography|works cited|reference list)\s*:?[ \t]*$', re.I | re.M)
QUOTE = re.compile(r'"[^"\n]+"|“[^”]+”|«[^»]+»')


def tokens(text):
    return [(m.group().lower(), m.start(), m.end()) for m in TOKEN.finditer(text)]


def sentence_ranges(text):
    start = 0
    for match in re.finditer(r'(?<=[.!?])\s+|\n\s*\n', text):
        # Keep author-year citations intact across "et al.".
        if text[max(start, match.start()-6):match.start()].lower().endswith('et al.'):
            continue
        end = match.start()
        if text[start:end].strip():
            yield start, end
        start = match.end()
    if text[start:].strip():
        yield start, len(text)


def match_document(text, sources, exclude_quotes=False, exclude_bibliography=False):
    """Match 4-word seeds across full documents; merge token coverage, never whole sentences.

    Source percentages can overlap. Overall coverage counts each query token once.
    Offsets are Python character offsets into the normalized text passed here.
    """
    query = tokens(text)
    words = [t[0] for t in query]
    n = len(words)
    index = defaultdict(list)
    # Index only seeds present in the query, bounding postings to relevant material.
    wanted = {tuple(words[i:i+MIN_MATCH_WORDS]) for i in range(n-MIN_MATCH_WORDS+1)
              if sum(w not in COMMON for w in words[i:i+MIN_MATCH_WORDS]) >= 2}
    source_tokens_by_key = {}
    for key, source in sources.items():
        source_tokens = tokens(source['text'])
        source_tokens_by_key[key] = source_tokens
        source_words = [t[0] for t in source_tokens]
        for j in range(len(source_words)-MIN_MATCH_WORDS+1):
            seed = tuple(source_words[j:j+MIN_MATCH_WORDS])
            if seed in wanted:
                index[seed].append((key, j))

    quotes = [(m.start(), m.end()) for m in QUOTE.finditer(text)]
    header = BIB_HEADER.search(text)
    bib_start = header.start() if header else len(text)
    quote_ids = {i for i, (_, start, end) in enumerate(query)
                 if any(start >= a and end <= b for a, b in quotes)}
    bib_ids = {i for i, (_, start, _) in enumerate(query) if start >= bib_start}
    excluded = (quote_ids if exclude_quotes else set()) | (bib_ids if exclude_bibliography else set())
    eligible = set(range(n)) - excluded
    raw_by_source = defaultdict(set)
    # Store each seed's source position. Consecutive hits coalesce below into passages.
    evidence = defaultdict(dict)
    for i in range(n-MIN_MATCH_WORDS+1):
        best_by_source = {}
        for key, j in index.get(tuple(words[i:i+MIN_MATCH_WORDS]), []):
            st = source_tokens_by_key[key]
            left, source_left = i, j
            right, source_right = i+MIN_MATCH_WORDS, j+MIN_MATCH_WORDS
            while left > 0 and source_left > 0 and words[left-1] == st[source_left-1][0]:
                left -= 1
                source_left -= 1
            while right < n and source_right < len(st) and words[right] == st[source_right][0]:
                right += 1
                source_right += 1
            candidate = (right-left, left, right, source_left)
            if candidate[0] > best_by_source.get(key, (0,))[0]:
                best_by_source[key] = candidate
        for key, (_, left, right, source_left) in best_by_source.items():
            for k in range(left, right):
                raw_by_source[key].add(k)
                evidence[key].setdefault(k, source_left+k-left)
    raw = set().union(*raw_by_source.values()) if raw_by_source else set()
    matched = raw & eligible
    per_source = {key: ids & eligible for key, ids in raw_by_source.items()}
    pct = lambda ids, denominator: round(100 * len(ids) / len(denominator), 2) if denominator else 0.0
    all_ids = set(range(n))
    body_ids = all_ids - bib_ids

    passages = []
    for key in sorted(per_source):
        ids = sorted(per_source[key])
        runs = []
        for i in ids:
            source_i = evidence[key][i]
            if runs and i == runs[-1][-1] + 1 and source_i == evidence[key][runs[-1][-1]] + 1:
                runs[-1].append(i)
            else:
                runs.append([i])
        st = source_tokens_by_key[key]
        for run in runs:
            first, last = run[0], run[-1]
            a, b = query[first][1], query[last][2]
            sa, sb = st[evidence[key][first]][1], st[evidence[key][last]][2]
            passages.append({'start': a, 'end': b, 'token_start': first, 'token_end': last+1,
                             'word_count': len(run), 'text': text[a:b], 'source_key': key,
                             'source_name': sources[key]['filename'], 'source_start': sa,
                             'source_end': sb, 'matched_text': sources[key]['text'][sa:sb]})

    highlighted = []
    diff = []
    from core.citation_validator import CitationValidator
    validator = CitationValidator()
    for start, end in sentence_ranges(text):
        ids = {i for i, (_, a, b) in enumerate(query) if a >= start and b <= end}
        coverage = matched & ids
        candidates = [(len(ids & hits), key) for key, hits in per_source.items() if ids & hits]
        key = sorted(candidates, key=lambda item: (-item[0], item[1]))[0][1] if candidates else None
        source = sources.get(key, {})
        matching = [p for p in passages if p['start'] < end and p['end'] > start]
        best = next((p for p in matching if p['source_key'] == key), None)
        has_citation, citation = validator.has_in_text_citation(text[start:end])
        row = {'text': text[start:end], 'start': start, 'end': end,
               'is_plagiarized': bool(coverage), 'similarity': pct(coverage, ids & eligible),
               'matched_word_count': len(coverage), 'has_citation': has_citation,
               'citation': citation, 'is_quoted': bool(ids & quote_ids),
               'source': source.get('filename'), 'url': source.get('url'),
               'badge': source.get('badge'), 'matched_source_sentence': best['matched_text'] if best else None,
               'matched_spans': matching}
        highlighted.append(row)
        if coverage:
            diff.append({'student_sentence': row['text'], 'matched_sentence': row['matched_source_sentence'],
                         'source_name': row['source'], 'source_url': row['url'], 'badge': row['badge'],
                         'similarity': row['similarity'], 'is_quoted': row['is_quoted'],
                         'has_citation': has_citation, 'citation': citation, 'matched_spans': matching})
    breakdown = []
    for key, ids in per_source.items():
        if not ids:
            continue
        source = sources[key]
        breakdown.append({'filename': source['filename'], 'similarity': pct(ids, eligible),
                          'common_words_count': len(ids), 'source_word_count': len(source_tokens_by_key[key]),
                          'matched_sentences_count': sum(bool(ids & {i for i, (_, a, b) in enumerate(query)
                                                               if a >= row['start'] and b <= row['end']}) for row in highlighted),
                          'max_passage_similarity': 100.0, 'source_type': source.get('source_type', 'institutional'),
                          'badge': source.get('badge', 'Institutional'), 'url': source.get('url')})
    breakdown.sort(key=lambda row: (-row['similarity'], row['filename']))
    return {'overall_similarity': pct(matched, eligible), 'raw_similarity': pct(raw, all_ids),
            'body_similarity': pct(raw & body_ids, body_ids),
            'bibliography_similarity': pct(raw & bib_ids, bib_ids),
            'quotation_similarity': pct(raw & quote_ids, quote_ids),
            'total_words': n, 'scored_word_count': len(eligible), 'flagged_word_count': len(matched),
            'raw_matched_word_count': len(raw), 'excluded_word_count': len(excluded),
            'bibliography_word_count': len(bib_ids), 'quotation_word_count': len(quote_ids),
            'matched_spans': passages, 'highlighted_sentences': highlighted, 'diff_matches': diff,
            'sources_breakdown': breakdown, 'total_sentences': len(highlighted),
            'plagiarized_sentences_count': len(diff), 'quotes_count': len(quotes),
            'highest_matching_source': breakdown[0]['filename'] if breakdown else None,
            'highest_matching_url': breakdown[0]['url'] if breakdown else None,
            'highest_similarity': breakdown[0]['similarity'] if breakdown else 0.0,
            'scoring': {'method': 'exact-word-spans-v1', 'minimum_match_words': MIN_MATCH_WORDS,
                        'exclude_quotes': exclude_quotes, 'exclude_bibliography': exclude_bibliography,
                        'citations_excluded': False, 'source_percentages_overlap': True,
                        'offset_text': 'normalized_text', 'offset_unit': 'unicode_code_points',
                        'limitations': 'Measures lexical overlap in retrieved sources; semantic paraphrases may be missed.'},
            'normalized_text': text}
