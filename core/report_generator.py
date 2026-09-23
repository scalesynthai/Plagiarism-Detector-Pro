import datetime
import hashlib
import html
import json
import math
from typing import Dict, Any


def _safe_data(value):
    """Escape report values without changing numeric values used for scoring."""
    if isinstance(value, str):
        return html.escape(value, quote=True)
    if isinstance(value, dict):
        return {key: _safe_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_data(item) for item in value]
    return value


def sentence_markup(sentence):
    text = sentence.get("text", "")
    if not isinstance(text, str):
        raise ValueError("Sentence text must be a string.")
    start = sentence.get("start", 0)
    ranges = []
    for span in sentence.get("matched_spans", []):
        a, b = max(0, span["start"]-start), min(len(text), span["end"]-start)
        if b > a:
            ranges.append((a, b))
    merged = []
    for a, b in sorted(ranges):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(b, merged[-1][1])
        else:
            merged.append([a, b])
    result, position = [], 0
    for a, b in merged:
        result.append(html.escape(text[position:a]))
        result.append('<span class="highlight-plag">' + html.escape(text[a:b]) + '</span>')
        position = b
    result.append(html.escape(text[position:]) + ' ')
    return ''.join(result)


def validate_report(data):
    if not isinstance(data, dict):
        raise ValueError("Report data must be an object.")
    for key in ("ai_analysis", "citation_analysis", "readability", "scoring"):
        if key in data and not isinstance(data[key], dict):
            raise ValueError(f"{key} must be an object.")
    for key in ("highlighted_sentences", "sources_breakdown"):
        if key in data and (not isinstance(data[key], list) or
                            any(not isinstance(item, dict) for item in data[key])):
            raise ValueError(f"{key} must be an array of objects.")
    for sentence in data.get("highlighted_sentences", []):
        if not isinstance(sentence.get("text", ""), str) or type(sentence.get("start", 0)) is not int:
            raise ValueError("Invalid sentence text or offset.")
        spans = sentence.get("matched_spans", [])
        if not isinstance(spans, list) or any(not isinstance(span, dict) or
                type(span.get("start")) is not int or type(span.get("end")) is not int
                for span in spans):
            raise ValueError("Invalid matched spans.")
    for value in (data.get("overall_similarity", 0), data.get("ai_analysis", {}).get("ai_probability", 0)):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("Scores must be finite numbers between 0 and 100.")


