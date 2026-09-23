"""Offline benchmark with fixed labels. Run from any directory; no provider calls."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.checker import PlagiarismChecker


def evaluate(case, result):
    expected = set(case['expected_positive_tokens'])
    eligible = set(case['expected_scored_tokens'])
    predicted = set()
    for span in result['matched_spans']:
        predicted.update(range(span['token_start'], span['token_end']))
    total = len(re.findall(r'\w+', case['text']))
    if not expected <= eligible or not eligible <= set(range(total)):
        raise ValueError(f"Invalid labels: {case['id']}")
    if not predicted <= eligible:
        raise ValueError(f"Matcher scored excluded/out-of-range tokens: {case['id']}")
    if result['flagged_word_count'] != len(predicted) or result['scored_word_count'] != len(eligible):
        raise ValueError(f"Score accounting mismatch: {case['id']}")
    expected_score = round(100 * len(expected) / len(eligible), 2) if eligible else 0
    if case['expected_score'] != expected_score:
        raise ValueError(f"Fixture score mismatch: {case['id']}")
    # Passage recall: at least half the labeled passage's eligible words recovered.
    ts = list(re.finditer(r'\w+', case['text']))
    passages = [{i for i,t in enumerate(ts) if t.start() >= a and t.end() <= b} & eligible
                for a,b in case['expected_spans']]
    passages = [p for p in passages if p]
    recovered = sum(len(p & predicted) / len(p) >= .5 for p in passages)
    return {'id':case['id'],'category':case['category'],'tp':len(expected & predicted),
            'fp':len(predicted - expected),'fn':len(expected - predicted),
            'tn':len(eligible - (expected | predicted)), 'expected_score':expected_score,
            'actual_score':result['overall_similarity'],
            'absolute_score_error':round(abs(result['overall_similarity'] - expected_score),2),
            'passages':len(passages),'passages_recovered':recovered}


def aggregate(rows):
    counts = {k:sum(r[k] for r in rows) for k in ('tp','fp','fn','tn','passages','passages_recovered')}
    tp, fp, fn, tn = [counts[k] for k in ('tp','fp','fn','tn')]
    ratio = lambda a,b: round(a/b,4) if b else None
    return {'cases':len(rows),**counts,'token_precision':ratio(tp,tp+fp),'token_recall':ratio(tp,tp+fn),
            'token_f1':ratio(2*tp,2*tp+fp+fn),'token_false_positive_rate':ratio(fp,fp+tn),
            'passage_recall_at_50_percent':ratio(counts['passages_recovered'],counts['passages']),
            'score_mae_percentage_points':round(sum(r['absolute_score_error'] for r in rows)/len(rows),2) if rows else None}


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    path=ROOT/'benchmarks/cases.json'
    raw=path.read_bytes(); dataset=json.loads(raw); cases=dataset['cases']
    results=[]
    for case in cases:
        checker=PlagiarismChecker()
        checker.sources={str(i):{'text':s['text'],'filename':s['filename']} for i,s in enumerate(case['sources'])}
        results.append(checker.analyze(case['text'],include_web_sources=False,**case['options']))
    node=json.loads(subprocess.run(['node',str(ROOT/'benchmarks/node_runner.js')],input=json.dumps(cases),
                                   text=True,capture_output=True,check=True,timeout=60).stdout)
    report={'dataset_sha256':hashlib.sha256(raw).hexdigest(),'scoring_method':'exact-word-spans-v1',
            'limitations':'Small synthetic English fixture set, not real-world accuracy or SafeAssign equivalence.', 'engines':{}}
    for name, predictions in [('python',results),('node',node)]:
        rows=[evaluate(case,result) for case,result in zip(cases,predictions)]
        report['engines'][name]={split:{'summary':aggregate([r for c,r in zip(cases,rows) if c['split']==split]),
                                     'cases':[r for c,r in zip(cases,rows) if c['split']==split]}
                                 for split in ('development','evaluation','challenge')}
    report['engine_parity']=all(a['overall_similarity']==b['overall_similarity'] and
                               {i for s in a['matched_spans'] for i in range(s['token_start'],s['token_end'])} ==
                               {i for s in b['matched_spans'] for i in range(s['token_start'],s['token_end'])}
                               for a,b in zip(results,node))
    if not report['engine_parity']:
        raise AssertionError('Python/Node scoring parity failed')
    rendered=json.dumps(report,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(rendered)
    for name, engine in report['engines'].items():
        for split, data in engine.items():
            print(name,split,json.dumps(data['summary']))
    print('Python/Node parity:',report['engine_parity'])

if __name__=='__main__':
    run()
