"""
PARAKH — Innov8 4.0 "The Corporate Heist" — Team IdeaForge
Ranked shortlist of 500 candidate_ids from test.csv.

Run:  python main.py        (train.csv, dev.csv, dev_winners.csv, test.csv in cwd)
Out:  submission.csv        (rank, candidate_id)
Runtime: ~25 s on 2 cores. Deterministic: SEED=42 everywhere.
"""
import os, re, sys, random, warnings
import numpy as np
import pandas as pd
import lightgbm as lgb

warnings.filterwarnings("ignore")
SEED = 42
random.seed(SEED); np.random.seed(SEED)
os.environ["PYTHONHASHSEED"] = str(SEED)
REF_YEAR = 2026          # the cycle year; graduation_year is measured against it
K = 500                  # size of the shortlist
USD_TO_INR = 83.0        # public reference rate, cited in the documentation

# ----------------------------------------------------------------------------
# 1. FIELD PARSERS  — every format observed in the three files
# ----------------------------------------------------------------------------
def p_tech(v):
    """technical_assessment -> 0..100. Handles 47 | 49/100 | 0.45 | 43.0 % | absent."""
    if not isinstance(v, str): return np.nan
    v = v.strip()
    if v.lower() in ("absent", "not taken", ""): return np.nan
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*/\s*100", v)
    if m: return float(m.group(1))
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*%", v)
    if m: return float(m.group(1))
    try: f = float(v)
    except ValueError: return np.nan
    return f * 100.0 if f <= 1.0 else f          # 0.45 is a fraction, 45 is a score

def p_apt(v):
    """aptitude_score -> 0..10. Handles 6.3 | 5.0/10 | 41%."""
    if not isinstance(v, str): return np.nan
    v = v.strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*/\s*10", v)
    if m: return float(m.group(1))
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*%", v)
    if m: return float(m.group(1)) / 10.0
    try: return float(v)
    except ValueError: return np.nan

_RATING_WORDS = {"outstanding": 5.0, "exceeds expectations": 4.0,
                 "meets expectations": 3.0, "needs improvement": 2.0,
                 "below expectations": 1.0}
def p_rating(v):
    """last_rating -> 1..5. Handles 3 | 3.0 | 3/5 | Outstanding | New joiner - not rated."""
    if not isinstance(v, str): return np.nan
    s = v.strip()
    if s.lower() in _RATING_WORDS: return _RATING_WORDS[s.lower()]
    if s.lower().startswith("new joiner"): return np.nan
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*/\s*5", s)
    if m: return float(m.group(1))
    try: return float(s)
    except ValueError: return np.nan

def p_bool(v):
    s = str(v).strip().lower()
    if s in ("yes", "y", "1", "true"):  return 1.0
    if s in ("no", "n", "0", "false"):  return 0.0
    return np.nan

def p_years(v):
    """total_experience -> years. Fresher | <1 year | 9.4 yrs | 135 months | >20 | 20+ years."""
    if not isinstance(v, str): return np.nan
    s = v.strip().lower()
    if s.startswith("fresher"): return 0.0
    if s.startswith("<1"):      return 0.5
    m = re.search(r"(\d+(?:\.\d+)?)\s*month", s)
    if m: return float(m.group(1)) / 12.0
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else np.nan

def p_ctc(v):
    """current/expected_ctc -> INR lakhs per annum. 13.9 LPA | Rs13,90,000 | 1390000
       | 13.90L | INR 13.9 lakh | $22,369 | 7.53 Cr."""
    if not isinstance(v, str): return np.nan
    s = v.strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "")
    is_usd = "$" in s
    s = s.replace("$", "").replace("INR", "").strip()
    low = s.lower()
    m = re.match(r"(\d+(?:\.\d+)?)", s)
    if not m: return np.nan
    x = float(m.group(1))
    if "cr" in low:                                        x *= 100.0      # crore -> lakh
    elif "lpa" in low or "lakh" in low or low.endswith("l"): pass          # already lakh
    else:                                                  x /= 1e5        # bare rupees
    if is_usd: x *= USD_TO_INR                                             # USD figure was absolute
    return x

