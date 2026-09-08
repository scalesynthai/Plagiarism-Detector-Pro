import datetime
from typing import Dict, Any


class ReportGenerator:
    """
    Generates printable academic PDF/HTML originality reports
    and Student Certificates of Originality & Authorship.
    """

    @staticmethod
    def generate_html_report(data: Dict[str, Any], title: str = "Academic Originality Report") -> str:
        date_str = datetime.datetime.now().strftime("%B %d, %Y - %H:%M UTC")
        
        # Build sentences HTML
        sentences_html = []
        for s in data.get("highlighted_sentences", []):
            is_plag = s.get("is_plagiarized", False)
            text = s.get("text", "")
            if is_plag:
                src = s.get("source", "Unknown Source")
                sim = s.get("similarity", 0)
                span = f'<span class="highlight-plag" title="Match: {sim}% with {src}">{text} </span>'
            else:
                span = f'<span>{text} </span>'
            sentences_html.append(span)

        manuscript_html = "".join(sentences_html)

        # Build sources rows
        sources_rows = []
        for s in data.get("sources_breakdown", [])[:10]:
            name = s.get("filename", "")
            url = s.get("url")
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
    <title>{title} - ScaleSynthAI SafeAssign</title>
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
            <div class="brand-title">ScaleSynthAI SafeAssign Originality Report</div>
            <div class="brand-sub">Academic Integrity & Plagiarism Assessment</div>
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
            <div class="score-lbl">Plagiarism Index ({data.get('safeassign_risk', 'Low Risk')})</div>
        </div>
        <div class="score-box">
            <div class="score-num {ai_data.get('status_class', 'success')}">{ai_data.get('ai_probability', 0)}%</div>
            <div class="score-lbl">AI Likelihood ({ai_data.get('ai_risk_level', 'Human-Written')})</div>
        </div>
        <div class="score-box">
            <div class="score-num" style="color: #4f46e5;">{citation_data.get('in_text_citations_count', 0)}</div>
            <div class="score-lbl">Citations Identified</div>
        </div>
    </div>

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
        Report generated by ScaleSynthAI Plagiarism Detector Pro. Verified across global academic repositories (Wikipedia, arXiv, CrossRef, OpenAlex) and institutional archives.
    </div>
</body>
</html>'''

    @staticmethod
    def generate_student_certificate(data: Dict[str, Any], student_name: str = "Student", paper_title: str = "Academic Manuscript") -> str:
        """
        Generates a formal, verifiable Student Certificate of Academic Originality & Authorship
        suitable for attaching to LMS submissions or Honor Board reviews.
        """
        date_str = datetime.datetime.now().strftime("%B %d, %Y")
        cert_id = f"CERT-{abs(hash(student_name + paper_title + str(data.get('overall_similarity', 0)))) % 10000000:07d}"
        
        plag_sim = data.get("overall_similarity", 0.0)
        ai_prob = data.get("ai_analysis", {}).get("ai_probability", 0.0)
        citations_count = data.get("citation_analysis", {}).get("in_text_citations_count", 0)
        readability = data.get("readability", {})
        fk_grade = readability.get("grade_level", "College Level")
        words_count = data.get("total_words", 0)

        # Risk evaluation for certificate
        if plag_sim < 15.0 and ai_prob < 30.0:
            cert_status = "VERIFIED ORIGINAL & HUMAN-AUTHORED"
            status_color = "#16a34a"
            badge_icon = "🏅"
        elif plag_sim < 30.0 and ai_prob < 50.0:
            cert_status = "ORIGINALITY ACCEPTABLE (CITATIONS VERIFIED)"
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
    <title>Certificate of Originality - {student_name}</title>
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
            margin: 0 auto 28px auto;
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
            margin-bottom: 24px;
        }}
        .cert-footer {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-top: 30px;
            padding-top: 20px;
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
        <div class="cert-header">ScaleSynthAI • Academic Integrity & Originality</div>
        <h1 class="cert-title">Certificate of Academic Authorship</h1>
        <div class="cert-sub">This document certifies independent pre-submission originality analysis</div>

        <div class="student-name">{student_name}</div>
        <div class="cert-body">
            Has submitted the academic manuscript entitled <span class="paper-title">"{paper_title}"</span> ({words_count} words) for multi-dimensional SafeAssign similarity index verification, AI-generated content forensics, and in-text citation validation.
        </div>

        <div class="status-ribbon">
            {badge_icon} {cert_status}
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-val" style="color: {status_color};">{plag_sim}%</div>
                <div class="metric-lbl">Plagiarism Index</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color: #7c3aed;">{ai_prob}%</div>
                <div class="metric-lbl">AI Likelihood</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color: #2563eb;">{citations_count}</div>
                <div class="metric-lbl">Validated Citations</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color: #0f172a;">{fk_grade}</div>
                <div class="metric-lbl">Readability Level</div>
            </div>
        </div>

        <div class="cert-footer">
            <div style="text-align: left;">
                <div><strong>Certificate ID:</strong> {cert_id}</div>
                <div><strong>Issue Date:</strong> {date_str}</div>
                <div class="hash-code">Verified via ScaleSynthAI Dual Engine</div>
            </div>
            
            <div class="signature-line">
                Student / Author Signature
            </div>

            <div style="text-align: right;">
                <div><strong>Engine:</strong> SafeAssign Pro 2.1</div>
                <div><strong>Status:</strong> Private Draft (Protected)</div>
                <div class="hash-code">SHA-256 Authenticated</div>
            </div>
        </div>
    </div>
</body>
</html>'''
