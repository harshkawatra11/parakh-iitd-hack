"""Fast checks of lib.py against formats from the preliminary round and the live requisition schema."""
import lib

REQ = {"req_id": "REQ-01", "role": "Backend Engineer",
       "skills": ["python", "java", "sql", "rest apis", "microservices", "postgresql"],
       "headcount": 9, "min_assessment": 75, "max_notice_days": 60, "max_expected_ctc_lpa": 26,
       "points_note": "points scale with ...", "filled": 0, "remaining": 9}


def main():
    b = lib.requisition_bar(REQ, 10)
    assert b["max_ctc_lpa"] == 26 and b["remaining"] == 9 and b["min_assessment"] == 75 and b["points"] == 10, b

    assert lib.p_pct_score("82/100") == 82
    assert lib.p_pct_score("0.82") == 82
    assert lib.p_pct_score("8.2/10") == 82
    assert lib.p_pct_score("43.0 %") == 43
    assert lib.p_pct_score("absent") is None
    assert lib.p_notice_days("Serving notice - 30 days") == 30
    assert lib.p_notice_days("2 months") == 60
    assert lib.p_notice_days("Immediate joiner") == 0
    assert lib.p_notice_days(45) == 45
    assert abs(lib.p_ctc_lpa("₹30,46,000") - 30.46) < 1e-6
    assert lib.p_ctc_lpa("25.7 lpa") == 25.7
    assert lib.p_ctc_lpa("13.90L") == 13.9
    assert lib.p_ctc_lpa("INR 13.9 lakh") == 13.9
    assert abs(lib.p_ctc_lpa("7.53 Cr") - 753) < 1e-6
    assert abs(lib.p_ctc_lpa("$22,369") - 18.566) < 0.01
    assert lib.p_ctc_lpa(2600000) == 26 and lib.p_ctc_lpa("24") == 24
    assert lib.normalise_skills("Python, PostgreSQL, REST APIs, k8s") == {"python", "postgresql", "rest apis", "kubernetes"}
    assert lib.normalise_skills(["A/B Testing", "sklearn"]) == {"a/b testing", "scikit-learn"}

    good = {"candidate_id": "C1", "role": "Backend Engineer", "skills": "Python, Java, SQL, REST APIs, Postgres",
            "assessment": "88/100", "notice_period": "30 days", "expected_ctc": "20 LPA",
            "notes": "Strong ownership; mentored two juniors.", "claimed": False,
            "age": 29, "graduation_year": 2019, "total_experience": "6 years"}
    q, reason, conf, d = lib.fit_score(good, b)
    assert q is not None and reason == "ok" and d["margin_pts"] == 13 and conf == 0.7, (q, reason, conf, d)
    assert lib.fit_score(dict(good, claimed=True), b)[1] == "claimed"
    assert lib.fit_score(dict(good, claimed="team_x"), b)[1] == "claimed"
    assert lib.fit_score(dict(good, assessment="70/100"), b)[1].startswith("below_bar")
    assert lib.fit_score(dict(good, notice_period="90 days"), b)[1] == "notice"
    assert lib.fit_score(dict(good, expected_ctc="40 LPA"), b)[1] == "ctc"
    assert lib.fit_score(dict(good, role="Data Scientist"), b)[1] == "role_mismatch"
    assert lib.fit_score(dict(good, age=24, total_experience="12 years"), b)[1].startswith("fabricated")
    qv, _, cv, _ = lib.fit_score(good, b, verified_assessment=95)
    assert cv == 0.95 and qv > q
    assert lib.fit_score(good, b, verified_assessment=60)[1].startswith("below_bar")

    assert lib.reference_check_bad({"reference_check": "Employment dates could not be verified"})
    assert not lib.reference_check_bad({"reference_check": "References confirm tenure; no discrepancies found",
                                        "fabricated": False, "verified_assessment": 82})
    assert lib.reference_check_bad({"fabricated": True})
    assert lib.reference_check_bad({"reference_ok": False})
    assert lib.truthy("team_x") and not lib.truthy(False) and not lib.truthy("false") and not lib.truthy(None)
    assert lib.roles_compatible("DevOps/SRE", "DevOps / SRE") and not lib.roles_compatible("Data Scientist", "ML Engineer")
    print("lib tests passed")


if __name__ == "__main__":
    main()
