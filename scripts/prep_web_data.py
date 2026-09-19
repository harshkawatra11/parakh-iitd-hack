"""
Post-processes parakh_export.json (raw, ~11MB, one row per test.csv candidate)
into the compact JSON files the Parakh web console consumes:

  shortlist.json   - the 500 selected candidates, richly annotated
  exclusions.json  - a sample of excluded candidates with a human-readable reason
  funnel.json      - the exclusion funnel stage counts
  evidence.json    - the archive-level statistics (correlations, group means, etc.)
  validation.json  - the Ledger recall numbers

Run from the repo root:  python scripts/prep_web_data.py
"""
import json, re, os
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT = os.path.join(ROOT, "data-export", "parakh_export.json")
META = os.path.join(ROOT, "data-export", "parakh_meta.json")
SUB = os.path.join(ROOT, "submission.csv")
CSV_DIR = os.path.join(os.path.dirname(ROOT), "Innov8 4.0")
OUT = os.path.join(ROOT, "web", "public", "data")
os.makedirs(OUT, exist_ok=True)

print("loading...")
rows = json.load(open(EXPORT, encoding="utf-8"))
df = pd.DataFrame(rows)
meta = json.load(open(META, encoding="utf-8"))
sub = pd.read_csv(SUB)

test_raw = pd.read_csv(os.path.join(CSV_DIR, "test.csv"), dtype=str)
raw_map = test_raw.set_index("candidate_id")[
    ["technical_assessment", "aptitude_score", "last_rating", "kpi_met",
     "total_experience", "notice_period", "current_ctc", "expected_ctc",
     "graduation_year", "age", "recruiter_note", "public_code_contributions"]
]
df = df.set_index("candidate_id").join(raw_map).reset_index()

def r2(x):
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return None
    return round(float(x), 3)

def sraw(x):
    """Safe raw string field: NaN/None -> None, never a bare NaN literal in JSON."""
    if x is None:
        return None
    if isinstance(x, float) and np.isnan(x):
        return None
    s = str(x)
    return None if s.lower() == "nan" else s

# ---------- shortlist.json ----------
rank_map = dict(zip(sub.candidate_id, sub["rank"]))
short = df[df.candidate_id.isin(rank_map)].copy()
short["rank"] = short.candidate_id.map(rank_map)
short = short.sort_values("rank")

shortlist = []
for _, r in short.iterrows():
    shortlist.append({
        "rank": int(r["rank"]),
        "candidate_id": r.candidate_id,
        "name": sraw(r.get("name")),
        "role": sraw(r.get("role")),
        "title": sraw(r.get("title")),
        "institute": sraw(r.get("institute")),
        "score": r2(r.get("score")),
        "tech_raw": sraw(r.get("technical_assessment")),
        "tech": r2(r.get("f_tech")),
        "apt": r2(r.get("f_apt")),
        "rating": r2(r.get("f_rating")),
        "kpi": sraw(r.get("kpi_met")),
        "exp_raw": sraw(r.get("total_experience")),
        "exp": r2(r.get("f_exp")),
        "notice_raw": sraw(r.get("notice_period")),
        "ctc_raw": sraw(r.get("current_ctc")),
        "ectc_raw": sraw(r.get("expected_ctc")),
        "pcc": r2(r.get("pcc")),
        "bonus_pcc": r2(r.get("b_pcc")),
        "bonus_newcol": r2(r.get("b_newcol")),
        "bonus_oldboys": r2(r.get("b_oldboys")),
        "newCollege": bool(r.get("b_newcol", 0) and r.get("b_newcol") > 0),
        "oldBoys": bool(r.get("b_oldboys", 0) and r.get("b_oldboys") > 0),
    })
json.dump(shortlist, open(os.path.join(OUT, "shortlist.json"), "w", encoding="utf-8"), allow_nan=False)
print("shortlist.json:", len(shortlist), "rows")

# ---------- exclusions.json ----------
excl = df[df.excluded == True].copy()  # noqa: E712

def reason_detail(r):
    if r.get("fabricated"):
        age, ysg, exp = r.get("f_age"), r.get("f_ysg"), r.get("f_exp")
        if pd.notna(age) and pd.notna(ysg) and (age - ysg) < 18:
            return "fabricated", f"implies graduating from college before age 18"
        if pd.notna(exp) and pd.notna(age) and exp > (age - 20):
            return "fabricated", f"claims {r.get('exp_raw')} experience, more than an adult life allows at age {int(age) if pd.notna(age) else '?'}"
        return "fabricated", "career history is internally inconsistent with stated experience/graduation year"
    if r.get("inflated"):
        return "inflated", f"holds title '{r.get('title')}' with tenure the Archive never associates with that seniority"
    if r.get("late"):
        return "late", f"notice period of {r.get('notice_raw')} exceeds the two-month cutoff"
    return "other", ""

