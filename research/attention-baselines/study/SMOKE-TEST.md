# Numerical smoke test

November 24, 2026. The archived timings and new observations used in the manuscript passed independent reconstruction. The numerical tests ran on a CPU host. No CUDA experiment was executed for this edition.

| Check | Evidence |
|---|---|
| Historical CPU data and code | Original raw data SHA-256 fb983199bed74bf9090a1b213689ebd3d858d4761941267707cc6663de6dc71c. Benchmark and tests matched the source manifest. All 48 configurations contained 11 complete randomized timing blocks. |
| Matched CPU data | Each of three fresh processes timed four geometries with 12 complete paired blocks each. Every case had six runs of each method order. All values were positive. Maximum float32 error against dense-all was 8.94 × 10⁻⁸. |
| Timing summaries | All numbers in manuscript Tables 1–3 matched source timings after rounding. All four analysis CSVs matched the second reconstruction byte for byte. |
| Numerical references | The three original tests passed, including 18 float64 causal SDPA reference geometries. Eight additional full-sequence float64 comparisons of the matched paths passed, with maximum absolute error 1.943 × 10⁻¹⁶. |
| GPU archive | Both published JSON files matched their raw file hashes. Recomputed ratios were 1.232622 and 1.361458. The two captures used different Torch builds and blocked method order. |
| Scope | All three fresh processes ran on one AMD EPYC host. The CPU evidence is conditional on the tested shapes. The T4 measurements cannot price the query-matched control. |

## Matched CPU process times (UTC)

| Session | Start | End |
|---|---|---|
| 1 | 2026-11-24T11:05:53.515113+00:00 | 2026-11-24T11:05:54.425008+00:00 |
| 2 | 2026-11-24T11:05:55.905357+00:00 | 2026-11-24T11:05:56.836566+00:00 |
| 3 | 2026-11-24T11:05:58.381537+00:00 | 2026-11-24T11:05:59.315536+00:00 |