def p_notice(v):
    """notice_period -> days. Immediate/Available now/Immediate joiner/0 days -> 0."""
    s = str(v).strip().lower()
    if s in ("immediate", "available now", "immediate joiner", "0 days"): return 0.0
    m = re.search(r"(\d+)\s*day", s)
    if m: return float(m.group(1))
    m = re.search(r"(\d+)\s*month", s)
    if m: return float(m.group(1)) * 30.0
    return np.nan

def p_awards(v):
    s = str(v).strip().lower()
    return 0.0 if s in ("nan", "-", "none", "0", "") else 1.0

def p_jobchange(v):
    s = str(v).strip().lower()
    if s == "never": return 0.0
    if s == ">4":    return 5.0
    try: return float(s)
    except ValueError: return np.nan

def p_pcc(v):
    """public_code_contributions -> count. 12 | ~3 | 10+ | 3 PRs | 3 merged PRs | not tracked.
       'not tracked' and NaN stay NaN: absence of tracking is NOT zero contributions."""
    if not isinstance(v, str): return np.nan
    s = v.strip().lower()
    if s in ("not tracked", "n/a", "na", "-", "none", ""): return np.nan
    m = re.search(r"(\d+)", s)
    return float(m.group(1)) if m else np.nan

# title seniority ladder, 0 = intern .. 8 = VP/Head
def p_level(t):
    s = str(t).strip().lower()
    if "intern" in s or s.startswith(("trainee", "apprentice")):      return 0
    if s.startswith(("junior", "associate")) or s.endswith(" i"):     return 1
    if s.startswith("vp ") or s.startswith("head of"):                return 8
    if s.startswith("director"):                                      return 7
    if "manager" in s:                                                return 6
    if s.startswith("principal"):                                     return 5
    if s.startswith(("lead", "staff")) or s.endswith("lead"):         return 4
    if s.startswith(("senior", "sr.")) or s.endswith(" iii"):         return 3
    return 2

_CP_SPLIT = re.compile(r"\s*(?:->|>|→|\|)\s*")
_CP_DUR   = re.compile(r"\[(\d+(?:\.\d+)?)\s*mo\]|\((\d+(?:\.\d+)?)\s*(?:y|yr|yrs)\)")
def p_career_years(v):
    """Sum of tenures in career_path, in years. Handles [23 mo] and (1.2 yrs) and (3.5y)."""
    if not isinstance(v, str): return np.nan
    tot = 0.0
    for m in _CP_DUR.finditer(v):
        tot += float(m.group(1)) if m.group(1) else float(m.group(2)) * 12.0
    return tot / 12.0 if tot > 0 else np.nan

def p_career_steps(v):
    if not isinstance(v, str) or not v.strip(): return 0
    return len(_CP_SPLIT.split(v.strip()))

def p_career_maxlevel(v):
    """Highest seniority ever reached in the career history."""
    if not isinstance(v, str) or not v.strip(): return np.nan
    best = 0
    for seg in _CP_SPLIT.split(v.strip()):
        best = max(best, p_level(_CP_DUR.sub("", seg).strip()))
    return float(best)

def n_items(v):
    if not isinstance(v, str) or not v.strip(): return 0
    return len([x for x in re.split(r"[,;|]", v) if x.strip()])