reasons = excl.apply(reason_detail, axis=1)
excl["reason"] = [x[0] for x in reasons]
excl["detail"] = [x[1] for x in reasons]

exclusions = []
# cap the sample for payload size but keep it representative across reasons
for reason, grp in excl.groupby("reason"):
    sample = grp.head(250)
    for _, r in sample.iterrows():
        exclusions.append({
            "candidate_id": r.candidate_id,
            "name": sraw(r.get("name")),
            "role": sraw(r.get("role")),
            "title": sraw(r.get("title")),
            "reason": r["reason"],
            "detail": r["detail"],
        })
json.dump(exclusions, open(os.path.join(OUT, "exclusions.json"), "w", encoding="utf-8"), allow_nan=False)
print("exclusions.json:", len(exclusions), "rows (sampled from", len(excl), "total)")

# ---------- funnel.json ----------
n_total = len(df)
n_fab = int(df.fabricated.sum())
n_infl = int(df.inflated.sum())
n_late = int(df.late.sum())
n_excl_union = int(df.excluded.sum())
n_after_excl = n_total - n_excl_union
# duplicate collapse count from meta / recompute simple approx via name+grad key
dup_count = n_total - 9754  # verified constant from the pipeline run
funnel = [
    {"stage": "Vault applicant pool", "count": n_total, "note": "test.csv, 10,000 rows"},
    {"stage": "Fabricated profiles removed", "count": n_total - n_fab, "note": f"-{n_fab} internally inconsistent"},
    {"stage": "Title-inflated removed", "count": n_total - n_fab - n_infl, "note": f"-{n_infl} seniority the Archive says is unearned"},
    {"stage": "Cannot join in time removed", "count": n_after_excl, "note": f"-{n_late} notice period > 60 days"},
    {"stage": "Duplicate people collapsed", "count": n_after_excl - dup_count, "note": f"-{dup_count} re-entered by a second recruiter"},
    {"stage": "Final shortlist", "count": 500, "note": "ranked 1-500"},
]
json.dump(funnel, open(os.path.join(OUT, "funnel.json"), "w", encoding="utf-8"))
print("funnel.json:", funnel)

# ---------- validation.json ----------
validation = {
    "recallVault": meta["recall_vault"],
    "recallFull": meta["recall_full"],
    "totalWinners": 150,
    "randomBaseline": round(150 * 150 / 2999, 1),
    "oldBoys": meta["old_boys"],
}
json.dump(validation, open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8"))
print("validation.json:", validation)

# ---------- evidence.json ----------
train = pd.read_csv(os.path.join(CSV_DIR, "train.csv"), dtype=str)

def p_tech(v):
    if not isinstance(v, str): return np.nan
    v = v.strip()
    if v.lower() in ("absent", "not taken", ""): return np.nan
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*/\s*100", v)
    if m: return float(m.group(1))
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*%", v)
    if m: return float(m.group(1))
    try: f = float(v)
    except ValueError: return np.nan
    return f * 100.0 if f <= 1.0 else f

y = pd.to_numeric(train.post_hire_score, errors="coerce")
ta = train.technical_assessment.map(p_tech)

corr_rows = []
kpi_bin = train.kpi_met.str.lower().map({"yes": 1, "y": 1, "1": 1, "true": 1,
                                          "no": 0, "n": 0, "0": 0, "false": 0})
for name, series in [("technical_assessment", ta), ("kpi_met", kpi_bin),
                      ("age", pd.to_numeric(train.age, errors="coerce")),
                      ("graduation_year", pd.to_numeric(train.graduation_year, errors="coerce")),
                      ("num_employers", pd.to_numeric(train.num_employers, errors="coerce"))]:
    ok = series.notna() & y.notna()
    if ok.sum() > 50:
        corr_rows.append({"feature": name, "spearman": r2(series[ok].corr(y[ok], method="spearman"))})

kpi_group = train.assign(kpi_bin=kpi_bin, y=y).dropna(subset=["kpi_bin"])
kpi_stats = kpi_group.groupby("kpi_bin").y.mean().to_dict()

evidence = {
    "correlations": corr_rows,
    "kpiEffect": {"met": r2(kpi_stats.get(1.0)), "notMet": r2(kpi_stats.get(0.0))},
    "note": "Computed from train.csv (the Archive), n=20,000.",
}
json.dump(evidence, open(os.path.join(OUT, "evidence.json"), "w", encoding="utf-8"))
print("evidence.json:", evidence)

print("done. output dir:", OUT)
