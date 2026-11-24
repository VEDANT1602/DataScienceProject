"""Smoke-test source hashes, the paper's rounded table values and count denominators."""
from pathlib import Path
import json
from analyze import RAW, old_cpu, new_cpu, t4, sha

def main():
    expected={'cpu_results.json':'fb983199bed74bf9090a1b213689ebd3d858d4761941267707cc6663de6dc71c',
       'colab_benchmark.py':'907bd82939912bed27663f32a3ebb13e324fdfa2989f6793cef5ad719d333914',
       'test_attention_audit.py':'b08c214f98d658c7b5834ee0d3b9d2e873ea404655a55147a3323d660a0f3df6',
       't4-first.json':'3ea076e957c329e9b9867e1bd3f29ad8e9c72ef6ddf56b3f1280cd4506b8d014',
       't4-repeat.json':'8d3356d01deef331e6b633039a15dc29308dd6ed2d328991b4c6d1a2f812725d'}
    for name,digest in expected.items():assert sha(RAW/name)==digest,name
    _,summary=old_cpu()
    assert [(round(r['ratio_median'],3),r['ratio_gt_one'],round(r['paired_median'],3),r['paired_gt_one']) for r in summary]==[
        (4.505,48,4.485,48),(1.271,44,1.298,44),(.965,20,.973,23)]
    records=new_cpu()
    expected_pairs={(1,16):([1.016,1.211,1.079],25),(1,256):([1.770,1.971,1.932],36),
                    (4,16):([1.493,1.412,1.380],34),(4,256):([3.142,3.155,2.849],36)}
    for (b,p),(times,count) in expected_pairs.items():
        subset=[r for r in records if (r['batch'],r['prefix'])==(b,p)]
        assert [round(r['median_of_block_ratios'],3) for r in subset]==times
        assert sum(r['blocks_ratio_gt_one'] for r in subset)==count
    assert [round(r['ratio_of_medians'],3) for r in t4()]==[1.233,1.361]
    assert max(r['max_abs_error'] for r in records)==8.940696716308594e-08
    print('All three manuscript tables match saved trial records and five frozen input checksums.')
    print('CPU: 48 historical cases, 11 blocks x 4 methods; 12 new case-process cells, 12 blocks x 2 methods.')
    print('T4: 2 historical captures, 7 timings x 2 methods; 2.11 and 2.13 Torch environments.')

if __name__=='__main__':main()
