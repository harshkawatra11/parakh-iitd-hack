"""
Local mock of the Battle Arena API, built to the real schema read live at 14:48
(requisitions with filled/remaining/max_expected_ctc_lpa and no points field;
ledger with points/points_as_of). Offline testing of agent.py only.

    python mock_arena.py        # serves http://127.0.0.1:8123
"""
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

random.seed(7)
START = time.time()
PHASE_TIMES = {"recon": 2, "market": 90, "closing": 30}
BUDGET = 50000
LOCK = threading.Lock()


def phase():
    t = time.time() - START
    if t < PHASE_TIMES["recon"]:
        return "recon"
    if t < PHASE_TIMES["recon"] + PHASE_TIMES["market"]:
        return "market"
    if t < sum(PHASE_TIMES.values()):
        return "closing"
    return "closed"


ROLE_SKILLS = {
    "Backend Engineer": ["python", "java", "sql", "rest apis", "microservices", "postgresql"],
    "Data Scientist": ["python", "statistics", "scikit-learn", "sql", "pandas", "a/b testing"],
    "DevOps / SRE": ["linux", "kubernetes", "terraform", "aws", "ci/cd", "docker"],
}
NOTE = ("points scale with skill match, assessment margin over the bar, recruiter notes, "
        "notice period and salary headroom; below the bar earns nothing")
REQS = [{"req_id": f"REQ-0{i + 1}", "role": role, "skills": skills, "headcount": 4,
         "min_assessment": 70, "max_notice_days": 60, "max_expected_ctc_lpa": 26, "points_note": NOTE}
        for i, (role, skills) in enumerate(ROLE_SKILLS.items())]
REQ_BY_ID = {r["req_id"]: r for r in REQS}

EXTRA = ["git", "excel", "go", "k8s", "Postgres", "REST", "sklearn"]
NOTES = ["Strong ownership; drove a cross-team initiative.", "Mentored two junior engineers.",
         "Reference check was lukewarm about teamwork.", "Struggled with the debugging exercise.", "", ""]
NOTICES = {"Immediate": 0, "15 days": 15, "30 days": 30, "60 days": 60, "90 days": 90}

POOL = {}
for i in range(1500):
    cid = f"C-{i:05d}"
    role = random.choice(list(ROLE_SKILLS))
    grad = random.randint(2010, 2024)
    exp = min(2026 - grad, random.randint(1, 12))
    age = (2026 - grad) + random.randint(21, 23)
    true_score = random.randint(45, 98)
    fab = (i % 23 == 0)
    self_score = min(100, true_score + (25 if fab else random.choice([0, 0, 2, 6])))
    ctc = random.randint(8, 34)
    POOL[cid] = {
        "candidate_id": cid, "name": f"Person {i}", "email": f"person{i}@mail.com",
        "role": role, "city": random.choice(["Pune", "Delhi", "Bengaluru"]),
        "experience": f"{exp} years", "total_experience": f"{exp} years",
        "skills": ", ".join(random.sample(ROLE_SKILLS[role], 3) + random.sample(EXTRA, 2)),
        "assessment": "not taken" if i % 13 == 0 else f"{self_score}/100",
        "notice_period": random.choice(list(NOTICES)),
        "expected_ctc": random.choice([f"{ctc} LPA", f"₹{ctc * 100000:,}"]),
        "age": 19 if (fab and i % 2 == 0) else age, "graduation_year": grad,
        "notes": random.choice(NOTES), "claimed": False,
        "_true": true_score, "_fab": fab, "_ctc": ctc,
    }
for i in range(0, 60, 3):                     # the same person under a second id
    src = POOL[f"C-{i:05d}"]
    dup = dict(src)
    dup["candidate_id"] = f"D-{i:05d}"
    dup["name"] = src["name"].upper()
    POOL[dup["candidate_id"]] = dup

OURS = {}                                      # candidate_id -> req_id held by the agent under test
USED = {"credits": 0, "calls": 0}
POINTS = {"value": 0.0, "as_of": time.time()}


def public(c):
    return {k: v for k, v in c.items() if not k.startswith("_")}


def person(c):
    return c["email"].lower()


def points_for(c, req):
    if c["_fab"] or c["_true"] < req["min_assessment"]:
        return 0.0
    notice = NOTICES[c["notice_period"]]
    if notice > req["max_notice_days"] or c["_ctc"] > req["max_expected_ctc_lpa"]:
        return 0.0
    skills = {s.strip().lower() for s in c["skills"].split(",")}
    skill = len(skills & set(req["skills"])) / len(req["skills"])
    margin = (c["_true"] - req["min_assessment"]) / (100 - req["min_assessment"])
    return round(10 * (0.4 + 0.25 * skill + 0.25 * margin + 0.05 * (1 - notice / 60)
                       + 0.05 * (1 - c["_ctc"] / 26)), 2)


def refresher():
    while True:
        time.sleep(20)
        with LOCK:
            POINTS["value"] = round(sum(points_for(POOL[c], REQ_BY_ID[r]) for c, r in OURS.items()), 2)
            POINTS["as_of"] = time.time()


