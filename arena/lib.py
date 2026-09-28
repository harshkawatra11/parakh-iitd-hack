"""
Parakh Arena agent - pure helpers (no network, no state).

Parsing messy profile fields, the fabrication checks carried over from the
preliminary round, duplicate-person keys, and the fit estimate that mirrors
the arena's own points_note: "points scale with skill match, assessment
margin over the bar, recruiter notes, notice period and salary headroom;
below the bar earns nothing".
"""
import re

REF_YEAR = 2026


# ---------------------------------------------------------------------------
# Defensive field access
# ---------------------------------------------------------------------------
def field(d, *names, default=None):
    """Case-insensitive lookup across several possible key spellings.

    "top.sub" looks one level into a nested dict, e.g. "bar.min_assessment".
    Empty strings count as missing; 0 and False are real values.
    """
    if not isinstance(d, dict):
        return default
    lower = {str(k).lower(): v for k, v in d.items()}
    for name in names:
        if "." in name:
            top, sub = name.split(".", 1)
            nested = lower.get(top.lower())
            if isinstance(nested, dict):
                v = field(nested, sub)
                if v is not None:
                    return v
            continue
        v = lower.get(name.lower())
        if v is not None and not (isinstance(v, str) and v.strip() == ""):
            return v
    return default


def first_number(text, default=None):
    """First number in a messy value: '71/100' -> 71, '45 days' -> 45, 26 -> 26."""
    if text is None or isinstance(text, bool):
        return default
    if isinstance(text, (int, float)):
        return float(text)
    m = re.search(r"-?\d+(?:\.\d+)?", str(text).replace(",", ""))
    return float(m.group()) if m else default


def truthy(v):
    """True for True / 1 / 'true' / 'yes' / a team name; False for False / None / '' / 'false' / 'no' / 0."""
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().lower() not in ("", "false", "no", "0", "none", "null", "unclaimed", "available", "n")


def clamp01(x):
    return max(0.0, min(1.0, float(x)))


# ---------------------------------------------------------------------------
# Field parsers (formats seen in the preliminary round's data)
# ---------------------------------------------------------------------------
def p_pct_score(v):
    """Assessment on a 0-100 scale: 71 | '71/100' | '0.71' | '71%' | '7.1/10' | 'absent' -> None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        return f * 100.0 if f <= 1.0 else f
    s = str(v).strip()
    if s.lower() in ("", "absent", "not taken", "n/a", "na", "-", "none", "null", "pending"):
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*/\s*100", s)
    if m:
        return float(m.group(1))
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*/\s*10", s)
    if m:
        return float(m.group(1)) * 10.0
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*%", s)
    if m:
        return float(m.group(1))
    n = first_number(s)
    if n is None:
        return None
    return n * 100.0 if n <= 1.0 else n


def p_notice_days(v):
    """Notice period in days: 45 | '45 days' | '2 months' | 'Immediate' | 'Serving notice - 30 days'."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    if s in ("", "none", "nan", "null", "-"):
        return None
    if s in ("immediate", "available now", "immediate joiner", "0 days", "immediately"):
        return 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*day", s)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*week", s)
    if m:
        return float(m.group(1)) * 7.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*month", s)
    if m:
        return float(m.group(1)) * 30.0
    if "immediate" in s:
        return 0.0
    return first_number(s)


def p_ctc_lpa(v, usd_to_inr=83.0):
    """Any CTC value -> INR lakh per annum.

    '13.9 LPA' | '13.90L' | 'INR 13.9 lakh' | '₹13,90,000' | '1390000' | '7.53 Cr' | '$22,369' | 26 | 2600000.
    A bare number below 1000 is taken as lakh already; 1000 or more as rupees.
    """
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        return x / 1e5 if x >= 1000 else x
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "-", "n/a", "null"):
        return None
    low = s.lower()
    is_usd = "$" in s or "usd" in low
    m = re.search(r"\d+(?:\.\d+)?", s.replace(",", ""))
    if not m:
        return None
    x = float(m.group())
    if "cr" in low:
        x *= 100.0
    elif "lpa" in low or "lakh" in low or "lac" in low or re.search(r"\d\s*l\b", low):
        pass
    else:
        x = x / 1e5 if x >= 1000 else x
    if is_usd:
        x *= usd_to_inr
    return x


