"""Validate saved timing blocks and reconstruct the report's three timing tables."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from math import isclose, isfinite
from pathlib import Path
from statistics import median
from itertools import product

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'archived'
FOUR = ('dense_all', 'last_query_recompute', 'cached_cat', 'cached_preallocated')
TWO = ('reproject', 'reuse')
CONTRASTS = ((FOUR[0],FOUR[2]), (FOUR[1],FOUR[2]), (FOUR[2],FOUR[3]))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def blocks(rows, names, count, time_field, order_field):
    panel = {}
    orders = Counter()
    assert len(rows) == len(names)*count
    for i in range(count):
        subset = sorted((r for r in rows if r['block']==i), key=lambda r:r[order_field])
        assert [r[order_field] for r in subset] == list(range(len(names)))
        order = tuple(r['method'] for r in subset)
        assert sorted(order) == sorted(names)
        orders[order] += 1
        times = {r['method']:r[time_field] for r in subset}
        assert all(isfinite(t) and t>0 for t in times.values())
        panel[i] = times
    return panel,orders

def old_cpu():
    d=json.loads((RAW/'cpu_results.json').read_text())
    assert sha(RAW/'cpu_results.json')=='fb983199bed74bf9090a1b213689ebd3d858d4761941267707cc6663de6dc71c'
    assert d['benchmark_script_sha256']==sha(RAW/'colab_benchmark.py')
    assert set(d['methods'])==set(FOUR) and d['repeats']==11 and d['warmup_per_method']==3
    expected=set(product((1,4),(16,64,128,256),(8,32),(7,42,101)))
    keys=set()
    output=[]
    for c in d['cases']:
        config=tuple(c[k] for k in ('batch','prefix','decode','seed'))
        assert config not in keys
        keys.add(config)
        panel,_=blocks(c['raw_trials'], FOUR, 11,'ms','order_in_block')
        checks=c['correctness']
        assert checks['future_perturbation_first_output_unchanged']
        assert all(checks['paths'][m]['allclose'] and checks['paths'][m]['finite'] for m in FOUR)
        for a,b in CONTRASTS:
            ratios=[r[a]/r[b] for r in panel.values()]
            ma=median(r[a] for r in panel.values());mb=median(r[b] for r in panel.values())
            output.append(dict(zip(('batch','prefix','decode','seed'),config))|
              {'numerator':a,'denominator':b,'numerator_median_ms':ma,'denominator_median_ms':mb,
               'ratio_of_medians':ma/mb,'median_of_block_ratios':median(ratios),
               'blocks_ratio_gt_one':sum(x>1 for x in ratios),'blocks':11})
    assert keys==expected
    summary=[]
    for a,b in CONTRASTS:
        sub=[r for r in output if (r['numerator'],r['denominator'])==(a,b)]
        m=[r['ratio_of_medians'] for r in sub];paired=[r['median_of_block_ratios'] for r in sub]
        summary.append({'numerator':a,'denominator':b,'ratio_median':median(m),'ratio_min':min(m),
                       'ratio_max':max(m),'ratio_gt_one':sum(x>1 for x in m),
                       'paired_median':median(paired),'paired_gt_one':sum(x>1 for x in paired)})
    return output,summary

def new_cpu():
    output=[]
    for s in (1,2,3):
        path=ROOT/'outputs'/f'split-session-{s}.json'
        doc=json.loads(path.read_text())
        assert doc['session']==s and doc['script_sha256']==sha(ROOT/'split_control.py')
        assert doc['model_source_sha256']==sha(RAW/'colab_benchmark.py')
        assert doc['torch_threads']==doc['torch_interop_threads']==1
        assert set((c['batch'],c['prefix']) for c in doc['cases'])==set(product((1,4),(16,256)))
        assert len(doc['cases'])==4
        for c in doc['cases']:
            assert c['decode']==32 and c['heads']==4 and c['width']==64
            panel,orders=blocks(c['trials'],TWO,12,'time_ns','order')
            assert orders==Counter({TWO:6,TWO[::-1]:6})
            assert max(c['max_abs_error'].values())<1e-5
            ratios=[r['reproject']/r['reuse'] for r in panel.values()]
            output.append({'session':s,'batch':c['batch'],'prefix':c['prefix'],
              'reproject_median_ms':median(r['reproject'] for r in panel.values())/1e6,
              'reuse_median_ms':median(r['reuse'] for r in panel.values())/1e6,
              'median_of_block_ratios':median(ratios),'blocks_ratio_gt_one':sum(v>1 for v in ratios),
              'blocks':12,'max_abs_error':max(c['max_abs_error'].values())})
    return sorted(output,key=lambda r:(r['batch'],r['prefix'],r['session']))

def t4():
    result=[]
    for p in (RAW/'t4-first.json',RAW/'t4-repeat.json'):
        d=json.loads(p.read_text())
        assert d['correctness']['allclose'] and d['status']=='executed' and d['device']=='cuda'
        a=d['full_recompute_ms'];b=d['kv_cached_ms']
        assert len(a)==len(b)==7 and all(x>0 for x in a+b)
        ratio=median(a)/median(b)
        assert isclose(ratio,d['median_ratio_full_to_cached'],abs_tol=1e-12)
        result.append({'capture':p.stem,'torch':d['torch'],'full_median_ms':median(a),
          'reuse_median_ms':median(b),'ratio_of_medians':ratio,'max_abs_error':d['correctness']['max_absolute_error'],
          'combined_peak_bytes':d['cuda_peak_allocated_bytes_combined_measurement']})
    return result

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output-dir',required=True,type=Path)
    out=cli.parse_args().output_dir
    out.mkdir(parents=True,exist_ok=True)
    archive,stats=old_cpu()
    for name,rows in (('historical-cases',archive),('historical-summary',stats),('matched-cpu',new_cpu()),('t4-summary',t4())):
        with (out/(name+'.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    print('Verified 2,112 archived CPU timings, 288 matched-control timings and 28 T4 timings.')

if __name__=='__main__':
    main()
