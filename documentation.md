# The Corporate Heist — Solution Documentation
**Team name:** IdeaForge
**Member:** Harsh Kawatra
**College:** Delhi Technological University (DTU)

## 1. Summary
We treat the Vault as a different population from the Archive, not as more of the same.
Three layers: (a) a forensic pass that removes internally inconsistent ("fabricated")
profiles and collapses duplicate people; (b) a LightGBM merit model trained on
post_hire_score with every feature the debrief says the new panel ignores deliberately
removed; (c) a regime-shift layer that turns each line of the debrief into a hard rule
or a calibrated bonus. Validated end-to-end on the Ledger: the de-biased ("vault-lens")
model recovers 68 of that cycle's 150 true top-5% at k=150 (chance = 7.5); the full
model with the deprecated old-panel features recovers 95 — which is exactly the +27
inflation we expect from biases the new panel no longer uses, and the reason we do not
submit the full model's ranking.

## 2. Data cleaning and parsing
Every numeric column is multi-format. technical_assessment appears as `47`, `49/100`,
`0.45`, `43.0 %`, `absent`, `not taken` — we map the fraction form (<=1.0) by x100 and
keep a separate "did not sit the test" flag rather than imputing a zero. aptitude_score
appears as `6.3`, `5.0/10`, `41%`. last_rating mixes `3`, `3/5`, `3.0` and the words
Outstanding / Exceeds / Meets / Needs Improvement / Below Expectations, plus
`New joiner - not rated` which is missingness, not a 0. total_experience appears as
`9.4 years`, `9.4 yrs`, `>20`, `20+ years`, `135 months`, `Fresher`, `<1 year`.
Compensation is the worst: `13.9 LPA`, `13.9 lpa`, `Rs13,90,000`, `1390000`, `13.90L`,
`INR 13.9 lakh`, `7.53 Cr` and **`$22,369`** — we normalise everything to INR lakh p.a.
and convert USD at 83 INR/USD. career_path uses three separators (`>`, `->`, `|`, plus a
unicode arrow) and two duration syntaxes (`[23 mo]`, `(1.2 yrs)`). institute collapses 730
raw spellings to roughly 314 schools (`IIT Delhi` / `I.I.T. Delhi` / `IIT-D` / `IITD` /
`Indian Institute of Technology Delhi`); current_city merges Madras→Chennai,
Gurgaon→Gurugram. kpi_met has ten spellings of a boolean. public_code_contributions
(test-only) appears as `12`, `10+`, `3 PRs`, `3 merged PRs`, shorthand like "roughly 3", or `not tracked` — we
parse the first integer and leave `not tracked`/blank as missing, never as zero.