def p_years_exp(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    if s in ("", "nan", "none", "null"):
        return None
    if s.startswith("fresher"):
        return 0.0
    if s.startswith("<1") or s.startswith("< 1"):
        return 0.5
    m = re.search(r"(\d+(?:\.\d+)?)\s*month", s)
    if m and "year" not in s and "yr" not in s:
        return float(m.group(1)) / 12.0
    return first_number(s)


_CP_DUR = re.compile(r"\[(\d+(?:\.\d+)?)\s*mo\]|\((\d+(?:\.\d+)?)\s*(?:y|yr|yrs|years?)\)")


def p_career_years(v):
    """Sum of tenures in a career path string: '[23 mo]' or '(1.2 yrs)' segments."""
    if not isinstance(v, str) or not v.strip():
        return None
    tot = 0.0
    for m in _CP_DUR.finditer(v):
        tot += float(m.group(1)) if m.group(1) else float(m.group(2)) * 12.0
    return tot / 12.0 if tot > 0 else None


def profile_ctc(profile):
    """Expected CTC in LPA from whatever field the profile uses."""
    v = field(profile, "expected_ctc_lpa", "expected_ctc_in_lpa")
    if v is not None:
        return first_number(v)
    return p_ctc_lpa(field(profile, "expected_ctc", "expected_salary", "ctc_expected",
                           "expected_compensation", "ctc"))


def profile_notes(profile):
    v = field(profile, "notes", "recruiter_note", "recruiter_notes", "note", "comments", "free_text")
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v or "")


# ---------------------------------------------------------------------------
# Skills: normalise spellings so overlap actually matches
# ---------------------------------------------------------------------------
_SKILL_SYNONYMS = {
    "js": "javascript", "es6": "javascript", "ecmascript": "javascript",
    "ts": "typescript",
    "reactjs": "react", "react.js": "react", "react js": "react",
    "nodejs": "node.js", "node": "node.js", "node js": "node.js", "express/node": "node.js",
    "vuejs": "vue", "vue.js": "vue",
    "k8s": "kubernetes", "kube": "kubernetes",
    "postgres": "postgresql", "psql": "postgresql", "postgre": "postgresql",
    "golang": "go",
    "py": "python", "python3": "python",
    "sklearn": "scikit-learn", "scikit learn": "scikit-learn", "scikitlearn": "scikit-learn",
    "ab testing": "a/b testing", "a/b tests": "a/b testing", "split testing": "a/b testing",
    "a-b testing": "a/b testing", "experimentation": "a/b testing",
    "rest": "rest apis", "rest api": "rest apis", "restful": "rest apis", "restful apis": "rest apis",
    "restful services": "rest apis", "rest services": "rest apis",
    "micro-services": "microservices", "micro services": "microservices",
    "ci-cd": "ci/cd", "cicd": "ci/cd", "ci cd": "ci/cd", "ci/cd pipelines": "ci/cd",
    "ms excel": "excel", "microsoft excel": "excel",
    "amazon web services": "aws",
    "gcp": "google cloud", "google cloud platform": "google cloud",
    "apache spark": "spark", "pyspark": "spark",
    "apache kafka": "kafka",
    "apache airflow": "airflow",
    "structured query language": "sql", "t-sql": "sql", "tsql": "sql",
    "torch": "pytorch",
    "ml ops": "mlops", "machine learning ops": "mlops",
    "stats": "statistics", "statistical analysis": "statistics",
    "html5": "html", "css3": "css",
    "android sdk": "android",
    "graph ql": "graphql",
    "selenium webdriver": "selenium",
    "linux administration": "linux", "unix/linux": "linux",
}


def _canon_skill(t):
    t = str(t).strip().lower()
    m = re.search(r"\(([^)]+)\)", t)          # 'workflow orchestration (airflow)' -> 'airflow'
    if m:
        t = m.group(1).strip()
    t = re.sub(r"\s+", " ", t)
    return _SKILL_SYNONYMS.get(t, t)


def normalise_skills(raw):
    """'k8s, ReactJS | Node.js' -> {'kubernetes', 'react', 'node.js'}. Never splits on '/' (a/b testing, ci/cd)."""
    if not raw:
        return set()
    parts = raw if isinstance(raw, (list, tuple, set)) else re.split(r"[,;|•]", str(raw))
    return {_canon_skill(p) for p in parts if str(p).strip()}


def skill_overlap(candidate_skills, wanted_skills):
    """Share of the requisition's skills the candidate has, 0..1 (0.5 if the requisition lists none)."""
    c, w = normalise_skills(candidate_skills), normalise_skills(wanted_skills)
    if not w:
        return 0.5
    return len(c & w) / len(w)


