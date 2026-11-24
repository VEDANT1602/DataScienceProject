# Reproduce the attention measurement report

The primary comparisons use generated tensors and saved timings. All results can be checked offline. The CPU result sets use different machines, programs and dates; each has its own timestamp and environment. The T4 files are historical observations of the original two programs.

## Verify the reported measurements

From this directory, using Python 3.11 or newer, run:

```sh
python verify.py
python analyze.py --output-dir reproduced
```

The first command checks five source-file hashes, validates timing blocks and tests the results against the values printed in all three tables. The second writes four CSVs. Both use only the Python standard library. Compare the regenerated CSVs with the corresponding files under `outputs/`. For Figure 1, `python plot_contrasts.py` reads `outputs/historical-cases.csv` and rebuilds the PNG using matplotlib.

## Run the numerical checks

Use a Python environment with the CPU build of PyTorch 2.9.1. The November 24 checks used Python 3.12.14, Linux x86_64 and torch 2.9.1+cpu.

```sh
python -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
python -m unittest discover -s archived -p test_attention_audit.py -v
python check_split.py
```

The three historical tests include 18 float64 reference configurations, cache-call isolation and a hand-checked MAC count. The new test compares both split-projection programs at all four timing geometries to the suffix of a single full causal SDPA computation in float64. Timing is outside these checks.

## Repeat the matched CPU experiment

Start three separate Python processes in sequence, with a fresh output path per session:

```sh
python split_control.py --session 1 --output new-session-1.json
python split_control.py --session 2 --output new-session-2.json
python split_control.py --session 3 --output new-session-3.json
```

Each process sets both Torch thread counts to one. On Linux it binds to the smallest allowed logical CPU ID. It uses the same model and input seed, shuffles configuration order, then balances the two method orders within each case. Each JSON retains the code and model hashes, build details, UTC start/end times, all 96 timing records and maximum numerical differences. It refuses to overwrite a result. Different hardware, runtime load or clocks change timings. Table 2 uses the three files actually recorded in `outputs/split-session-*.json`. A local repeat does not replace those observations.

## Original input records

- `archived/cpu_results.json`, `archived/colab_benchmark.py` and `archived/test_attention_audit.py` are the original study's byte-exact CPU evidence, benchmark and independent validation suite, from the author's attention-baseline-audit revision `6db0313037ca93728adaea94f8ebd54ab7e95bf0`. The CPU run was captured November 11 with CPython 3.11.9 and torch 2.9.1+cpu on Windows, before the matched Linux experiment. Optional reruns of that four-program measurement should use a fresh output file, e.g. `python archived/colab_benchmark.py --device cpu --extended --repeats 11 --output new-four-path.json`.
- `archived/t4-first.json` and `archived/t4-repeat.json` are the two byte-exact captures in [the public archive](https://github.com/VEDANT1602/inference-systems-lab/tree/7e1b547cb35c32e5286acc342529617a7ad3c5f4/results/colab-t4). The first was captured before and the second after installing additional packages and restarting Python. Both identify portfolio source commit [5780a7c0](https://github.com/VEDANT1602/DataScienceProject/commit/5780a7c0661c4cf528957cff730de16e3fd447c4). Each records one T4 configuration with blocked method order and a combined allocator peak. The newer split or preallocation programs have no saved CUDA measurements.
- `outputs/historical-cases.csv` has one row per contrast and case. `historical-summary.csv` summarizes all 48 cases. `matched-cpu.csv` has one row per new process and case. `t4-summary.csv` contains two rows. In every ratio the number over the line names the program whose time is divided by that of the denominator. A ratio above one means the denominator was faster.

## Source rights

The original Inference Systems Lab software is available under its existing MIT notice, reproduced in `archived/UPSTREAM-LICENSE`. The original four-path benchmark was based on that project. The November 11 attention audit did not add a license grant. Credit the public source and retain its software notice when reusing derived code. Software license notices do not change the authorship of the manuscripts.
