"""
Parakh Arena agent - shared helpers.

Everything here is pure and side-effect free: field parsing, fabrication
detection, duplicate-person resolution, and the fit/value scoring that turns
a messy profile plus an open requisition into an expected-points number.

The arena's exact JSON field names were not available before kick-off, so
every lookup goes through field() with a list of plausible aliases rather
than a single hardcoded key. If a field genuinely is not there, the code
degrades gracefully (treats it as unknown, not as zero or false).
"""
import re
import math


# ---------------------------------------------------------------------------
# Defensive field access
# ---------------------------------------------------------------------------
def field(d, *names, default=None):
    """Case-insensitive lookup across several possible key spellings.

    Also checks one level of nested dicts commonly seen in requisition bars,
    e.g. field(req, "min_assessment", "bar.min_assessment").
    """
    if not isinstance(d, dict):
        return default
    lower = {str(k).lower(): v for k, v in d.items()}
    for name in names:
        if "." in name:
            top, sub = name.split(".", 1)
            nested = lower.get(top.lower())
            if isinstance(nested, dict):
                v = field(nested, sub, default=None)
                if v is not None:
                    return v
            continue
        if name.lower() in lower and lower[name.lower()] is not None:
            return lower[name.lower()]
    return default


def first_number(text, default=None):
    """First number in a messy string: '71/100' -> 71, '45 days' -> 45."""
    if text is None:
        return default
    if isinstance(text, (int, float)):
        return float(text)
    m = re.search(r"-?\d+(\.\d+)?", str(text))
    return float(m.group()) if m else default


# ---------------------------------------------------------------------------
# Field parsers (patterns proven in the preliminary round's train/test data)
# ---------------------------------------------------------------------------
def p_pct_score(v, scale100=True):
    """Assessment-style score: '71', '71/100', '0.71', '71%'."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        return f * 100 if scale100 and f <= 1.0 else f
    s = str(v).strip()
    if s.lower() in ("", "absent", "not taken", "n/a", "na", "-"):
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*/\s*100", s)
    if m:
        return float(m.group(1))
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*%", s)
    if m:
        return float(m.group(1))
    try:
        f = float(s)
    except ValueError:
        return None
    return f * 100 if scale100 and f <= 1.0 else f


def p_notice_days(v):
    s = str(v).strip().lower()
    if s in ("", "none", "nan"):
        return None
    if s in ("immediate", "available now", "immediate joiner", "0 days"):
        return 0.0
    m = re.search(r"(\d+)\s*day", s)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)\s*month", s)
    if m:
        return float(m.group(1)) * 30.0
    return first_number(s)


def p_ctc_lpa(v, usd_to_inr=83.0):
    """Any CTC-like value normalised to INR lakh per annum."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        return x / 1e5 if x > 1000 else x  # bare rupees vs already-lakh
    s = str(v).strip().replace(",", "")
    if not s or s.lower() in ("nan", "none", "-"):
        return None
    is_usd = "$" in s
    s2 = s.replace("₹", "").replace("$", "").replace("INR", "").replace("Rs.", "").replace("Rs", "").strip()
    low = s2.lower()
    m = re.match(r"(\d+(?:\.\d+)?)", s2)
    if not m:
        return None
    x = float(m.group(1))
    if "cr" in low:
        x *= 100.0
    elif "lpa" in low or "lakh" in low or low.endswith("l"):
        pass
    else:
        x /= 1e5
    if is_usd:
        x *= usd_to_inr
    return x


