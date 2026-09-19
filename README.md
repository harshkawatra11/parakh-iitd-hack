# परख · Parakh

**Parakh** (Sanskrit/Hindi: *discernment; the act of appraising true worth*) is our
submission and review console for **Innov8 4.0 — "The Corporate Heist"**
(Eightfold.ai × ARIES, IIT Delhi).

## The problem, in one line
Given Nightingale Systems' historical hiring archive and a new cycle's 10,000-profile
applicant pool ("the Vault"), rank the 500 candidates most likely to become this cycle's
top 5% performers — where the Vault runs on a hiring standard that is deliberately
**different** from the archive it was trained on.

## Our thesis
A model trained only on `train.csv → post_hire_score` learns the *old* hiring panel's
biases — institute prestige, employer brand, "proper" degrees, CV gaps. The insider's
debrief says the panel changed. We built a three-layer system instead of a single model:

1. **Forensics** — remove internally-inconsistent ("fabricated") profiles and collapse
   duplicate people entered twice by different recruiters.
2. **Merit model** — a LightGBM regressor + top-5% classifier blend, trained with every
   deprecated-bias feature (institute, city, referral channel, employer type, degree,
   CV gaps) deliberately excluded.
3. **Regime-shift layer** — the debrief's own claims, turned into code: a notice-period
   cutoff, a learned title-inflation floor, a public-code-contributions fast-track ramp,
   a "no pedigree, no problem" boost for new colleges that top the assessment, and a
   narrow, evidence-derived "old-boys' network" bonus for the handful of schools whose
   effect on performance survives after controlling for merit.

## Verified, not assumed
Every claim below is printed by `code/main.py` itself at run time — not a one-off
analysis, a build-time assertion.

| Check | Result |
|---|---|
| Fabricated profiles removed from the Archive | 561 / 20,000 — mean outcome **5.49**, zero in the true top 5% |
| Fabricated profiles removed from the Ledger (dev) | 87 / 2,999 — **zero** of the 150 true winners among them |
| Fabricated profiles removed from the Vault (test) | 393 / 10,000 |
| Title-inflated profiles removed from the Vault | 149 — seniority the Archive says cannot be earned that fast |
| Late-availability profiles removed from the Vault | 208 — `notice_period > 60 days`, a value that **never occurs** in train or dev |
| Duplicate people collapsed in the Vault | 10,000 rows → **9,754 real people** |
| Ledger recall@150, de-biased ("vault-lens") model | **68 / 150** (chance ≈ 7.5) |
| Ledger recall@150, full model incl. deprecated features | 95 / 150 — the inflation those features cause, and why we don't use them |
| Old-boys' network (computed, not hardcoded) | MDS Ajmer, IISc, BITS Pilani, IIT Kharagpur, NIT Warangal |
| Determinism | two consecutive runs → byte-identical `submission.csv` (MD5 match) |
| Runtime | ~60 s, CPU only, 2 cores (limit 300 s) |

## Repository layout
```
submission.csv          the ranked shortlist (rank, candidate_id) — 500 rows
documentation.pdf        4-page methodology writeup (see documentation.md for source)
code/
  main.py                 the entire pipeline: parsing -> forensics -> model -> rules
  README.md                how to run it
data-export/
  parakh_meta.json         summary numbers consumed by the web console
web/                     Parakh — the Next.js review console (see below)
```

## Run the pipeline
```
cd code
python main.py
```
Needs `train.csv`, `dev.csv`, `dev_winners.csv`, `test.csv` in the working directory
(not committed — see the problem statement). Writes `submission.csv` there.
Python 3.11 · numpy, pandas, scikit-learn, lightgbm only. Set `PARAKH_EXPORT=1` to also
emit `parakh_export.json` / `parakh_meta.json` for the web console.

## Parakh — the review console
A static, data-driven audit trail for the shortlist: the debrief annotated line by line,
an exclusion funnel, per-candidate score decomposition, and the Ledger validation curve.
Built with Next.js 15, shadcn/ui, Framer Motion, GSAP and Chart.js. See `web/README.md`.

Live: **https://parakh-ideaforge.vercel.app**

---
Built for **Innov8 4.0 · Eightfold.ai × ARIES, IIT Delhi** by **Team IdeaForge**.