def rival():
    ids = list(POOL)
    while True:
        time.sleep(0.4)
        if phase() in ("market", "closing"):
            with LOCK:
                c = POOL[random.choice(ids)]
                if not c["claimed"]:
                    c["claimed"] = True


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, obj, status=200, cost=0):
        with LOCK:
            if cost and cost > BUDGET - USED["credits"]:
                status, obj, cost = 429, {"error": "credits_exhausted"}, 0
            USED["credits"] += cost
            if cost:
                USED["calls"] += 1
            remaining = BUDGET - USED["credits"]
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Credits-Remaining", str(remaining))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return {}

    def do_GET(self):
        u = urlsplit(self.path)
        qs = parse_qs(u.query)
        if u.path == "/health":
            return self.send({"ok": True, "phase": phase()})
        if u.path == "/ledger":
            with LOCK:
                led = {"team": "mock", "credits_used": USED["credits"],
                       "credits_remaining": BUDGET - USED["credits"], "calls": USED["calls"],
                       "signed": len(OURS), "points": POINTS["value"], "points_as_of": POINTS["as_of"],
                       "phase": phase()}
            led["score"] = round(led["points"] - led["credits_used"] * 0.05, 2)
            return self.send(led)
        if u.path == "/requisitions":
            out = []
            with LOCK:
                for r in REQS:
                    filled = sum(1 for v in OURS.values() if v == r["req_id"])
                    out.append(dict(r, filled=filled, remaining=r["headcount"] - filled))
            return self.send(out)
        if phase() == "closed":
            return self.send({"error": "wrong_phase"}, 409)
        if random.random() < 0.02:
            return self.send({"error": "temporary"}, 503)
        if u.path == "/search":
            role = (qs.get("role") or [None])[0]
            page = int((qs.get("page") or ["0"])[0])
            size = min(100, int((qs.get("size") or ["100"])[0]))
            hits = [c for c in POOL.values() if not role or c["role"] == role]
            chunk = hits[page * size:(page + 1) * size]
            summ = [{k: c[k] for k in ("candidate_id", "name", "role", "city", "experience", "skills")}
                    for c in chunk]
            return self.send({"results": summ, "page": page, "total": len(hits)}, cost=1)
        if u.path.startswith("/candidate/"):
            c = POOL.get(unquote(u.path.split("/candidate/", 1)[1]))
            if not c:
                return self.send({"error": "not_found"}, 404)
            return self.send(public(c), cost=2)
        if u.path.startswith("/assess/"):
            c = POOL.get(unquote(u.path.split("/assess/", 1)[1]))
            if not c:
                return self.send({"error": "not_found"}, 404)
            ref = ("Employment dates could not be verified; title history inconsistent." if c["_fab"]
                   else "References confirm role and tenure; no discrepancies found.")
            return self.send({"candidate_id": c["candidate_id"], "verified_assessment": c["_true"],
                              "reference_check": ref}, cost=25)
        if u.path == "/market":
            return self.send({"phase": phase(), "rank": 1, "leader_score": 0}, cost=2)
        return self.send({"error": "not_found"}, 404)

    def do_POST(self):
        u = urlsplit(self.path)
        b = self.body()
        if phase() == "closed":
            return self.send({"error": "wrong_phase"}, 409)
        if u.path == "/candidates/batch":
            ids = b.get("ids") or []
            if not ids or len(ids) > 50:
                return self.send({"error": "bad_request"}, 422)
            return self.send({"profiles": [public(POOL[i]) for i in ids if i in POOL]}, cost=60)
        if u.path == "/offer":
            if phase() == "recon":
                return self.send({"error": "offers locked in recon"}, 409)
            cost = 20 if phase() == "closing" else 10
            cid, rid = b.get("candidate_id"), b.get("req_id")
            c, r = POOL.get(cid), REQ_BY_ID.get(rid)
            if not c or not r:
                return self.send({"error": "not_found"}, 404)
            with LOCK:
                if OURS.get(cid) == rid:
                    result = {"accepted": True, "already_yours": True}
                elif c["claimed"]:
                    result = {"accepted": False, "reason": "already_signed"}
                elif any(person(POOL[o]) == person(c) for o in OURS):
                    result = {"accepted": False, "reason": "same_person_already_signed"}
                elif c["role"] != r["role"]:
                    result = {"accepted": False, "reason": "role_mismatch"}
                elif sum(1 for v in OURS.values() if v == rid) >= r["headcount"]:
                    result = {"accepted": False, "reason": "requisition_full"}
                else:
                    OURS[cid] = rid
                    c["claimed"] = True
                    result = {"accepted": True}
            return self.send(result, cost=cost)
        return self.send({"error": "not_found"}, 404)

    def do_DELETE(self):
        u = urlsplit(self.path)
        if u.path.startswith("/offer/"):
            cid = unquote(u.path.split("/offer/", 1)[1])
            with LOCK:
                OURS.pop(cid, None)
            return self.send({"released": True}, cost=5)
        return self.send({"error": "not_found"}, 404)


if __name__ == "__main__":
    threading.Thread(target=refresher, daemon=True).start()
    threading.Thread(target=rival, daemon=True).start()
    ThreadingHTTPServer.allow_reuse_address = False   # a second copy fails loudly instead of sharing the port
    srv = ThreadingHTTPServer(("127.0.0.1", 8123), H)
    print("mock arena on http://127.0.0.1:8123 phases", PHASE_TIMES, flush=True)
    srv.serve_forever()
