# Reproduce the braking-clearance comparisons

The original synthetic study is Vedant Thaker's version 0.1.0, dated November 11, 2026. The November 24 working paper adds a sufficient ordering condition, a four-cell comparison by cap and onset order, an independent numerical checker, a paired witness figure and a separate observational test on public highway trajectories. The physical units are metres and seconds. The 1 m threshold in this experiment is a diagnostic choice.

## Verify the synthetic results offline

From the package root, with Python 3.11 or later, run:

```sh
python study/check_clearance.py
```

No third-party packages or GPU are required for this command. It checks the original code and archived file hashes and independently calculates all 2,916 factorial clearances and all 30,000 nominal, actual and corner clearances for the two 5,000-draw experiments. Its numerical method brackets relative-velocity roots on intervals of monotonicity defined using relative acceleration. The checked output is in `ordering-audit.json`. The test uses a 10⁻⁹ m absolute agreement threshold. Use `--output <path>` to save the output separately.

`archived-results.zip` contains the exact original `results/summary.json` and six CSV files. The 2,916-row factorial output and the dense and integration checks describe different input sets. `factorial.csv` includes both signs of the error for the instantaneous estimate in the columns `instant_shortfall_m` and `instant_excess_m`. `uncertainty.csv` contains each input draw, its nominal and actual parameters, and both decisions with the common 1 m margin. `witness_trajectory.csv` samples the largest discrepancy. `by_delay.csv` groups the factorial outcomes. The CSV files retain the original serialization and content digests. `source-hashes.json` identifies the November 11 source commit and lists SHA-256 digests against which the local files were verified.

## Regenerate the full synthetic study

The original run used CPython 3.11.9 on Windows with NumPy 1.26.0 and Matplotlib 3.7.3. In a Python 3.11 environment:

```sh
python -m pip install -r study/original-requirements.txt
python study/study.py --output reproduced-results
```

The program writes fresh figures, CSVs and summary into the chosen directory. The November 24 check used a Linux host with CPython 3.12.14, NumPy 2.3.5 and Matplotlib 3.10.8. Four of the six numerical tables matched the original file digests exactly. `uncertainty.csv` had floating-point differences up to 2.85 × 10⁻¹⁴ m, and `witness_trajectory.csv` up to 7.11 × 10⁻¹⁵ m. Every boolean decision and all study headline numbers were reproduced. The original study script has SHA-256 `7efb0efc8e1bca71c824cfb264b9e7af0cf9ce4cfb85dce81fa8036ada577f6a`.

With Matplotlib installed, `python study/plot_witness.py` regenerates the two-case figure using cases 2367 and 1437. Each trajectory uses its saved model parameters. A figure is generated for the model, not for any specific driver or vehicle.

## Observational comparison

The separate [observational study directory](observed/) gives the FHWA data source, window-selection algorithm, query records and aggregate results. Its six-second windows describe observed near-stops, without fitting the synthetic model's emergency-braking parameters.

## Scope and provenance

The historical source commit is `2da723d76dc465a081b29d40a67f512fc5e40c5c` in the author's access-controlled braking-clearance-benchmark repository. The included archive and code allow offline verification from the download. The original package did not grant a software license. This supplement preserves the original terms and credits. External publications and traffic data retain their respective terms.