def canon_institute(s):
    """730 raw strings -> ~314 schools. Aliases merged."""
    if not isinstance(s, str): return "unknown"
    t = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    t = re.sub(r"\s+", " ", t).strip()
    t = (t.replace("indian institute of technology", "iit")
           .replace("national institute of technology", "nit")
           .replace("i i t", "iit").replace("n i t", "nit"))
    for a, b in [("iitd", "iit delhi"), ("iitb", "iit bombay"), ("iitm", "iit madras"),
                 ("iitkgp", "iit kharagpur"), ("iitk", "iit kanpur"), ("iitr", "iit roorkee"),
                 ("iitg", "iit guwahati"), ("iith", "iit hyderabad")]:
        t = re.sub(r"\b%s\b" % a, b, t)
    short = {"d": "iit delhi", "b": "iit bombay", "m": "iit madras", "k": "iit kanpur",
             "kgp": "iit kharagpur", "r": "iit roorkee", "g": "iit guwahati", "h": "iit hyderabad"}
    t = re.sub(r"\biit (d|b|m|k|kgp|r|g|h)\b", lambda m: short[m.group(1)], t)
    if "birla institute of technology and science" in t or re.search(r"\bbits\b", t): t = "bits pilani"
    if "delhi technological" in t or t == "dtu" or "delhi college of engineering" in t: t = "dtu"
    if "netaji subhas" in t or "nsit" in t or "nsut" in t: t = "nsut"
    if "indian institute of science" in t or t == "iisc": t = "iisc"
    if "international institute of information technology" in t and "hyderabad" in t: t = "iiit hyderabad"
    return t

_CITY_ALIAS = {"madras": "chennai", "bangalore": "bengaluru", "gurgaon": "gurugram",
               "bombay": "mumbai", "calcutta": "kolkata", "new delhi": "delhi"}
def canon_city(s):
    t = str(s).strip().lower()
    return _CITY_ALIAS.get(t, t)

# recruiter_note is 1090 concatenations of ~25 fixed atoms -> exact keyword counting
NOTE_NEG = ["lukewarm", "struggled with the debugging", "missed two sprint",
            "needed frequent guidance", "was unclear"]
NOTE_POS = ["strong ownership", "led the migration", "ahead of sprint", "1m+ users",
            "mentored two", "excellent system-design", "on-call owner",
            "owned production incidents", "carried the pager", "24x7 on-call"]

# ----------------------------------------------------------------------------
# 2. FEATURE MATRIX
# ----------------------------------------------------------------------------
# Features the debrief says the NEW panel ignores. Built for the Ledger check,
# excluded from the Vault model. (01:39 "forget the old committee's pet preferences")
DEPRECATED = ["f_inst", "f_city", "f_channel", "f_is_referral", "f_is_metro",
              "f_company_type", "f_company_size", "f_degree", "f_gap_years"]

CAT_COLS = {"f_role": "applied_role", "f_degree": "degree", "f_company_type": "company_type",
            "f_company_size": "company_size", "f_channel": "recruitment_channel",
            "f_city": "current_city", "f_inst": "institute", "f_major": "major"}

METROS = {"bengaluru", "mumbai", "delhi", "gurugram", "noida", "hyderabad", "pune", "chennai"}