class ReportGenerator:
    """
    Generates printable similarity reports and advisory analysis summaries.
    """

    @staticmethod
    def generate_html_report(data: Dict[str, Any], title: str = "Academic Text Similarity Report") -> str:
        validate_report(data)
        manuscript_html = "".join(sentence_markup(row) for row in data.get("highlighted_sentences", []))
        data = _safe_data(data)
        date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
        
        title = html.escape(title, quote=True)
        # Build sources rows
        sources_rows = []
        for s in data.get("sources_breakdown", [])[:10]:
            name = s.get("filename", "")
            url = s.get("url")
            if not isinstance(url, str) or not url.lower().startswith(("https://", "http://")):
                url = None
            badge = s.get("badge", "Source")
            sim = s.get("similarity", 0)
            url_html = f'<a href="{url}" target="_blank">{name}</a>' if url else name
            sources_rows.append(f'''
                <tr>
                    <td>{url_html}</td>
                    <td><span class="badge">{badge}</span></td>
                    <td>{s.get("source_word_count", 0)} words</td>
                    <td><strong>{sim}%</strong></td>
                </tr>
            ''')

        sources_table_html = "".join(sources_rows)

        ai_data = data.get("ai_analysis", {})
        citation_data = data.get("citation_analysis", {})

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title} - ScaleSynthAI</title>
    <style>
        @page {{ size: A4; margin: 20mm; }}
        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #1e293b;
            line-height: 1.6;
            margin: 0;
            padding: 24px;
            background: #fff;
        }}
        .header {{
            border-bottom: 2px solid #0f172a;
            padding-bottom: 16px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .brand-title {{ font-size: 24px; font-weight: bold; color: #0f172a; }}
        .brand-sub {{ font-size: 13px; color: #64748b; }}
        .scores-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 28px;
        }}
        .score-box {{
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 16px;
            text-align: center;
            background: #f8fafc;
        }}
        .score-num {{ font-size: 32px; font-weight: 800; }}
        .score-num.danger {{ color: #dc2626; }}
        .score-num.warning {{ color: #d97706; }}
        .score-num.success {{ color: #16a34a; }}
        .score-lbl {{ font-size: 11px; text-transform: uppercase; font-weight: bold; color: #64748b; margin-top: 4px; }}
        
        .section-hdr {{ font-size: 16px; font-weight: bold; color: #0f172a; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; margin: 24px 0 12px 0; }}
        .manuscript {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; font-size: 14px; line-height: 1.8; text-align: justify; }}
        .highlight-plag {{ background: #fecaca; border-bottom: 2px solid #ef4444; color: #991b1b; padding: 2px 4px; border-radius: 3px; font-weight: 500; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
        th, td {{ border-bottom: 1px solid #e2e8f0; padding: 10px; text-align: left; }}
        th {{ background: #f1f5f9; color: #475569; font-weight: 600; font-size: 11px; text-transform: uppercase; }}
        .badge {{ display: inline-block; padding: 2px 6px; font-size: 10px; font-weight: bold; border-radius: 4px; background: #e2e8f0; color: #334155; }}
        .footer {{ margin-top: 40px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; }}
        @media print {{
            body {{ padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="brand-title">ScaleSynthAI Text Similarity Report</div>
            <div class="brand-sub">Lexical-overlap and writing-pattern screening</div>
        </div>
        <div style="text-align: right; font-size: 12px; color: #64748b;">
            <div><strong>Generated:</strong> {date_str}</div>
            <div><strong>Total Words:</strong> {data.get("total_words", 0)} words</div>
        </div>
    </div>

    <!-- Dual Metric Summary -->
    <div class="scores-grid">
        <div class="score-box">
            <div class="score-num {data.get('status_class', 'success')}">{data.get('overall_similarity', 0)}%</div>
            <div class="score-lbl">Selected Similarity ({data.get('safeassign_risk', 'Low Risk')})</div>
        </div>
        <div class="score-box">
            <div class="score-num {ai_data.get('status_class', 'success')}">{ai_data.get('ai_probability', 0)}%</div>
            <div class="score-lbl">AI-Pattern Heuristic (not authorship proof)</div>
        </div>
        <div class="score-box">
            <div class="score-num" style="color: #4f46e5;">{citation_data.get('in_text_citations_count', 0)}</div>
            <div class="score-lbl">Citations Identified</div>
        </div>
    </div>

    <p>Scored words: {data.get('scored_word_count', data.get('total_words', 0))}; matched words: {data.get('flagged_word_count', 0)}.
    All-text similarity: {data.get('raw_similarity', data.get('overall_similarity', 0))}%; body: {data.get('body_similarity', 0)}%;
    bibliography: {data.get('bibliography_similarity', 0)}%; quotations: {data.get('quotation_similarity', 0)}%.
    Exclude quotations: {data.get('scoring', {}).get('exclude_quotes', False)};
    exclude bibliography: {data.get('scoring', {}).get('exclude_bibliography', False)}.
    Citations remain included. Source percentages may overlap. Similarity is not proof of plagiarism.</p>
    <!-- Manuscript -->
    <div class="section-hdr">1. Color-Annotated Manuscript</div>
    <div class="manuscript">
        {manuscript_html}
    </div>

    <!-- Matched Sources Appendix -->
    <div class="section-hdr">2. Matched Database & Internet Sources</div>
    <table>
        <thead>
            <tr>
                <th>Reference Publication / Source</th>
                <th>Database</th>
                <th>Word Count</th>
                <th>Similarity</th>
            </tr>
        </thead>
        <tbody>
            {sources_table_html}
        </tbody>
    </table>

    <div class="footer">
        <div>Generated after comparing {data.get('total_corpus_searched', len(data.get('sources_breakdown', [])))} retrieved or configured sources. Sources not retrieved were not assessed.</div>
        <div style="margin-top: 6px; font-size: 10px; color: #94a3b8;"><strong>Academic Advisory Disclaimer:</strong> This report measures lexical overlap in the compared sources. It does not prove plagiarism, originality, AI authorship, or institutional compliance.</div>
    </div>
</body>
</html>'''

    @staticmethod
    def generate_student_certificate(data: Dict[str, Any], student_name: str = "Student", paper_title: str = "Academic Manuscript") -> str:
        """Generate an advisory, unsigned summary of supplied analysis results."""
        validate_report(data)
        data = _safe_data(data)
        date_str = datetime.datetime.now().strftime("%B %d, %Y")
        digest_input = json.dumps({"student_name": student_name, "paper_title": paper_title,
                                   "analysis": data}, sort_keys=True, ensure_ascii=False, default=str)
        cert_id = "ANALYSIS-" + hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:12].upper()
        
        student_name = html.escape(student_name, quote=True)
        paper_title = html.escape(paper_title, quote=True)
        plag_sim = data.get("overall_similarity", 0.0)
        ai_prob = data.get("ai_analysis", {}).get("ai_probability", 0.0)
        citations_count = data.get("citation_analysis", {}).get("in_text_citations_count", 0)
        readability = data.get("readability", {})
        fk_grade = readability.get("grade_level", "College Level")
        words_count = data.get("total_words", 0)

        # Risk evaluation for certificate
        if plag_sim < 15.0 and ai_prob < 30.0:
            cert_status = "LOW HEURISTIC SCORES — AUTHORSHIP NOT VERIFIED"
            status_color = "#16a34a"
            badge_icon = "🏅"
        elif plag_sim < 30.0 and ai_prob < 50.0:
            cert_status = "REVIEW ATTRIBUTION AND ORIGINALITY"
            status_color = "#2563eb"
            badge_icon = "📘"
        else:
            cert_status = "ORIGINALITY REVIEW RECOMMENDED"
            status_color = "#d97706"
            badge_icon = "⚠️"

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Advisory Analysis Summary - {student_name}</title>
    <style>
        @page {{ size: landscape A4; margin: 10mm; }}
        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            color: #0f172a;
            margin: 0;
            padding: 30px;
            background: #fff;
            box-sizing: border-box;
        }}
        .cert-border {{
            border: 8px double #1e3a8a;
            padding: 30px 40px;
            text-align: center;
            position: relative;
            background: radial-gradient(circle at center, #ffffff 0%, #f8fafc 100%);
            border-radius: 6px;
        }}
        .cert-header {{
            font-size: 13px;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: #64748b;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .cert-title {{
            font-size: 32px;
            font-weight: bold;
            color: #1e3a8a;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin: 0 0 10px 0;
        }}
        .cert-sub {{
            font-size: 16px;
            color: #475569;
            font-style: italic;
            margin-bottom: 24px;
        }}
        .student-name {{
            font-size: 30px;
            font-weight: bold;
            color: #0f172a;
            border-bottom: 2px solid #cbd5e1;
            display: inline-block;
            padding: 0 40px 6px 40px;
            margin-bottom: 12px;
        }}
        .cert-body {{
            font-size: 15px;
            line-height: 1.6;
            color: #334155;
            max-width: 800px;
            margin: 0 auto 24px auto;
        }}
        .paper-title {{
            font-weight: bold;
            color: #1e3a8a;
            font-style: italic;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            max-width: 800px;
            margin: 0 auto 24px auto;
            font-family: 'Helvetica Neue', Arial, sans-serif;
        }}
        .metric-card {{
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
            background: #ffffff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        }}
        .metric-val {{
            font-size: 20px;
            font-weight: 800;
            color: #0f172a;
        }}
        .metric-lbl {{
            font-size: 10px;
            text-transform: uppercase;
            font-weight: bold;
            color: #64748b;
            margin-top: 4px;
        }}
        .status-ribbon {{
            display: inline-block;
            padding: 6px 20px;
            background: {status_color};
            color: #ffffff;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-weight: 800;
            font-size: 13px;
            letter-spacing: 1px;
            border-radius: 20px;
            margin-bottom: 20px;
        }}
        .cert-disclaimer {{
            max-width: 800px;
            margin: 0 auto 20px auto;
            padding: 8px 12px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 11px;
            color: #64748b;
            line-height: 1.4;
        }}
        .cert-footer {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-top: 20px;
            padding-top: 16px;
            border-top: 1px solid #e2e8f0;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 12px;
            color: #64748b;
        }}
        .signature-line {{
            border-top: 1px solid #94a3b8;
            width: 220px;
            padding-top: 4px;
            font-weight: 600;
            color: #334155;
            text-align: center;
        }}
        .hash-code {{
            font-family: monospace;
            font-size: 10px;
            color: #94a3b8;
        }}
        @media print {{
            body {{ padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="cert-border">
        <div class="cert-header">ScaleSynthAI • Advisory Text Analysis</div>
        <h1 class="cert-title">Pre-Submission Analysis Summary</h1>
        <div class="cert-sub">Unsigned summary of automated lexical and writing-pattern diagnostics</div>

        <div class="student-name">{student_name}</div>
        <div class="cert-body">
            Requested analysis of <span class="paper-title">"{paper_title}"</span> ({words_count} words). The results below describe configured heuristics and detected citation syntax; they do not verify authorship or academic integrity.
        </div>

        <div class="status-ribbon">
            {badge_icon} {cert_status}
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-val" style="color: {status_color};">{plag_sim}%</div>
                <div class="metric-lbl">Selected Similarity</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color: #7c3aed;">{ai_prob}%</div>
                <div class="metric-lbl">AI-Pattern Heuristic</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color: #2563eb;">{citations_count}</div>
                <div class="metric-lbl">Citations Detected</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color: #0f172a;">{fk_grade}</div>
                <div class="metric-lbl">Readability Level</div>
            </div>
        </div>

        <div class="cert-disclaimer">
            <strong>Advisory only:</strong> This unsigned summary does not certify originality, authorship, citation validity, conference readiness, or institutional compliance. Review the matched passages and source coverage manually.
        </div>

        <div class="cert-footer">
            <div style="text-align: left;">
                <div><strong>Analysis ID:</strong> {cert_id}</div>
                <div><strong>Issue Date:</strong> {date_str}</div>
                <div class="hash-code">Generated by ScaleSynthAI diagnostics</div>
            </div>
            
            <div class="signature-line">
                Student / Author Signature
            </div>

            <div style="text-align: right;">
                <div><strong>Method:</strong> Lexical overlap + advisory heuristics</div>
                <div><strong>Corpus storage:</strong> Not added by this scanner</div>
                <div class="hash-code">SHA-256 analysis reference prefix</div>
            </div>
        </div>
    </div>
</body>
</html>'''
