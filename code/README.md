# Parakh — code

    python main.py

Reads `train.csv`, `dev.csv`, `dev_winners.csv`, `test.csv` from the working
directory and writes `submission.csv` (rank, candidate_id; 500 rows).

Python 3.11 · numpy, pandas, scikit-learn, lightgbm · CPU only, 2 cores
Runtime ~60 s. SEED = 42 throughout; the output is byte-reproducible (verified
via MD5 hash across two consecutive runs).

Set `PARAKH_EXPORT=1` to additionally emit `parakh_export.json` /
`parakh_meta.json`, which power the Parakh review UI. Not required for the
shortlist and off by default.