def build_features(df, cat_levels):
    f = pd.DataFrame(index=df.index)
    # --- merit ---
    f["f_tech"]      = df.technical_assessment.map(p_tech)
    f["f_tech_miss"] = f.f_tech.isna().astype(int)
    f["f_apt"]       = df.aptitude_score.map(p_apt)
    f["f_rating"]    = df.last_rating.map(p_rating)
    f["f_kpi"]       = df.kpi_met.map(p_bool)
    f["f_awards"]    = df.awards.map(p_awards)
    f["f_overtime"]  = (df.overtime_history.astype(str).str.strip().str.lower() == "yes").astype(int)
    # --- tenure / trajectory ---
    f["f_age"]       = pd.to_numeric(df.age, errors="coerce")
    f["f_gradyear"]  = pd.to_numeric(df.graduation_year, errors="coerce")
    f["f_ysg"]       = REF_YEAR - f.f_gradyear
    f["f_exp"]       = df.total_experience.map(p_years)
    f["f_cp_years"]  = df.career_path.map(p_career_years)
    f["f_cp_steps"]  = df.career_path.map(p_career_steps)
    f["f_cp_maxlvl"] = df.career_path.map(p_career_maxlevel)
    f["f_level"]     = df.current_title.map(p_level).astype(float)
    f["f_nemp"]      = pd.to_numeric(df.num_employers, errors="coerce")
    f["f_jobchange"] = df.last_job_change.map(p_jobchange)
    f["f_tenure_avg"]= f.f_cp_years / f.f_cp_steps.replace(0, np.nan)
    f["f_lvl_per_yr"]= f.f_level / (f.f_exp + 1.0)
    f["f_age_at_grad"] = f.f_age - f.f_ysg
    f["f_exp_vs_ysg"]  = f.f_exp - f.f_ysg
    f["f_exp_vs_cp"]   = f.f_exp - f.f_cp_years
    f["f_exp_vs_age"]  = f.f_exp - (f.f_age - 18.0)
    f["f_gap_years"]   = f.f_ysg - f.f_cp_years        # DEPRECATED: the "no gaps" preference
    # --- compensation ---
    f["f_ctc"]       = df.current_ctc.map(p_ctc)
    f["f_ectc"]      = df.expected_ctc.map(p_ctc)
    f["f_ctc_ratio"] = f.f_ectc / f.f_ctc.replace(0, np.nan)
    f["f_ctc_per_yr"]= f.f_ctc / (f.f_exp + 1.0)
    # --- availability / learning ---
    f["f_notice"]    = df.notice_period.map(p_notice)
    f["f_serving"]   = df.notice_period.astype(str).str.contains("Serving", case=False, na=False).astype(int)
    f["f_trainings"] = pd.to_numeric(df.trainings_last_year, errors="coerce")
    f["f_train_hrs"] = pd.to_numeric(df.training_hours, errors="coerce")
    f["f_enrolled"]  = df.currently_enrolled.map({"no_enrollment": 0, "Part time course": 1,
                                                  "Full time course": 2})
    f["f_nskills"]   = df.skills.map(n_items)
    f["f_ncerts"]    = df.certifications.map(n_items)
    # --- recruiter note ---
    note = df.recruiter_note.fillna("").str.lower()
    f["f_note_neg"]  = note.map(lambda s: sum(k in s for k in NOTE_NEG))
    f["f_note_pos"]  = note.map(lambda s: sum(k in s for k in NOTE_POS))
    f["f_note_any"]  = (note.str.len() > 0).astype(int)
    # --- deprecated scalars ---
    f["f_is_referral"] = df.recruitment_channel.isin(["Referral", "Employee Referral"]).astype(int)
    f["f_is_metro"]    = df.current_city.map(canon_city).isin(METROS).astype(int)
    # --- categoricals ---
    for fname, col in CAT_COLS.items():
        src = df[col].map(canon_institute) if col == "institute" else (
              df[col].map(canon_city) if col == "current_city" else df[col])
        f[fname] = pd.Categorical(src, categories=cat_levels[fname])
    return f

def category_levels(train_df):
    lv = {}
    for fname, col in CAT_COLS.items():
        src = train_df[col].map(canon_institute) if col == "institute" else (
              train_df[col].map(canon_city) if col == "current_city" else train_df[col])
        lv[fname] = sorted(set(src.dropna().astype(str)))
    return lv

# ----------------------------------------------------------------------------
# 3. FORENSICS — fabricated profiles and duplicate people
# ----------------------------------------------------------------------------
def fabricated_mask(F):
    """Internal-consistency failures. On train: 561 rows, mean post_hire_score 5.49,
       ZERO in the top 5%. On dev: 87 rows, ZERO of the 150 winners."""
    m = ((F.f_age_at_grad < 18) |
         (F.f_exp > (F.f_age - 20)) |
         (F.f_exp_vs_ysg > 1.5) |
         (F.f_exp_vs_cp > 1.0) |
         (F.f_exp_vs_cp < -8.0) |
         (F.f_gap_years < -4.0) |
         (F.f_gap_years > 10.0))
    return m.fillna(False).to_numpy()