def roles_compatible(a, b):
    ka = re.sub(r"[^a-z]", "", str(a or "").lower())
    kb = re.sub(r"[^a-z]", "", str(b or "").lower())
    if not ka or not kb:
        return True
    return ka == kb or ka in kb or kb in ka


# ---------------------------------------------------------------------------
# Fabrication detection (preliminary round: on 20,000 archive rows these rules
# flagged 561 rows averaging 5.49/100 post-hire, and caught zero real winners
# on the held-out ledger cycle)
# ---------------------------------------------------------------------------
def fabrication_flags(profile):
    """List of reasons a profile's own numbers contradict each other; [] = consistent."""
    reasons = []
    age = first_number(field(profile, "age"))
    grad_year = first_number(field(profile, "graduation_year", "grad_year", "year_of_graduation"))
    exp = p_years_exp(field(profile, "total_experience", "experience", "years_of_experience", "exp"))
    cp = p_career_years(field(profile, "career_path", "career_history"))
    ysg = (REF_YEAR - grad_year) if grad_year else None

    if age is not None and ysg is not None and (age - ysg) < 18:
        reasons.append("age_at_graduation_under_18")
    if exp is not None and age is not None and exp > (age - 20):
        reasons.append("experience_exceeds_adult_life")
    if exp is not None and ysg is not None and exp > ysg + 1.5:
        reasons.append("experience_exceeds_years_since_graduation")
    if exp is not None and cp is not None:
        if (exp - cp) > 1.0:
            reasons.append("experience_exceeds_career_history")
        if (exp - cp) < -8.0:
            reasons.append("career_history_overruns_experience")
    if ysg is not None and cp is not None:
        gap = ysg - cp
        if gap < -4.0:
            reasons.append("career_history_overruns_graduation")
        if gap > 10.0:
            reasons.append("unaccounted_years")
    return reasons


def person_key_candidates(profile):
    """Three independent signals that two ids are the same human."""
    keys = []
    phone = re.sub(r"\D", "", str(field(profile, "phone", "phone_number", "mobile") or ""))
    if len(phone) >= 10:
        keys.append("ph:" + phone[-10:])
    email = str(field(profile, "email") or "").strip().lower()
    if "@" in email:
        local, _, dom = email.partition("@")
        keys.append("em:" + local.replace(".", "") + "@" + dom)
    name = re.sub(r"[^a-z ]", "", str(field(profile, "full_name", "name") or "").lower()).strip()
    grad = field(profile, "graduation_year", "grad_year")
    if name and grad:
        keys.append("nm:" + " ".join(sorted(name.split())) + "|" + str(grad))
    return keys


# ---------------------------------------------------------------------------
# Recruiter notes and reference checks
# ---------------------------------------------------------------------------
NOTE_NEG = ("lukewarm", "struggled", "missed two sprint", "frequent guidance", "was unclear",
            "fabricat", "inconsistent", "does not add up", "doesn't add up", "red flag",
            "exaggerat", "plagiar", "no-show", "ghosted")
NOTE_POS = ("strong ownership", "led the migration", "ahead of sprint", "1m+ users", "mentored",
            "system-design", "system design", "on-call owner", "production incidents",
            "carried the pager", "24x7", "strong communicator", "open source", "maintainer",
            "shipped")


def note_sentiment(note):
    s = str(note or "").lower()
    return sum(k in s for k in NOTE_POS) - sum(k in s for k in NOTE_NEG)


REF_BAD = ("fail", "fabricat", "fake", "mismatch", "discrepan", "could not verify", "couldn't verify",
           "could not be verif", "couldn't be verif", "cannot be verif", "unable to be verif",
           "unable to verify", "cannot verify", "not verified", "not be verified", "unverifiable",
           "falsif", "inconsistent", "red flag", "do not hire", "not recommended", "would not rehire",
           "misrepresent", "exaggerat")
REF_OK_NEGATIONS = ("no discrepanc", "no mismatch", "no issues", "no red flag", "no concerns",
                    "no inconsisten", "nothing negative", "not fabricated", "no fabricat",
                    "no failures", "no failed")


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _strings(v)


def reference_check_bad(assess_resp):
    """True when a /assess response says the profile does not hold up.

    Looks at explicit flags first, then only at string VALUES (never keys, so a
    key like 'fabricated': false cannot trigger it), after removing reassuring
    negations such as 'no discrepancies found'.
    """
    if isinstance(assess_resp, dict):
        for k in ("fabricated", "is_fabricated", "flagged", "fraud", "is_fake"):
            if truthy(field(assess_resp, k)):
                return True
        for k in ("reference_ok", "references_ok", "passed", "reference_passed", "verified"):
            v = field(assess_resp, k)
            if isinstance(v, bool) and v is False:
                return True
            if isinstance(v, str) and v.strip().lower() in ("false", "no", "failed", "fail"):
                return True
    text = " ".join(_strings(assess_resp)).lower()
    for ok in REF_OK_NEGATIONS:
        text = text.replace(ok, " ")
    return any(b in text for b in REF_BAD)


