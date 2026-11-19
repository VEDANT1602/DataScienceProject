"""Generate the narrative from the measured artifact, not from separate arithmetic."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def link(target: Path, directory: Path):
    try:
        return os.path.relpath(target.resolve(), directory.resolve()).replace(os.sep, "/")
    except ValueError:
        return target.resolve().as_uri()


def number(value, places=3):
    return "N/A" if value is None else f"{value:.{places}f}"


def render(output: Path):
    data = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
    protocol, kv = data.get("endpoint_run"), data.get("attention_run")
    fixture = data["execution_kind"] == "loopback_protocol_fixture"
    if fixture:
        title = "Streaming measurements from the loopback fixture"
        context = ("The server returns known answers. This run checks whether the client records admission, "
                   "first content, completion, task quality and retry costs consistently. Its timings belong "
                   "to the fixture and client on this host.")
    else:
        title = "Streaming measurements from the configured endpoint"
        context = ("The client sent the fictional evaluation workload to the configured endpoint. "
                   "These results describe this model, concurrency and operating condition.")
    lines = [f"# {title}", "", context, ""]
    if protocol:
        lines.extend(["## Which requests finished within the serving contract?", "",
                      f"The batch scheduled {protocol['requests']} requests at concurrency {protocol['concurrency']}. "
                      f"Across {protocol['attempts']} attempts, {protocol['transport_successes']} requests completed the stream, "
                      f"{protocol['quality_successes']} returned an accepted schema and label, and "
                      f"{protocol['slo_successes']} met the post-admission latency limits as well.", "",
                      "| Batch observation | Value |", "| --- | ---: |",
                      f"| HTTP and stream completions | {protocol['transport_successes']}/{protocol['requests']} |",
                      f"| Correct responses | {protocol['quality_successes']}/{protocol['requests']} |",
                      f"| Responses meeting the SLO | {protocol['slo_successes']}/{protocol['requests']} |",
                      f"| First nonempty content, accepted answers, p50 / p95 | {number(protocol['ttft_proxy_successes_ms']['p50'])} / {number(protocol['ttft_proxy_successes_ms']['p95'])} ms |",
                      f"| Post-admission end-to-end latency, all requests, p50 / p95 | {number(protocol['e2e_all_requests_ms']['p50'])} / {number(protocol['e2e_all_requests_ms']['p95'])} ms |",
                      "", "First content is measured when a nonempty chunk arrives. A chunk may contain several tokens, "
                      "so inter-token latency is unknown. The all-request end-to-end denominator retains failed and rejected answers. "
                      "The trace records client queue time separately, and a retry retains the failed attempt's time and known usage.",
                      "", "[Per-request and per-attempt traces](traces.jsonl)", ""])
    if kv and kv.get("status") == "executed":
        correctness = kv["correctness"]
        interpretation = ("The two implementations agree at the declared tolerance on these inputs."
                          if correctness["allclose"] else
                          "The two implementations fail the declared tolerance. The timings cannot support a comparison of equivalent outputs.")
        lines.extend(["## A separate tensor calculation", "",
                      f"The recorded device is **{kv['device_name']}**, with dtype {kv['dtype']}, width {kv['width']} "
                      f"and {kv['heads']} attention heads. Both paths use a prefix of {kv['prefix_positions']} positions "
                      f"and decode {kv['decode_positions']} positions. The cached path includes prefill.", "",
                      f"{interpretation} Maximum absolute difference was **{correctness['max_absolute_error']:.8g}**. "
                      f"After {kv['warmup_runs']} warmups, {kv['repeats']} repetitions gave medians of "
                      f"**{number(kv['median_full_recompute_ms'])} ms** for dense recomputation and "
                      f"**{number(kv['median_kv_cached_ms'])} ms** with projected KV reuse.", "",
                      "The benchmark uses a single untrained attention layer. It times tensor operations and "
                      "omits the scheduler, tokenizer and trained model needed for an end-to-end serving comparison.", ""])
    else:
        lines.extend(["This run contains no executed attention measurement.", ""])
    if protocol:
        cost = protocol["cost"]
        lines.extend(["## What goes into the cost estimate?", "",
                      f"The entered input and output rates per million tokens are {number(cost['input_per_million_assumption'])} "
                      f"and {number(cost['output_per_million_assumption'])}. The entered dedicated hourly rate is "
                      f"{number(cost['dedicated_hourly_assumption'])}. Complete usage for all attempts: {cost['all_attempt_usage_known']}.", "",
                      f"The economic break-even under those inputs is **{number(cost['economic_break_even_requests_per_second'])} "
                      "requests per second**. A missing rate or usage needed for the calculation leaves the estimate unavailable. "
                      "A deployment would also have to sustain that rate at the same quality and tail-latency limits. "
                      "The fixture's illustrative rates cannot establish a provider price or a capacity result.", ""])
    lines.extend(["## Evidence for a serving comparison", "",
                  "To test prefix caching, pair a fresh-process run with repeated-prefix requests and record cache state "
                  "alongside both traces. A phase label alone cannot establish a reset or a hit. Keep the same workload, "
                  "output limit and concurrency for both conditions.", "",
                  f"- [Workload and data card]({link(PROJECT / 'data' / 'DATA_CARD.md', output)})",
                  f"- [GPU and endpoint runbook]({link(PROJECT / 'docs' / 'gpu-runbook.md', output)})",
                  f"- [Metric definitions]({link(PROJECT / 'docs' / 'measurement-contract.md', output)})",
                  f"- [Separate archived T4 attention run]({link(PROJECT / 'results' / 'colab-t4' / 'README.md', output)})",
                  "- [Metrics and execution environment for this run](metrics.json)", "",
                  "Independent systems experiment by Vedant Thaker.", ""])
    (output / "case-study.md").write_bytes("\n".join(lines).encode("utf-8"))
    if kv and kv.get("status") == "executed":
        values = [kv["median_full_recompute_ms"], kv["median_kv_cached_ms"]]
        maximum = max(values) * 1.15
        title = "Projected KV reuse passes the arithmetic check" if kv["correctness"]["allclose"] else "Arithmetic check failed; do not interpret the timing ratio"
        device = "CUDA GPU" if kv["device"] == "cuda" else "CPU"
        timing = "CUDA event time" if kv["device"] == "cuda" else "CPU wall time"
        svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="840" height="310" viewBox="0 0 840 310">',
               '<rect width="840" height="310" fill="#f8fafc"/>',
               f'<text x="30" y="34" font-size="22" font-family="sans-serif" fill="#0f172a">{title}</text>',
               f'<text x="30" y="60" font-size="14" font-family="sans-serif">Untrained tiny attention on {device}; this does not measure vLLM serving performance.</text>']
        for i, (name, value) in enumerate(zip(("Full recomputation", "KV reuse + prefill"), values)):
            y = 92 + i * 75
            svg.extend([f'<text x="30" y="{y+23}" font-size="16" font-family="sans-serif">{html.escape(name)}</text>',
                        f'<rect x="225" y="{y}" width="{value/maximum*470:.2f}" height="36" fill="{"#64748b" if i == 0 else "#0369a1"}"/>',
                        f'<text x="{235+value/maximum*470:.2f}" y="{y+24}" font-size="15" font-family="sans-serif">{value:.3f} ms</text>'])
        svg.append(f'<text x="30" y="285" font-size="14" font-family="sans-serif">Median {timing}; same input and weights; warmup excluded; full context vs one-position decode.</text></svg>')
        (output / "attention.svg").write_bytes("\n".join(svg).encode("utf-8"))