def title_inflation_mask(F, min_tenure_by_level):
    """Seniority the candidate cannot have earned. Thresholds are learned from train:
       the 0.5th percentile of min(exp, ysg) actually observed at each level."""
    tenure = np.minimum(F.f_exp.to_numpy(dtype=float), F.f_ysg.to_numpy(dtype=float))
    need = F.f_level.map(min_tenure_by_level).to_numpy(dtype=float)
    with np.errstate(invalid="ignore"):
        m = tenure < need
    return np.where(np.isnan(tenure) | np.isnan(need), False, m)

def learn_min_tenure(F_train):
    """Minimum tenure ever legitimately seen at each seniority level in the Archive."""
    t = np.minimum(F_train.f_exp, F_train.f_ysg)
    out = {}
    for lvl, grp in t.groupby(F_train.f_level):
        g = grp.dropna()
        out[float(lvl)] = float(np.quantile(g, 0.005)) if len(g) >= 50 else 0.0
    return out

class DSU:
    def __init__(self, n): self.p = list(range(n))
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[rb] = ra

def person_ids(df):
    """Same person entered twice by two recruiters. Union-find over three keys.
       test.csv: 10000 rows -> 9754 people."""
    n = len(df)
    phone = df.phone.astype(str).str.replace(r"\D", "", regex=True).str[-10:]
    email = (df.email.astype(str).str.lower().str.strip()
               .str.replace(r"\.(?=[^@]*@)", "", regex=True))
    name  = (df.full_name.astype(str).str.lower().str.replace(r"[^a-z ]", "", regex=True)
               .map(lambda s: " ".join(sorted(s.split()))))
    namekey = name + "|" + df.graduation_year.astype(str)
    dsu = DSU(n)
    for key in (phone, email, namekey):
        buckets = {}
        for i, v in enumerate(key.to_numpy()):
            if isinstance(v, str) and len(v.strip()) > 2 and "nan" not in v:
                buckets.setdefault(v, []).append(i)
        for idx in buckets.values():
            for j in idx[1:]:
                dsu.union(idx[0], j)
    return np.array([dsu.find(i) for i in range(n)])

# ----------------------------------------------------------------------------
# 4. LOAD
# ----------------------------------------------------------------------------
print("[1/7] loading", flush=True)
train = pd.read_csv("train.csv", dtype=str)
dev   = pd.read_csv("dev.csv",   dtype=str)
test  = pd.read_csv("test.csv",  dtype=str)
winners = set(pd.read_csv("dev_winners.csv", dtype=str).candidate_id)

y = pd.to_numeric(train.post_hire_score, errors="coerce")
levels = category_levels(train)
Ftr = build_features(train, levels)
Fdv = build_features(dev,   levels)
Fte = build_features(test,  levels)

# ----------------------------------------------------------------------------
# 5. TRAIN — drop fabricated rows from the Archive first; they are label noise
#            (mean post_hire_score 5.49, never in the top 5%).
# ----------------------------------------------------------------------------
print("[2/7] forensics", flush=True)
fab_tr = fabricated_mask(Ftr)
fab_dv = fabricated_mask(Fdv)
fab_te = fabricated_mask(Fte)
print(f"      fabricated: train {fab_tr.sum()}  dev {fab_dv.sum()}  test {fab_te.sum()}")
assert fab_tr.sum() > 400, "fabrication rule mis-fired on train"
assert len(winners & set(dev.candidate_id[fab_dv])) == 0, "a real Ledger winner was flagged fake"

keep_tr = ~fab_tr
Xtr, ytr = Ftr[keep_tr], y[keep_tr]

ALL_FEATS   = list(Ftr.columns)
VAULT_FEATS = [c for c in ALL_FEATS if c not in DEPRECATED]   # the new panel's lens
top5_cut = ytr.quantile(0.95)
ybin = (ytr >= top5_cut).astype(int)

