import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from app import create_app
from config import TestingConfig
from core.checker import PlagiarismChecker
from core.batch_processor import BatchProcessor
from core.report_generator import ReportGenerator


class HardeningTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name
        config = type('Config', (TestingConfig,), {'SOURCES_DIR': self.directory})
        self.app = create_app(config)
        self.client = self.app.test_client()
        self.headers = {'X-Admin-PIN': config.ADMIN_PIN}

    def test_security_headers_present(self):
        for path in ('/', '/sources', '/docs'):
            response = self.client.get(path)
            self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
            self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')
            self.assertIn("object-src 'none'", response.headers['Content-Security-Policy'])
        app_csp = self.client.get('/').headers['Content-Security-Policy']
        self.assertIn("script-src 'self'", app_csp)
        self.assertNotIn('unpkg.com', app_csp)
        self.assertNotIn('swagger-ui-dist@5/', self.client.get('/docs').get_data(as_text=True))

    def test_extraction_errors_do_not_leak_internals(self):
        response = self.client.post('/check', data={'file': (io.BytesIO(b'%PDF-1.4 garbage'), 'bad.pdf')},
                                    content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('pypdf', response.get_data(as_text=True).lower())

    def test_cleanup_apply_validates_accept(self):
        for accept in ('1', {'a': 1}, [[1]], [{}], [True], ['x']):
            response = self.client.post('/api/writing-cleanup/apply', json={'text': 'We delve into it.', 'accept': accept})
            self.assertEqual(response.status_code, 400, accept)
        ok = self.client.post('/api/writing-cleanup/apply', json={'text': 'We delve into it.', 'accept': [0]})
        self.assertEqual(ok.status_code, 200)

    def test_json_shapes_return_client_errors(self):
        endpoints = ['/check', '/api/cite', '/api/paraphrase', '/check/compare-drafts',
                     '/api/student-coach/evaluate-thesis', '/reports/html', '/reports/certificate']
        for endpoint in endpoints:
            for payload in [[], [1], 'text', 123, None]:
                with self.subTest(endpoint=endpoint, payload=payload):
                    response = self.client.post(endpoint, data=json.dumps(payload), content_type='application/json')
                    self.assertEqual(response.status_code, 400)
                    self.assertIn('error', response.get_json())
        for payload in [{'query': 12}, {'query': []}, {'query': 'text', 'include_web': 'false'}]:
            self.assertEqual(self.client.post('/check', json=payload).status_code, 400)
        response = self.client.post('/check', data='{', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.is_json)

    def test_report_input_validation(self):
        for payload in [{'data': []}, {'overall_similarity': 'bad'}, {'ai_analysis': None},
                        {'overall_similarity': float('nan')}, {'overall_similarity': -1}]:
            self.assertEqual(self.client.post('/reports/certificate', json=payload).status_code, 400)
        self.assertEqual(self.client.post('/reports/html', json={'highlighted_sentences': [1]}).status_code, 400)

    def test_report_escapes_html_and_rejects_script_links(self):
        attack = '<script>alert(1)</script>'
        report = ReportGenerator.generate_html_report({
            'highlighted_sentences': [{'text': attack, 'source': '\" onmouseover=\"alert(1)', 'is_plagiarized': True}],
            'sources_breakdown': [{'filename': attack, 'url': 'javascript:alert(1)'}],
        }, title=attack)
        self.assertNotIn(attack, report)
        self.assertNotIn('href="javascript:', report)
        self.assertIn('&lt;script&gt;', report)
        certificate = ReportGenerator.generate_student_certificate({}, attack, attack)
        self.assertNotIn(attack, certificate)
        self.assertNotIn('VERIFIED ORIGINAL & HUMAN-AUTHORED', certificate)

    def test_corpus_mutations_require_configured_header_secret(self):
        response = self.client.post('/sources/upload', data={'file': (io.BytesIO(b'text'), 'test.txt')})
        self.assertEqual(response.status_code, 403)
        self.app.config['ADMIN_PIN'] = ''
        response = self.client.delete('/sources/test.txt', headers={'X-Admin-PIN': '1234'})
        self.assertEqual(response.status_code, 403)

    def test_upload_validation_and_no_overwrites(self):
        for filename, data in [('bad.pdf', b'not a PDF'), ('empty.txt', b'   ')]:
            response = self.client.post('/sources/upload', headers=self.headers, data={'file': (io.BytesIO(data), filename)})
            self.assertEqual(response.status_code, 400)
            self.assertFalse((Path(self.directory) / filename).exists())
        self.app.checker.add_source('keep.txt', 'original content')
        with self.assertRaises(FileExistsError):
            self.app.checker.add_source('keep.txt', 'replacement')
        self.assertEqual((Path(self.directory) / 'keep.txt').read_text(), 'original content')
        with self.assertRaises(ValueError):
            self.app.checker.add_source('../outside.txt', 'content')
        with self.assertRaises(ValueError):
            self.app.checker.delete_source('../outside.txt')

    def test_other_worker_refreshes_after_add_and_delete(self):
        second = PlagiarismChecker(self.directory)
        self.app.checker.add_source('paper.txt', 'An original reference document with enough words.')
        self.assertEqual([s['filename'] for s in second.list_sources()], ['paper.txt'])
        self.app.checker.delete_source('paper.txt')
        self.assertEqual(second.list_sources(), [])
        self.assertEqual(second.vector_engine.index, {})

    def test_zip_limits_and_corruption_return_client_errors(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('large.txt', b'a' * 1024)
        stream.seek(0)
        with patch.object(BatchProcessor, 'MAX_FILE_BYTES', 100):
            response = self.client.post('/check/batch', data={'file': (stream, 'test.zip')})
            self.assertEqual(response.status_code, 400)
        response = self.client.post('/check/batch', data={'file': (io.BytesIO(b'corrupt'), 'test.zip')})
        self.assertEqual(response.status_code, 400)
        with self.assertRaises(ValueError):
            self.app.batch_processor.process_multiple_files([('x.txt', io.BytesIO(b'x'))] * 101)

    def test_sensitive_responses_not_cached_and_errors_do_not_leak(self):
        with patch.object(self.app.checker, 'analyze', side_effect=RuntimeError('/secret/internal/path')):
            response = self.client.post('/check', json={'query': 'valid text', 'include_web': False})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('/secret/internal/path', response.get_data(as_text=True))
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_analysis_limits_are_client_errors(self):
        for query in ['x' * 100001, 'word ' * 501]:
            response = self.client.post('/check', json={'query': query, 'include_web': False})
            self.assertEqual(response.status_code, 400)
        response = self.client.post('/check', data={'file': (io.BytesIO(b'word ' * 501), 'long.txt')})
        self.assertEqual(response.status_code, 400)

    def test_docx_decompression_limit(self):
        from core.extractor import extract_text_from_file
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('word/document.xml', b'a' * (32 * 1024 * 1024 + 1))
        stream.seek(0)
        with self.assertRaisesRegex(ValueError, 'expanded content'):
            extract_text_from_file(stream, 'bomb.docx')

    def test_citation_outage_is_explicit(self):
        from core.citation_generator import CitationGenerator
        with patch('core.citation_generator.requests.get', side_effect=OSError('offline')):
            result = CitationGenerator.generate_from_identifier('10.1234/example')
        self.assertFalse(result['metadata_resolved'])
        self.assertIn('Unverified', result['warning'])
        self.assertEqual(result['year'], 'n.d.')

    def test_missing_corpus_directory_is_empty(self):
        checker = PlagiarismChecker(str(Path(self.directory) / 'missing'))
        self.assertEqual(checker.list_sources(), [])


class CitationHostTests(unittest.TestCase):
    def test_source_type_uses_hostname_not_substring(self):
        gen = PlagiarismChecker.generate_smart_citations
        self.assertIn("arXiv", gen("p.txt", "https://arxiv.org/abs/1")["apa"])
        self.assertIn("Wikipedia", gen("p.txt", "https://en.wikipedia.org/wiki/X")["apa"])
        for url in ("https://evil.com/?q=wikipedia.org", "https://wikipedia.org.evil.com/x",
                    "https://evilarxiv.org/x", "not a url arxiv.org"):
            apa = gen("p.txt", url)["apa"]
            self.assertNotIn("Wikipedia", apa)
            self.assertNotIn("arXiv", apa)


class RegexPerformanceTests(unittest.TestCase):
    def test_heading_regexes_are_linear_on_whitespace_heavy_input(self):
        import time
        from core.sections import select_opening, front_matter
        from core.matching import BIB_HEADER
        for text in ("\n" * 100000, " \n" * 50000, "a" + "\n \n" * 33000, ("   \n" * 25000) + "zz",
                     "abstract" + " " * 100000 + "x", "abstract" + "\t" * 100000 + "x",
                     "references" + " " * 100000 + "x", "abstract:" + " " * 100000 + "x"):
            started = time.monotonic()
            select_opening(text)
            front_matter(text)
            BIB_HEADER.search(text)
            self.assertLess(time.monotonic() - started, 2.0)


class ErrorAndBlockTests(unittest.TestCase):
    def test_plain_blocks_linear_and_equivalent(self):
        import time
        from core.style_review import WritingStyleReviewer
        text = "First para line one.\nstill first.  \n\n  > quoted\n\nReferences\nA. B.\n"
        blocks = WritingStyleReviewer._plain_blocks(text)
        self.assertEqual([b["text"] for b in blocks],
                         ["First para line one.\nstill first.", "> quoted", "References\nA. B."])
        self.assertEqual([b["type"] for b in blocks], ["paragraph", "quotation", "reference"])
        for b in blocks:
            self.assertEqual(text[b["start_offset"]:b["end_offset"]], b["text"])
        for big in ("a " * 50000, "word\n" * 20000, "a\n \n" * 20000):
            started = time.monotonic()
            WritingStyleReviewer._plain_blocks(big)
            self.assertLess(time.monotonic() - started, 2.0)

    def test_corrupt_documents_do_not_leak_library_errors(self):
        from core.extractor import extract_text_from_file
        for name in ("x.pdf", "x.docx"):
            with self.assertRaises(ValueError) as ctx:
                extract_text_from_file(io.BytesIO(b"garbage"), name)
            self.assertNotIn("pypdf", str(ctx.exception).lower())
            self.assertNotIn("zip", str(ctx.exception).lower().replace("unsupported", ""))

    def test_duplicate_upload_does_not_leak_paths(self):
        app = create_app(type('C', (TestingConfig,), {'SOURCES_DIR': tempfile.mkdtemp()}))
        client = app.test_client()
        headers = {'X-Admin-PIN': TestingConfig.ADMIN_PIN}
        for _ in range(2):
            response = client.post('/sources/upload', headers=headers,
                                   data={'file': (io.BytesIO(b'Some reference text about science.'), 'dup.txt')},
                                   content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('/', response.get_json()['error'].replace('.', ''))
