"""Numerical/property checks for the research benchmark, separate from timings."""
import json
import unittest
from pathlib import Path

import torch
import torch.nn.functional as F

from colab_benchmark import AuditAttention, analytical_work, make_paths


class AttentionAuditTests(unittest.TestCase):
    def test_outputs_match_independent_sdpa_reference(self):
        torch.set_num_threads(1)
        checked = 0
        with torch.inference_mode():
            for width, heads in [(8, 1), (16, 4), (64, 4)]:
                for batch in [1, 3]:
                    for prefix, decode in [(1, 1), (2, 4), (13, 7)]:
                        torch.manual_seed(902 + checked)
                        model = AuditAttention(width, heads).double().eval()
                        x = torch.randn(batch, prefix+decode, width, dtype=torch.float64)
                        outputs = []
                        for i in range(decode):
                            q, k, v = model.projections(x[:, :prefix+i+1])
                            value = F.scaled_dot_product_attention(q, k, v, dropout_p=0.0, is_causal=True)
                            joined = value.transpose(1, 2).reshape(batch, prefix+i+1, width)
                            outputs.append(model.out(joined)[:, -1:])
                        reference = torch.cat(outputs, dim=1)
                        for name, path in make_paths(model, x, prefix, decode).items():
                            self.assertTrue(torch.allclose(reference, path(), atol=1e-11, rtol=1e-11),
                                            (width, heads, batch, prefix, decode, name))
                        checked += 1
        self.assertEqual(checked, 18)

    def test_cache_run_has_no_state_leak_between_calls(self):
        with torch.inference_mode():
            torch.manual_seed(14)
            model = AuditAttention(16, 4).eval()
            x = torch.randn(2, 23, 16)
            paths = make_paths(model, x, 11, 12)
            for name in ['cached_cat', 'cached_preallocated']:
                first = paths[name]()
                second = paths[name]()
                self.assertTrue(torch.equal(first, second), name)

    def test_analytical_macs_hand_case(self):
        counts = analytical_work(1, 2, 2, 4, 4)
        self.assertEqual(counts['matmul_macs'], {'dense_all': 648,
                                               'last_query_recompute': 424,
                                               'cached_cat': 280,
                                               'cached_preallocated': 280})
        self.assertEqual(counts['live_kv_payload_bytes_at_end'], 128)
        self.assertEqual(counts['cat_destination_bytes_over_decode'], 224)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AttentionAuditTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    Path(__file__).with_name('validation.json').write_text(json.dumps({
        'tests_run': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'successful': result.wasSuccessful(),
        'independent_reference_cases': 18, 'reference_dtype': 'float64',
        'reference': 'torch.nn.functional.scaled_dot_product_attention is_causal=True',
        'scope': 'numerical equivalence/state isolation/analytical arithmetic; not performance validation'
    }, indent=2), encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
