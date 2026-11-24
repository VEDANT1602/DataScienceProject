"""Four-path attention audit. No models, data downloads, or paid services.

Based on Vedant Thaker's inference-systems-lab/inference_lab/kv.py.
Original artifact revision: 5780a7c0661c4cf528957cff730de16e3fd447c4.
This is untrained single-layer tensor arithmetic, not an LLM/server benchmark.

GPU: python colab_benchmark.py --device cuda --output new_gpu_results.json
CPU: python colab_benchmark.py --device cpu --extended --output cpu_results.json
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import platform
import random
import shutil
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import torch

METHODS = ('dense_all', 'last_query_recompute', 'cached_cat', 'cached_preallocated')


class AuditAttention(torch.nn.Module):
    def __init__(self, width=64, heads=4):
        super().__init__()
        if width % heads:
            raise ValueError('width must be divisible by heads')
        self.width, self.heads, self.dim = width, heads, width // heads
        self.qkv = torch.nn.Linear(width, 3 * width, bias=False)
        self.out = torch.nn.Linear(width, width, bias=False)

    def projections(self, x):
        batch, length, _ = x.shape
        pieces = self.qkv(x).chunk(3, dim=-1)
        return tuple(t.reshape(batch, length, self.heads, self.dim).transpose(1, 2)
                     for t in pieces)

    def attention_output(self, q, k, v):
        joined = ((q @ k.transpose(-2, -1) / math.sqrt(self.dim)).softmax(-1) @ v)
        batch, _, length, _ = joined.shape
        return self.out(joined.transpose(1, 2).reshape(batch, length, self.width))

    def full(self, x):
        q, k, v = self.projections(x)
        scores = q @ k.transpose(-2, -1) / math.sqrt(self.dim)
        mask = torch.ones(x.shape[1], x.shape[1], dtype=torch.bool, device=x.device).triu(1)
        scores = scores.masked_fill(mask, float('-inf'))
        joined = (scores.softmax(-1) @ v).transpose(1, 2).reshape(x.shape)
        return self.out(joined)

    def last(self, x):
        # Control retains the original fused all-position QKV projection but
        # computes only the requested last query's attention/output projection.
        q, k, v = self.projections(x)
        return self.attention_output(q[:, :, -1:], k, v)

    def prefill(self, x):
        # Keep only K/V views alive, matching the original helper's lifetime.
        projected = self.projections(x)
        return projected[1], projected[2]


def make_paths(model, x, prefix, decode):
    def dense_all():
        return torch.cat([model.full(x[:, :prefix+i+1])[:, -1:]
                          for i in range(decode)], dim=1)

    def last_query_recompute():
        return torch.cat([model.last(x[:, :prefix+i+1])
                          for i in range(decode)], dim=1)

    def cached_cat():
        k, v = model.prefill(x[:, :prefix])
        values = []
        for i in range(decode):
            q, nk, nv = model.projections(x[:, prefix+i:prefix+i+1])
            k = torch.cat((k, nk), dim=2)
            v = torch.cat((v, nv), dim=2)
            values.append(model.attention_output(q, k, v))
        return torch.cat(values, dim=1)

    def cached_preallocated():
        # Allocation and projection-only prefix setup are included in timing.
        batch, total, _ = x.shape
        shape = (batch, model.heads, total, model.dim)
        k = torch.empty(shape, dtype=x.dtype, device=x.device)
        v = torch.empty_like(k)
        pk, pv = model.prefill(x[:, :prefix])
        k[:, :, :prefix].copy_(pk)
        v[:, :, :prefix].copy_(pv)
        del pk, pv
        values = []
        for i in range(decode):
            at = prefix + i
            q, nk, nv = model.projections(x[:, at:at+1])
            k[:, :, at:at+1].copy_(nk)
            v[:, :, at:at+1].copy_(nv)
            values.append(model.attention_output(q, k[:, :, :at+1], v[:, :, :at+1]))
        return torch.cat(values, dim=1)

    return dict(zip(METHODS, (dense_all, last_query_recompute, cached_cat, cached_preallocated)))


def inventory(device):
    result = {'python': platform.python_version(), 'platform': platform.platform(),
              'torch': torch.__version__, 'torch_cuda_build': torch.version.cuda,
              'cuda_available': torch.cuda.is_available(), 'logical_cpu_count': os.cpu_count(),
              'processor': platform.processor(), 'torch_threads': torch.get_num_threads(),
              'device': device, 'cuda_device_count': torch.cuda.device_count()}
    if device == 'cuda':
        properties = torch.cuda.get_device_properties(0)
        result.update(device_name=properties.name, total_device_memory_bytes=properties.total_memory,
                      compute_capability=list(torch.cuda.get_device_capability(0)))
        smi = shutil.which('nvidia-smi')
        if smi:
            query = subprocess.run([smi, '--query-gpu=name,driver_version,memory.total',
                                    '--format=csv,noheader'], capture_output=True, text=True, timeout=10)
            result['nvidia_smi_inventory'] = query.stdout.strip() if query.returncode == 0 else 'query_failed'
    return result


def analytical_work(batch, prefix, decode, width, element_bytes):
    """Exact dense matmul MAC counts for the implemented paths; omit softmax,
    masks, copies, bias, allocation, launch/scheduling and indexing overhead.
    One multiply-accumulate = one MAC, not two operations.
    """
    lengths = list(range(prefix + 1, prefix + decode + 1))
    full_projection = sum(3 * batch * n * width * width for n in lengths)
    full_attention = sum(2 * batch * n * n * width for n in lengths)
    last_attention = sum(2 * batch * n * width for n in lengths)
    last_output = decode * batch * width * width
    cached_projection = 3 * batch * (prefix + decode) * width * width
    result = {
        'dense_all': full_projection + full_attention + sum(batch * n * width * width for n in lengths),
        'last_query_recompute': full_projection + last_attention + last_output,
        'cached_cat': cached_projection + last_attention + last_output,
        'cached_preallocated': cached_projection + last_attention + last_output,
    }
    # Sum of newly allocated concatenation destination elements for both K/V.
    # This is analytical destination storage written, not measured memory traffic.
    return {'matmul_macs': result,
            'live_kv_payload_bytes_at_end': 2 * batch * (prefix + decode) * width * element_bytes,
            'cat_destination_bytes_over_decode': 2 * batch * sum(lengths) * width * element_bytes,
            'preallocated_kv_capacity_bytes': 2 * batch * (prefix + decode) * width * element_bytes}


def measure(path, device):
    if device == 'cuda':
        torch.cuda.synchronize()
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        output = path()
        end.record()
        end.synchronize()
        elapsed = start.elapsed_time(end)
    else:
        begin = time.perf_counter_ns()
        output = path()
        elapsed = (time.perf_counter_ns() - begin) / 1e6
    # All output positions are returned; no asynchronous host transfer in timing.
    del output
    return elapsed


def check_case(model, x, prefix, decode, paths, dtype):
    expected = paths['dense_all']()
    tolerance = 5e-3 if dtype == torch.float16 else 1e-5
    checks = {}
    for name in METHODS:
        value = paths[name]()
        checks[name] = {'allclose': bool(torch.allclose(expected, value, atol=tolerance, rtol=tolerance)),
                        'max_absolute_error': float((expected-value).abs().max().item()),
                        'absolute_relative_tolerance': tolerance,
                        'finite': bool(torch.isfinite(value).all().item())}
        del value
    # Causality: changing future embeddings cannot alter the first checked output.
    altered = x.clone()
    if decode > 1:
        altered[:, prefix+1:] += 7
    other = make_paths(model, altered, prefix, decode)['dense_all']()[:, :1]
    causal = bool(torch.allclose(expected[:, :1], other, atol=tolerance, rtol=tolerance))
    del other, altered, expected
    if not causal or any(not c['allclose'] or not c['finite'] for c in checks.values()):
        raise RuntimeError(f'Correctness check failed: {checks}, causal={causal}')
    return {'paths': checks, 'future_perturbation_first_output_unchanged': causal}


def run_study(device='cuda', output='new_gpu_results.json', extended=False,
              repeats=9, warmup=3, dtype_name=None):
    if device not in ('cpu', 'cuda'):
        raise ValueError('unsupported device')
    if device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA is unavailable. No CPU substitution was performed.')
    torch.set_num_threads(1)
    dtype_name = dtype_name or ('float16' if device == 'cuda' else 'float32')
    dtype = {'float16': torch.float16, 'float32': torch.float32}[dtype_name]
    if device == 'cpu' and dtype != torch.float32:
        raise ValueError('This CPU audit requires float32')
    prefixes = [16, 64, 128, 256] if extended else [64, 256]
    decodes = [8, 32] if extended else [32]
    seeds = [7, 42, 101] if extended else [7, 42]
    configurations = [(b, p, d, s) for b in [1, 4] for p in prefixes for d in decodes for s in seeds]
    # Randomize case order as well as method order within each trial block.
    random.Random(11011).shuffle(configurations)
    script_path = Path(globals().get('__file__', 'colab_benchmark.py'))
    result = {'status': 'executed', 'recorded_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'untrained_single_layer_attention_arithmetic_not_llm_or_serving',
              'source_basis': 'https://github.com/VEDANT1602/inference-systems-lab/blob/main/inference_lab/kv.py',
              'archived_source_commit': '5780a7c0661c4cf528957cff730de16e3fd447c4',
              'benchmark_script_sha256': hashlib.sha256(script_path.read_bytes()).hexdigest() if script_path.exists() else None,
              'environment': inventory(device), 'dtype': dtype_name,
              'methods': list(METHODS), 'repeats': repeats, 'warmup_per_method': warmup,
              'randomized_case_order_seed': 11011, 'method_order_seed_rule': '900000+case_index',
              'timing_scope': 'CUDA events with per-trial synchronization' if device == 'cuda' else 'CPU perf_counter_ns wall time',
              'cached_setup_included': 'cache allocation and projection-only prefix setup included',
              'memory_scope': 'CUDA incremental allocated peak measured separately per method; allocator reserved memory not reported',
              'cases': []}
    print(json.dumps({'starting': result['environment'], 'cases': len(configurations)}), flush=True)
    with torch.inference_mode():
        for index, (batch, prefix, decode, seed) in enumerate(configurations):
            torch.manual_seed(seed)
            if device == 'cuda':
                torch.cuda.manual_seed_all(seed)
            model = AuditAttention(64, 4).to(device=device, dtype=dtype).eval()
            x = torch.randn(batch, prefix+decode, 64, device=device, dtype=dtype)
            paths = make_paths(model, x, prefix, decode)
            checks = check_case(model, x, prefix, decode, paths, dtype)
            for _ in range(warmup):
                for name in METHODS:
                    del_result = paths[name]()
                    del del_result
            if device == 'cuda':
                torch.cuda.synchronize()
            randomizer = random.Random(900000+index)
            raw = []
            for block in range(repeats):
                order = list(METHODS)
                randomizer.shuffle(order)
                for position, name in enumerate(order):
                    raw.append({'block': block, 'order_in_block': position,
                                'method': name, 'ms': measure(paths[name], device)})
            memory = {}
            if device == 'cuda':
                for name in METHODS:
                    torch.cuda.synchronize()
                    baseline = torch.cuda.memory_allocated()
                    torch.cuda.reset_peak_memory_stats()
                    value = paths[name]()
                    torch.cuda.synchronize()
                    memory[name] = {'baseline_allocated_bytes': baseline,
                                    'incremental_peak_allocated_bytes': torch.cuda.max_memory_allocated()-baseline}
                    del value
            medians = {name: statistics.median(row['ms'] for row in raw if row['method'] == name)
                       for name in METHODS}
            case = {'case_index': index, 'batch': batch, 'prefix': prefix, 'decode': decode,
                    'seed': seed, 'width': 64, 'heads': 4, 'correctness': checks,
                    'raw_trials': raw, 'median_ms': medians, 'cuda_separate_memory': memory,
                    'analytical': analytical_work(batch, prefix, decode, 64, x.element_size())}
            result['cases'].append(case)
            Path(output).write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps({'completed_case': index+1, 'total_cases': len(configurations),
                              'batch': batch, 'prefix': prefix, 'decode': decode, 'seed': seed,
                              'median_ms': medians}), flush=True)
            del paths, model, x
    print(json.dumps({'output': str(Path(output).resolve()), 'status': 'executed',
                      'cases': len(result['cases'])}), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    parser.add_argument('--output', default='new_gpu_results.json')
    parser.add_argument('--extended', action='store_true')
    parser.add_argument('--repeats', type=int, default=9)
    parser.add_argument('--warmup', type=int, default=3)
    parser.add_argument('--dtype', choices=['float16', 'float32'])
    args = parser.parse_args()
    if args.repeats < 3 or args.warmup < 1:
        parser.error('at least three trials and one warmup are required')
    run_study(device=args.device, output=args.output, extended=args.extended,
              repeats=args.repeats, warmup=args.warmup, dtype_name=args.dtype)