def p_years_exp(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    if s in ("", "nan", "none"):
        return None
    if s.startswith("fresher"):
        return 0.0
    if s.startswith("<1"):
        return 0.5
    m = re.search(r"(\d+(?:\.\d+)?)\s*month", s)
    if m:
        return float(m.group(1)) / 12.0
    return first_number(s)


_CP_SPLIT = re.compile(r"\s*(?:->|>|→|\|)\s*")
_CP_DUR = re.compile(r"\[(\d+(?:\.\d+)?)\s*mo\]|\((\d+(?:\.\d+)?)\s*(?:y|yr|yrs)\)")


def p_career_years(v):
    if not isinstance(v, str) or not v.strip():
        return None
    tot = 0.0
    for m in _CP_DUR.finditer(v):
        tot += float(m.group(1)) if m.group(1) else float(m.group(2)) * 12.0
    return tot / 12.0 if tot > 0 else None


# ---------------------------------------------------------------------------
# Skills: normalise spellings so overlap actually matches
# ---------------------------------------------------------------------------
_SKILL_SYNONYMS = {
    "js": "javascript", "javascript": "javascript", "ts": "typescript",
    "typescript": "typescript", "reactjs": "react", "react.js": "react",
    "react": "react", "vuejs": "vue", "vue.js": "vue", "nodejs": "node",
    "node.js": "node", "k8s": "kubernetes", "kubernetes": "kubernetes",
    "postgres": "postgresql", "psql": "postgresql", "postgresql": "postgresql",
    "golang": "go", "go": "go", "py": "python", "python": "python",
    "ml": "machine learning", "machine-learning": "machine learning",
    "ai": "artificial intelligence", "gcp": "google cloud",
    "google cloud platform": "google cloud", "aws": "aws",
    "amazon web services": "aws", "azure": "azure", "sql": "sql",
    "t-sql": "sql", "mysql": "mysql", "mongo": "mongodb", "mongodb": "mongodb",
    "cicd": "ci/cd", "ci-cd": "ci/cd", "ci/cd": "ci/cd",
    "tensorflow": "tensorflow", "pytorch": "pytorch",
}


def normalise_skills(raw):
    """'k8s, ReactJS | Node.js' -> {'kubernetes', 'react', 'node'}."""
    if not raw:
        return set()
    if isinstance(raw, list):
        parts = raw
    else:
        parts = re.split(r"[,;|/]", str(raw))
    out = set()
    for p in parts:
        t = p.strip().lower()
        if not t:
            continue
        out.add(_SKILL_SYNONYMS.get(t, t))
    return out


def skill_overlap(candidate_skills, wanted_skills):
    c, w = normalise_skills(candidate_skills), normalise_skills(wanted_skills)
    if not w:
        return 0.5  # requisition doesn't specify skills: neutral
    return len(c & w) / max(len(w), 1)


# ---------------------------------------------------------------------------
# Fabrication detection (thresholds proven in the preliminary round: on the
# 20,000-row historical Archive these rules flagged 561 rows averaging a
# post-hire score of 5.49/100, and zero of the confirmed top-5% winners on
# the held-out Ledger cycle were ever caught by them)
# ---------------------------------------------------------------------------
REF_YEAR = 2026


def fabrication_flags(profile):
    """Returns a list of reasons; empty list = internally consistent."""
    reasons = []
    age = first_number(field(profile, "age"))
    grad_year = first_number(field(profile, "graduation_year", "grad_year"))
    exp = p_years_exp(field(profile, "total_experience", "experience", "exp"))
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
    """Three independent signals for 'is this the same human as another row'."""
    keys = []
    phone = re.sub(r"\D", "", str(field(profile, "phone", "phone_number") or ""))
    if len(phone) >= 10:
        keys.append("ph:" + phone[-10:])
    email = str(field(profile, "email") or "").strip().lower()
    if "@" in email:
        local, _, dom = email.partition("@")
        keys.append("em:" + local.replace(".", "") + "@" + dom)
    name = str(field(profile, "full_name", "name") or "").strip().lower()
    name = re.sub(r"[^a-z ]", "", name)
    grad = field(profile, "graduation_year", "grad_year")
    if name:
        keys.append("nm:" + " ".join(sorted(name.split())) + "|" + str(grad))
    return keys


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


# ---------------------------------------------------------------------------
# Valuation: does this candidate meet this requisition, and how well
# ---------------------------------------------------------------------------
def requisition_bar(req):
    return {
        "min_assessment": first_number(field(req, "min_assessment", "bar.min_assessment", "bar_min_assessment")),
        "max_notice_days": first_number(field(req, "max_notice_days", "bar.max_notice_days", "bar_max_notice_days")),
        "max_ctc_lpa": p_ctc_lpa(field(req, "max_ctc", "bar.max_ctc", "budget", "max_expected_ctc")),
        "skills": field(req, "skills", "skills_wanted", default=[]),
        "role": field(req, "role"),
        "points": first_number(field(req, "points", "points_per_hire", "score_per_hire"), default=1.0),
        "headcount": int(first_number(field(req, "headcount", "slots"), default=1)),
    }


def fit_score(profile, bar, verified_assessment=None):
    """Returns (fit in [0,1] or None if a hard filter fails, notes, confidence).

    confidence is how sure we are that `fit` is right: high when the score
    came from a verified /assess call, low when it's the profile's own
    unverified self-report, and lowest when no assessment is present at all.
    """
    if field(profile, "claimed") in (True, "true", "True", 1):
        return None, ["already_claimed"], 1.0

    assessment = verified_assessment
    src = "verified"
    if assessment is None:
        assessment = p_pct_score(field(profile, "assessment", "technical_assessment"))
        src = "self_reported"
    notice = p_notice_days(field(profile, "notice_period"))
    ctc = p_ctc_lpa(field(profile, "expected_ctc", "expected_salary"))

    if bar["min_assessment"] is not None and assessment is not None and assessment < bar["min_assessment"]:
        return None, [f"assessment {assessment} below bar {bar['min_assessment']}"], 0.9
    if bar["max_notice_days"] is not None and notice is not None and notice > bar["max_notice_days"]:
        return None, [f"notice {notice}d over bar {bar['max_notice_days']}d"], 0.9
    if bar["max_ctc_lpa"] is not None and ctc is not None and ctc > bar["max_ctc_lpa"]:
        return None, [f"expected ctc {ctc} over budget {bar['max_ctc_lpa']}"], 0.9

    reasons = fabrication_flags(profile)
    if reasons:
        return None, ["fabricated:" + ",".join(reasons)], 0.95

    skill_fit = skill_overlap(field(profile, "skills"), bar["skills"])
    margin = 0.5
    if bar["min_assessment"] and assessment is not None:
        margin = min(1.0, max(0.0, (assessment - bar["min_assessment"]) / 30.0 + 0.5))
    confidence = 0.65 if src == "self_reported" else 0.95
    if assessment is None:
        confidence = 0.35
        margin = 0.4

    quality = min(1.0, max(0.0, 0.55 * margin + 0.35 * skill_fit + 0.10))
    notes = [f"src={src}", f"skill_fit={skill_fit:.2f}", f"margin={margin:.2f}", f"conf={confidence:.2f}"]
    return quality, notes, confidence


NOTE_NEG = ["lukewarm", "struggled", "missed two sprint", "frequent guidance", "unclear"]
NOTE_POS = ["strong ownership", "led the migration", "ahead of sprint", "1m+ users",
            "mentored", "excellent system-design", "on-call owner", "production incidents",
            "carried the pager", "24x7"]


def note_sentiment(note):
    s = str(note or "").lower()
    pos = sum(k in s for k in NOTE_POS)
    neg = sum(k in s for k in NOTE_NEG)
    return pos - neg