REG_P = dict(objective="regression", learning_rate=0.05, num_leaves=63,
             min_child_samples=40, colsample_bytree=0.8, subsample=0.8,
             subsample_freq=1, n_estimators=600, n_jobs=2, verbose=-1)
CLF_P = dict(objective="binary", learning_rate=0.05, num_leaves=31,
             min_child_samples=40, colsample_bytree=0.8, subsample=0.8,
             subsample_freq=1, n_estimators=500, n_jobs=2, verbose=-1)

def fit_blend(feats, seeds=(42, 202, 777)):
    """Rank-average a score regressor and a top-5% classifier, bagged over 3 seeds."""
    regs = [lgb.LGBMRegressor(random_state=s, **REG_P).fit(Xtr[feats], ytr) for s in seeds]
    clfs = [lgb.LGBMClassifier(random_state=s, **CLF_P).fit(Xtr[feats], ybin) for s in seeds]
    def score(F):
        r = np.mean([m.predict(F[feats]) for m in regs], axis=0)
        c = np.mean([m.predict_proba(F[feats])[:, 1] for m in clfs], axis=0)
        rr = pd.Series(r).rank(pct=True).to_numpy()
        cc = pd.Series(c).rank(pct=True).to_numpy()
        return 0.5 * rr + 0.5 * cc, r, c
    return score

print("[3/7] fitting models", flush=True)
score_vault = fit_blend(VAULT_FEATS)
score_full  = fit_blend(ALL_FEATS)

# ----------------------------------------------------------------------------
# 6. LEDGER CHECK — does the pipeline recover a known cycle's top 5%?
# ----------------------------------------------------------------------------
print("[4/7] ledger validation", flush=True)
def recall_at(sc, k=150):
    d = dev.assign(s=sc).copy()
    d.loc[fab_dv, "s"] = -1e9                       # forensics applied to dev too
    pick = set(d.nlargest(k, "s").candidate_id)
    return len(pick & winners)

s_v, _, _ = score_vault(Fdv)
s_f, _, _ = score_full(Fdv)
print(f"      recall@150  vault-lens model : {recall_at(s_v)}/150")
print(f"      recall@150  full  model      : {recall_at(s_f)}/150   (old-panel features included)")

# ----------------------------------------------------------------------------
# 7. THE VAULT — regime-shift layer
# ----------------------------------------------------------------------------
print("[5/7] scoring the vault", flush=True)
base, raw_reg, raw_clf = score_vault(Fte)
z = (base - base.mean()) / (base.std() + 1e-9)       # base merit, in z-units

# ---- 7a. old-boys' network: the handful of schools with a bump beyond merit ----
# Computed, not hardcoded: residual of post_hire_score on merit + role, per school.
merit = Xtr[["f_tech", "f_apt", "f_rating", "f_kpi"]].copy()
merit = merit.fillna(merit.median())
merit = pd.concat([merit, pd.get_dummies(train.loc[keep_tr, "applied_role"], prefix="r")], axis=1)
from sklearn.linear_model import LinearRegression
resid = ytr - LinearRegression().fit(merit, ytr).predict(merit)
inst_tr = train.loc[keep_tr, "institute"].map(canon_institute)
g = pd.DataFrame({"i": inst_tr.to_numpy(), "r": resid.to_numpy()}).groupby("i").r.agg(["mean", "count"])
g = g[g["count"] >= 40]
g["t"] = g["mean"] / (resid.std() / np.sqrt(g["count"]))
OLD_BOYS = list(g[g["t"] >= 3.0].sort_values("mean", ascending=False).head(5).index)
print("      old-boys' network:", OLD_BOYS)
inst_te = test.institute.map(canon_institute)
b_oldboys = inst_te.isin(OLD_BOYS).to_numpy().astype(float) * 0.25   # "a leg up", not a ticket

