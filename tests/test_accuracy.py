import unittest
from core.checker import PlagiarismChecker
from core.citation_validator import CitationValidator
from core.student_coach import AcademicStudentCoach
from core.phd_auditor import PhdResearchAuditor
from core.web_searcher import LiveWebSearcher
from core.report_generator import ReportGenerator
from benchmarks.run import evaluate, aggregate


def scan(text, sources, **options):
    checker = PlagiarismChecker()
    checker.sources = {str(i): {'filename': f'source_{i}.txt', 'text': source} for i,source in enumerate(sources)}
    return checker.analyze(text, include_web_sources=False, **options)


class MatchingAccuracyTests(unittest.TestCase):
    def test_partial_sentence_counts_only_shared_words(self):
        result = scan('Novel experiments confirm blue crystals absorb ultraviolet radiation while controls stay clear.',
                      ['Blue crystals absorb ultraviolet radiation.'])
        self.assertEqual(result['flagged_word_count'], 5)
        self.assertEqual(result['total_words'], 12)
        self.assertEqual(result['overall_similarity'], 41.67)
        self.assertEqual(result['matched_spans'][0]['text'], 'blue crystals absorb ultraviolet radiation')

    def test_duplicate_sources_and_overlaps_are_counted_once(self):
        result = scan('Blue crystals absorb ultraviolet radiation under cold conditions.',
                      ['Blue crystals absorb ultraviolet radiation.', 'Absorb ultraviolet radiation under cold conditions.'] * 2)
        self.assertEqual(result['flagged_word_count'], 8)
        self.assertEqual(result['overall_similarity'], 100)
        self.assertGreater(sum(s['similarity'] for s in result['sources_breakdown']), 100)

    def test_repeated_source_seed_uses_the_best_context(self):
        text = 'Novel blue crystals absorb ultraviolet radiation accurately.'
        source = ('Old blue crystals absorb ultraviolet radiation poorly. '
                  'Novel blue crystals absorb ultraviolet radiation accurately.')
        result = scan(text, [source])
        self.assertEqual(result['flagged_word_count'], 7)
        self.assertEqual(result['overall_similarity'], 100)
        self.assertEqual(result['matched_spans'][0]['text'], text.rstrip('.'))

    def test_citation_is_not_an_exemption(self):
        text = 'Blue crystals absorb ultraviolet radiation (Smith et al., 2024).'
        result = scan(text, ['Blue crystals absorb ultraviolet radiation.'], exclude_quotes=True)
        self.assertEqual(result['flagged_word_count'], 5)
        self.assertTrue(result['highlighted_sentences'][0]['has_citation'])
        self.assertEqual(result['total_sentences'], 1)

    def test_partial_quote_exclusion_preserves_other_matches(self):
        text = '"Blue crystals absorb ultraviolet radiation" whereas red minerals reflect infrared light.'
        result = scan(text, ['Blue crystals absorb ultraviolet radiation.', 'Red minerals reflect infrared light.'], exclude_quotes=True)
        self.assertEqual(result['flagged_word_count'], 5)
        self.assertEqual(result['excluded_word_count'], 5)
        self.assertEqual(result['scored_word_count'], 6)
        self.assertEqual(result['raw_matched_word_count'], 10)
        self.assertEqual(result['overall_similarity'], 83.33)

    def test_reference_exclusion_and_zero_denominator(self):
        text = 'Independent observations.\n\nReferences\nBlue crystals absorb ultraviolet radiation.'
        result = scan(text, ['Blue crystals absorb ultraviolet radiation.'], exclude_bibliography=True)
        self.assertEqual(result['scored_word_count'], 2)
        self.assertEqual(result['overall_similarity'], 0)
        self.assertGreater(result['bibliography_similarity'], 0)
        result = scan('"Blue crystals absorb ultraviolet radiation"', ['Blue crystals absorb ultraviolet radiation.'], exclude_quotes=True)
        self.assertEqual(result['scored_word_count'], 0)
        self.assertEqual(result['overall_similarity'], 0)

    def test_unicode_offsets_and_html_are_safe(self):
        text = '🧪 New: blue crystals absorb ultraviolet radiation <script>alert(1)</script>.'
        result = scan(text, ['Blue crystals absorb ultraviolet radiation.'])
        for span in result['matched_spans']:
            self.assertEqual(text[span['start']:span['end']],span['text'])
        report = ReportGenerator.generate_html_report(result)
        self.assertNotIn('<script>',report)

    def test_empty_and_stopword_only(self):
        for text in ['', 'the and of in to with']:
            result = scan(text, [text])
            self.assertEqual(result['flagged_word_count'], 0)
            self.assertIn('scoring', result)

    def test_lexical_engine_does_not_claim_synonym_detection(self):
        result = scan('Restored marshes diminish recurring inundation.', ['Wetland restoration reduces seasonal flooding.'])
        self.assertEqual(result['overall_similarity'], 0)
        self.assertIn('paraphrases',result['scoring']['limitations'])

    def test_even_search_sampling(self):
        text=' '.join(f'Experiment {i} measured a distinctive material response under controlled laboratory conditions.' for i in range(24))
        queries=LiveWebSearcher().extract_search_queries(text, max_queries=4)
        self.assertEqual(len(queries),4)
        self.assertIn('Experiment 0',queries[0])
        self.assertIn('Experiment 23',queries[-1])
        self.assertEqual(LiveWebSearcher().extract_search_queries(text,0),[])


