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
