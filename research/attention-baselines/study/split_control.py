"""Paired CPU experiment with matched last-position Q and separate KV projections."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import random
import sys
import time
from datetime import datetime, timezone

import torch
from torch.nn import functional as F

from archived.colab_benchmark import AuditAttention, make_paths

WIDTH, HEADS, DECODE, SEED = 64, 4, 32, 42
NAMES = ("reproject", "reuse")

def clock():
    return datetime.now(timezone.utc).isoformat()

def matched_paths(model, x, prefix):
    batch, _, width = x.shape
    q_weight = model.qkv.weight[:width]
    kv_weight = model.qkv.weight[width:]

    def heads(t):
        return t.reshape(batch, t.shape[1], HEADS, width // HEADS).transpose(1, 2)

    def kv(t):
        k, v = F.linear(t, kv_weight).chunk(2, dim=-1)
        return heads(k), heads(v)

    def reproject():
        outputs = []
        for t in range(prefix, prefix + DECODE):
            q = heads(F.linear(x[:, t:t+1], q_weight))
            k, v = kv(x[:, :t+1])
            outputs.append(model.attention_output(q, k, v))
        return torch.cat(outputs, dim=1)

    def reuse():
        k, v = kv(x[:, :prefix])
        outputs = []
        for t in range(prefix, prefix + DECODE):
            current = x[:, t:t+1]
            q = heads(F.linear(current, q_weight))
            k1, v1 = kv(current)
            k = torch.cat((k, k1), dim=2)
            v = torch.cat((v, v1), dim=2)
            outputs.append(model.attention_output(q, k, v))
        return torch.cat(outputs, dim=1)

    return dict(zip(NAMES, (reproject, reuse)))

def run(session):
    affinity = None
    if hasattr(os, "sched_getaffinity"):
        affinity = min(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {affinity})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    rng = random.Random(20261124 + session)
    configs = list(itertools.product((1,4), (16,256)))
    rng.shuffle(configs)
    metadata = {"session":session, "start_utc":clock(), "platform":platform.platform(),
        "processor":platform.processor(), "machine":platform.machine(), "python":platform.python_version(),
        "torch":torch.__version__, "torch_threads":torch.get_num_threads(),
        "torch_interop_threads":torch.get_num_interop_threads(), "affinity_cpu":affinity,
        "cuda_available":torch.cuda.is_available(), "timing":"perf_counter_ns", "warmups":3,
        "blocks":12, "design_seed":20261124+session, "input_seed":SEED, "dtype":"float32",
        "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "model_source_sha256":hashlib.sha256((Path(__file__).parent/'archived/colab_benchmark.py').read_bytes()).hexdigest(),
        "torch_build":torch.__config__.show(), "cases":[]}
    cpu_info = Path('/proc/cpuinfo')
    if cpu_info.exists():
        metadata['cpu_model'] = next((l.split(':',1)[1].strip() for l in cpu_info.read_text().splitlines() if l.startswith('model name')), None)
    with torch.inference_mode():
        for batch,prefix in configs:
            torch.manual_seed(SEED)
            model = AuditAttention(WIDTH,HEADS).eval()
            x = torch.randn(batch,prefix+DECODE,WIDTH)
            paths = matched_paths(model,x,prefix)
            reference = make_paths(model,x,prefix,DECODE)['dense_all']()
            errors = {}
            for name,fn in paths.items():
                result = fn()
                if not torch.isfinite(result).all() or not torch.allclose(result,reference,rtol=1e-5,atol=1e-5):
                    raise ValueError(f'Output mismatch in {name}')
                errors[name] = (reference-result).abs().max().item()
            for _ in range(3):
                for name in rng.sample(list(paths),2): paths[name]()
            orders = [NAMES, NAMES[::-1]]*6
            rng.shuffle(orders)
            trials=[]
            for block,order in enumerate(orders):
                for position,name in enumerate(order):
                    start = time.perf_counter_ns()
                    paths[name]()
                    ns = time.perf_counter_ns()-start
                    trials.append({"block":block,"order":position,"method":name,"time_ns":ns})
            metadata['cases'].append({"batch":batch,"prefix":prefix,"decode":DECODE,
                                      "width":WIDTH,"heads":HEADS,"max_abs_error":errors,"trials":trials})
    metadata['end_utc'] = clock()
    return metadata

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=int,choices=(1,2,3),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():parser.error("Output exists; select a fresh output path.")
    result = run(args.session)
    with args.output.open('x') as out:json.dump(result,out,indent=2);out.write('\n')