# ---- 7b. public code contributions: the new fast-track (00:11) ----
# "A handful means nothing ... dozens of merged contributions or more gets fast-tracked,
#  even if the rest of the profile is only good rather than great."
pcc = test.public_code_contributions.map(p_pcc).to_numpy(dtype=float)
lo, hi = 12.0, 48.0                                  # ramp starts at a dozen, saturates at four
with np.errstate(invalid="ignore"):
    ramp = (np.log1p(pcc) - np.log1p(lo)) / (np.log1p(hi) - np.log1p(lo))
b_pcc = np.clip(np.nan_to_num(ramp, nan=0.0), 0.0, 1.0) * 1.00       # up to +1.00 z
# 'not tracked'/blank is missing data, not evidence of zero -> no bonus, no penalty.

# ---- 7c. no-pedigree stars: new colleges that top the assessment (01:21) ----
seen = set(train.institute.map(canon_institute)) | set(dev.institute.map(canon_institute))
is_new_college = (~inst_te.isin(seen)).to_numpy()
ta_te = Fte.f_tech.to_numpy(dtype=float)
role_pct = (Fte.assign(role=test.applied_role.to_numpy())
               .groupby("role").f_tech.rank(pct=True).to_numpy())   # within-role percentile
fits_role = (Fte.f_cp_maxlvl.to_numpy(dtype=float) >= 1.0) & (Fte.f_kpi.fillna(0).to_numpy() >= 0)
b_newcol = (is_new_college & (np.nan_to_num(role_pct) >= 0.90) & fits_role).astype(float) * 0.70

final = z + b_pcc + b_newcol + b_oldboys

# ---- 7d. hard exclusions ----
min_tenure = learn_min_tenure(Ftr[keep_tr])
infl_te = title_inflation_mask(Fte, min_tenure)
notice_te = (Fte.f_notice.to_numpy(dtype=float) > 60.0)
notice_te = np.where(np.isnan(Fte.f_notice.to_numpy(dtype=float)), False, notice_te)

excl = fab_te | infl_te | notice_te
print(f"      excluded: fabricated {fab_te.sum()}  title-inflated {infl_te.sum()}  "
      f"notice>60d {notice_te.sum()}  union {excl.sum()}")
final = np.where(excl, -1e9, final)

# ---- 7e. one row per person ----
pid = person_ids(test)
out = pd.DataFrame({"candidate_id": test.candidate_id, "score": final, "pid": pid})
out = out.sort_values("score", ascending=False).drop_duplicates("pid", keep="first")
print(f"      unique people: {out.pid.nunique()} of {len(test)} rows")

# ----------------------------------------------------------------------------
# 8. WRITE
# ----------------------------------------------------------------------------
print("[6/7] writing submission.csv", flush=True)
short = out.nlargest(K, "score").reset_index(drop=True)
assert len(short) == K, f"expected {K} rows, produced {len(short)}"
assert short.score.min() > -1e8, "an excluded profile reached the shortlist"
assert short.candidate_id.is_unique, "duplicate candidate_id in the shortlist"
sub = pd.DataFrame({"rank": np.arange(1, K + 1), "candidate_id": short.candidate_id})
sub.to_csv("submission.csv", index=False)

# ---- optional: artefacts for the Parakh web app (harmless if unused) ----
if os.environ.get("PARAKH_EXPORT") == "1":
    import json
    Fte.assign(candidate_id=test.candidate_id, score=final, excluded=excl,
               fabricated=fab_te, inflated=infl_te, late=notice_te,
               pcc=pcc, b_pcc=b_pcc, b_newcol=b_newcol, b_oldboys=b_oldboys,
               institute=inst_te, role=test.applied_role, name=test.full_name,
               title=test.current_title).to_json("parakh_export.json", orient="records")
    json.dump({"old_boys": OLD_BOYS, "min_tenure": min_tenure,
               "recall_vault": recall_at(s_v), "recall_full": recall_at(s_f)},
              open("parakh_meta.json", "w"), indent=2)

print(f"[7/7] done — {K} rows written to submission.csv", flush=True)