## 3. What drives a great hire — our findings
Spearman correlation with post_hire_score on the Archive: technical_assessment +0.27,
last_rating +0.20, aptitude_score +0.20, graduation_year +0.13; total_experience −0.12
and current_ctc −0.12 are *negative*. kpi_met is the strongest binary: mean 53.4 vs 46.5,
P(top 5%) 0.081 vs 0.033. Awards lift the mean to 53.8 (Spot Award 56.9). Seniority is
inverted-U: candidates at individual-contributor levels average 51.3–51.4 while
Lead/Principal/Director/VP applicants average 45.6–46.3. trainings_last_year (+0.003) and
training_hours (+0.017) are noise. The recruiter_note field is 1,090 concatenations of
roughly 25 fixed sentences; we count positive atoms ("owned production incidents",
"shipped a feature used by 1M+ users") against negative ones ("reference check was
lukewarm", "missed two sprint commitments") rather than embedding the text.

## 4. The current cycle
The debrief describes four changes and all four are visible in the data.
(i) **Notice period.** `notice_period > 60 days` occurs **208 times in test.csv and zero
times in train.csv or dev.csv** — 90/120/150/180-day and 3–6-month values exist only in
the Vault. Excluded.
(ii) **Title inflation.** We learn, per seniority level, the minimum tenure ever observed
in the Archive (e.g. Director/VP levels never appear below roughly 13 years of combined
experience-or-time-since-graduation). The Vault contains **149 profiles** that violate
their level's learned floor. Excluded.
(iii) **Public code contributions.** Test-only. Median 6, p90 26, max 408; uncorrelated
with experience (−0.02) and with our fabrication flags, i.e. an independently injected
signal. Following "a handful means nothing, dozens gets fast-tracked" we apply a
log-ramp bonus that is zero below 12, saturating at +1.0 z by 48. `not tracked` receives
neither bonus nor penalty.
(iv) **Deprecated preferences.** We drop institute, current_city, recruitment_channel,
company_type, company_size, degree and the career-gap feature from the Vault model.
This is costly and deliberate: on the Ledger those features inflate recall@150 from
68 to 95. They are exactly the biases the new panel abandoned. The one survivor is the
old-boys' network: regressing post_hire_score on merit + role and grouping the residual
by school (n≥40, t≥3) isolates a handful — MDS Ajmer, IISc, BITS Pilani, IIT Kharagpur,
NIT Warangal. Note that MDS Ajmer is not a conventional prestige school yet carries the
largest residual, which is the signature of a leadership-alumni effect rather than
brand recognition. Those five get a modest +0.25 z bonus — "a leg up", not a ticket.
(v) **No pedigree, no problem.** A meaningful share of Vault rows come from institutes
that appear nowhere in the Archive or Ledger, with a materially higher median technical
assessment than the rest of the pool. New-school candidates in the top decile of their
role's assessment, with a coherent career history, get a +0.70 z bonus.

## 5. Profiles we excluded and why
**Fabricated (393 in test; 561 in train used only to clean the training label).** A
profile is rejected if any internal check fails: age at graduation < 18; experience >
age − 20; experience > years since graduation + 1.5; stated experience exceeding the
career history by > 1 year; career history overrunning stated experience by > 8 years or
graduation by > 4 years; more than 10 unaccounted years. Calibration on the Archive: 561
rows flagged, mean post_hire_score **5.49**, and **not one of them is in the true top
5%**. On the Ledger, 87 rows flagged and **zero of the 150 winners** among them. The
thresholds sit in empty bands — the Archive has no row with age-at-graduation between 17
and 19.
**Cannot join in time (208).** notice_period > 60 days.
**Title inflation (149).** As above.
**Duplicate people (246 rows in test).** Union-find over normalised phone (last 10
digits), e-mail (lower-cased, dots stripped from the local part) and sorted-name +
graduation year. 10,000 rows resolve to **9,754 people**; we keep each person's
best-scoring entry. Example: CH-0R5RQA "Advani, Vaagdevi" / `61047 27758` and CH-CEZTFK
"Vaagdevi Advani" / `+91 6104727758` are one IIT Delhi 2013 DevOps applicant.

## 6. Model and selection procedure
LightGBM on the de-fabricated Archive (19,439 rows), roughly 40 engineered features, bagged over
seeds 42/202/777. Two heads: an L2 regressor on post_hire_score and a binary classifier on
"is in the top 5%". Their percentile ranks are averaged 50/50. The blended rank is
z-scored, the Vault bonuses (§4) are added, hard exclusions (§5) are set to −infinity,
duplicate people are collapsed to their best-scoring entry, and the top 500 are emitted
in descending order. Validation is the Ledger: the same code path, the same forensics,
recall@150 printed at run time as a build-time assertion, not a claim.

## 7. What did not work
- **Skill-content features.** Lift of each skill token among top performers per role was
  1.3–2.2 on thin counts and incoherent (`pytorch` ranked top for DevOps/SRE, `vuejs`
  second). Only the *count* of skills survived into the feature set.
- **Sentence-transformer embeddings of recruiter_note.** The field is a closed vocabulary
  of roughly 25 atoms; keyword counting is exact and costs nothing, embeddings cost real runtime
  budget for no measurable gain.
- **Target-encoding the institute for the Vault.** Lifts Ledger recall by about 27 points, but
  it is the deprecated bias in disguise. Rejected on the debrief's evidence, not on taste.
- **Treating `not tracked` public contributions as 0.** Would penalise over a thousand
  candidates for a recruiter's data-entry habit rather than their actual record.
- **Predicting a score for all 10,000 and cutting at the 95th percentile.** Only
  membership and order of the 500 matter; effort was better spent on the exclusion rules,
  which is where the fabricated/duplicate/inflated profiles actually get removed.

## 8. External resources and AI tools (mandatory)
- **Libraries:** numpy, pandas, scikit-learn, LightGBM (all from the permitted list). No
  external datasets, no pretrained models, no network access.
- **Reference constants:** USD→INR at 83 (public reference rate) for `$`-denominated CTC;
  institute and city alias tables were written by hand from the values present in the
  provided files, not from any external list.
- **AI assistants:** Anthropic Claude (Claude Code) was used to draft and refactor the
  parsing code, to run the exploratory analysis behind §3–§5, and to draft this document.
  Every rule and threshold reported here was re-derived and verified by the team against
  train.csv and dev.csv; all numbers quoted are reproducible from the submitted code and
  are printed by the code itself at run time.

## 9. How to run
    python main.py
`train.csv`, `dev.csv`, `dev_winners.csv`, `test.csv` in the working directory; writes
`submission.csv` there. Python 3.11, CPU only. **Runtime about 60 s** (limit 5 min, i.e. 300 s).
Seeds: `SEED = 42`, model seeds 42/202/777, `PYTHONHASHSEED=42`. Two consecutive runs
produce byte-identical output (verified: identical MD5 hash).