class DiagnosticAccuracyTests(unittest.TestCase):
    def test_report_citations_are_recognized(self):
        text='Evidence (Barocas et al., 2023). Data (n = 442; Efron et al., 2004). Code (Pedregosa et al., 2011).'
        result=CitationValidator().validate_citations(text)
        self.assertEqual(result['in_text_citations_count'],3)
        self.assertEqual(result['unlinked_citations_count'],3)

    def test_citation_variants(self):
        validator=CitationValidator()
        for text in ['(Smith & Jones, 2020)', '(Smith et al., 2020, pp. 12–15)', '(Smith, 2020; Jones, 2021)', 'Smith et al. (2020)', '[1, 2–4]', '[1,2]']:
            with self.subTest(text=text):
                self.assertTrue(validator.has_in_text_citation(text)[0])
                validator.validate_citations(text)
        self.assertFalse(validator.has_in_text_citation('(n = 442)')[0])

    def test_coach_does_not_split_et_al_citation(self):
        self.assertEqual(AcademicStudentCoach.scan_unsupported_claims('Studies show that restored wetlands reduce flooding (Smith et al., 2024).'), [])

    def test_thesis_skips_cover_and_stops_before_methods(self):
        text='An Evaluation of Models\n\nJane Doe\n\nUniversity of Example\n\nIntroduction\n\nThis paper argues that evaluation requires subgroup analysis. Using a dataset, we compare models. The significance is practical.\n\nMethods\n\nDO NOT INCLUDE THIS SECTION.'
        result=AcademicStudentCoach.evaluate_thesis_abstract(text)
        self.assertEqual(result['score'],100)
        self.assertEqual(result['selection'],'introduction')
        self.assertNotIn('Jane Doe',result['evaluated_text'])
        self.assertNotIn('DO NOT INCLUDE',result['evaluated_text'])

    def test_thesis_without_heading_and_insufficient_input(self):
        result=AcademicStudentCoach.evaluate_thesis_abstract('Title\n\nAuthor\n\nThis paper argues for a new hypothesis using a dataset. Its significance is practical.')
        self.assertEqual(result['score'],100)
        self.assertEqual(AcademicStudentCoach.evaluate_thesis_abstract('Title only')['score'],0)

    def test_front_matter_anonymity_and_body_reference(self):
        result=PhdResearchAuditor.audit_manuscript('Title\n\nBy Jane Doe\nUniversity of Example\njane@example.org\n\nIntroduction\nThis paper evaluates a method.')
        self.assertFalse(result['is_anonymity_compliant'])
        self.assertGreaterEqual(result['anonymity_count'],3)
        clean=PhdResearchAuditor.audit_manuscript('Introduction\nThis paper compares published findings from the University of Example.')
        self.assertTrue(clean['is_anonymity_compliant'])
        self.assertNotIn('Verified',clean['readiness_verdict'])
        self.assertIsNone(PhdResearchAuditor.audit_manuscript('')['is_anonymity_compliant'])


class BenchmarkEvaluatorTests(unittest.TestCase):
    def test_metrics_account_for_missed_and_false_matches(self):
        case={'id':'hand-calculated','category':'test','text':'alpha beta gamma delta',
              'expected_positive_tokens':[0,1], 'expected_scored_tokens':[0,1,2,3],
              'expected_spans':[[0,10]],'expected_score':50}
        result={'matched_spans':[{'token_start':1,'token_end':3}], 'flagged_word_count':2,
                'scored_word_count':4,'overall_similarity':50}
        row=evaluate(case,result)
        self.assertEqual((row['tp'],row['fp'],row['fn'],row['tn']),(1,1,1,1))
        summary=aggregate([row])
        self.assertEqual(summary['token_f1'],.5)
        self.assertEqual(summary['score_mae_percentage_points'],0)
        # Equal percentages can hide completely different matches.