# ---------------------------------------------------------------------------
# Requisition bar and candidate fit
# ---------------------------------------------------------------------------
def requisition_bar(req, points_per_hire=10.0):
    headcount = int(first_number(field(req, "headcount", "slots"), default=1) or 1)
    filled = int(first_number(field(req, "filled"), default=0) or 0)
    remaining = first_number(field(req, "remaining", "slots_remaining"))
    remaining = int(remaining) if remaining is not None else max(0, headcount - filled)
    return {
        "req_id": field(req, "req_id", "id"),
        "role": field(req, "role", default="") or "",
        "skills": field(req, "skills", "skills_wanted", default=[]) or [],
        "headcount": headcount,
        "filled": filled,
        "remaining": remaining,
        "min_assessment": first_number(field(req, "min_assessment", "bar.min_assessment")),
        "max_notice_days": first_number(field(req, "max_notice_days", "bar.max_notice_days")),
        "max_ctc_lpa": first_number(field(req, "max_expected_ctc_lpa", "max_ctc_lpa",
                                          "bar.max_expected_ctc_lpa", "max_expected_ctc", "max_ctc")),
        "points": float(points_per_hire),
    }


def fit_score(profile, bar, verified_assessment=None):
    """Returns (quality 0..1 or None, reason, confidence 0..1, detail dict).

    None means a hard filter failed: claimed, wrong role, below the assessment
    bar, notice too long, expected CTC over budget, or fabricated. quality
    mirrors the points_note weights. confidence is how much we trust the
    assessment behind it: verified 0.95, self-reported 0.70, none 0.35.
    """
    if truthy(field(profile, "claimed", "is_claimed")):
        return None, "claimed", 1.0, {}
    prole = field(profile, "role", "applied_role")
    if prole and bar.get("role") and not roles_compatible(prole, bar["role"]):
        return None, "role_mismatch", 1.0, {}

    self_rep = p_pct_score(field(profile, "assessment", "technical_assessment", "assessment_score"))
    if verified_assessment is not None:
        assessment, src = verified_assessment, "verified"
    elif self_rep is not None:
        assessment, src = self_rep, "self"
    else:
        assessment, src = None, "none"
    notice = p_notice_days(field(profile, "notice_period", "notice", "notice_days"))
    ctc = profile_ctc(profile)
    mn, mx_notice, mx_ctc = bar.get("min_assessment"), bar.get("max_notice_days"), bar.get("max_ctc_lpa")

    if mn is not None and assessment is not None and assessment < mn:
        return None, f"below_bar {assessment:.0f}<{mn:.0f}", 0.9, {}
    if mx_notice is not None and notice is not None and notice > mx_notice:
        return None, "notice", 0.9, {}
    if mx_ctc is not None and ctc is not None and ctc > mx_ctc:
        return None, "ctc", 0.9, {}
    flags = fabrication_flags(profile)
    if flags:
        return None, "fabricated:" + ",".join(flags), 0.95, {}

    skill = skill_overlap(field(profile, "skills", "skill_list"), bar.get("skills"))
    if mn is not None and assessment is not None:
        margin = clamp01((assessment - mn) / max(1.0, 100.0 - mn))
        margin_pts = assessment - mn
    else:
        margin, margin_pts = 0.3, None
    notice_s = clamp01(1.0 - notice / mx_notice) if (notice is not None and mx_notice) else 0.5
    ctc_s = clamp01(1.0 - ctc / mx_ctc) if (ctc is not None and mx_ctc) else 0.5
    sent = note_sentiment(profile_notes(profile))
    note_s = clamp01(0.5 + 0.25 * sent)

    quality = 0.35 * skill + 0.35 * margin + 0.10 * notice_s + 0.10 * ctc_s + 0.10 * note_s
    conf = {"verified": 0.95, "self": 0.70, "none": 0.35}[src]
    if sent < 0:
        conf -= 0.15
    detail = {"src": src, "assessment": assessment, "self_reported": self_rep, "margin_pts": margin_pts,
              "skill": round(skill, 2), "notice": notice, "ctc": ctc, "sentiment": sent}
    return quality, "ok", max(0.05, conf), detail
