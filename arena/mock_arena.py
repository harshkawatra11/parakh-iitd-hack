"""
Minimal local mock of the Arena API, for smoke-testing agent.py before
deploy. Not a full simulation: just enough surface (correct shapes, phase
transitions, offer rejections, rate limits, an injected error) to prove the
agent survives a full run without crashing.

    python mock_arena.py &
    ARENA_URL=http://localhost:8123 ARENA_KEY=test PENALTY_FACTOR=0.05 \
        MARKET_POLL_SECONDS=2 timeout 30 python agent.py
"""
import json
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

random.seed(7)
START = time.time()
PHASE_TIMES = {"recon": 90, "market": 240, "closing": 60}  # seconds, accelerated


def phase():
    t = time.time() - START
    if t < PHASE_TIMES["recon"]:
        return "recon"
    if t < PHASE_TIMES["recon"] + PHASE_TIMES["market"]:
        return "market"
    if t < sum(PHASE_TIMES.values()):
        return "closing"
    return "closed"


ROLES = ["Backend Engineer", "Data Scientist", "DevOps / SRE"]
SKILLS = ["python", "sql", "docker", "kubernetes", "react", "go", "aws"]
POOL = []
for i in range(300):
    fabricated = i % 37 == 0
    grad_year = random.randint(2010, 2024)
    real_exp = min(2026 - grad_year, random.randint(1, 12))  # internally consistent
    age = (2026 - grad_year) + random.randint(21, 23)  # years since grad + age at grad
    POOL.append({
        "candidate_id": f"CH-{i:05d}",
        "full_name": f"Person {i}",
        "email": f"person{i}@mail.com",
        "role": random.choice(ROLES),
        "skills": ", ".join(random.sample(SKILLS, 3)),
        "assessment": "not taken" if i % 11 == 0 else f"{random.randint(40, 95)}/100",
        "notice_period": random.choice(["Immediate", "30 days", "60 days", "90 days"]),
        "expected_ctc": f"{random.randint(8, 40)} LPA",
        "age": 90 if fabricated else age,
        "graduation_year": grad_year,
        "total_experience": f"{99 if fabricated else real_exp} years",
        "career_path": f"SDE ({max(1, real_exp)} yrs)",
        "claimed": False,
        "recruiter_note": random.choice(["Strong ownership.", "Struggled with debugging.", ""]),
    })

REQS = {r: {"req_id": r, "role": role, "headcount": 3, "min_assessment": 55,
            "max_notice_days": 60, "skills": random.sample(SKILLS, 2), "points": 10}
        for r, role in zip(["req-be", "req-ds", "req-sre"], ROLES)}

SIGNED = {}
CREDITS = {"used": 0}
BUDGET = 5000


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, status=200, cost=0):
        CREDITS["used"] += cost
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Credits-Remaining", str(max(0, BUDGET - CREDITS["used"])))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        if random.random() < 0.03:  # inject an occasional transient error
            return self._send({"error": "boom"}, 503)
        p = self.path
        if p == "/requisitions":
            return self._send(list(REQS.values()))
        if p == "/ledger":
            return self._send({"phase": phase(), "signed": len(SIGNED),
                                "credits_used": CREDITS["used"], "points": 0, "score": 0})
        if p == "/market":
            return self._send({"pressure": {}, "rank": 1}, cost=2)
        if p.startswith("/search"):
            if phase() == "closed":
                return self._send({"error": "wrong phase"}, 409)
            role = None
            if "role=" in p:
                role = p.split("role=")[1].split("&")[0].replace("%20", " ").replace("+", " ")
            results = [c for c in POOL if not role or c["role"].replace(" ", "") in role.replace(" ", "") or role.replace(" ", "") in c["role"].replace(" ", "")]
            return self._send({"results": results[:100]}, cost=1)
        if p.startswith("/candidate/"):
            cid = p.split("/candidate/")[1]
            c = next((x for x in POOL if x["candidate_id"] == cid), None)
            if not c:
                return self._send({"error": "not found"}, 404)
            return self._send(c, cost=2)
        if p.startswith("/assess/"):
            cid = p.split("/assess/")[1]
            c = next((x for x in POOL if x["candidate_id"] == cid), None)
            if not c:
                return self._send({"error": "not found"}, 404)
            return self._send({"assessment": random.randint(50, 90), "reference_check": "solid"}, cost=25)
        return self._send({"error": "unknown"}, 404)

    def do_POST(self):
        body = self._body()
        if self.path == "/candidates/batch":
            ids = body.get("ids", [])
            got = [c for c in POOL if c["candidate_id"] in ids]
            return self._send({"profiles": got}, cost=60)
        if self.path == "/offer":
            if phase() == "recon":
                return self._send({"error": "offers locked"}, 409)
            cid, req_id = body.get("candidate_id"), body.get("req_id")
            cost = 20 if phase() == "closing" else 10
            if cid in SIGNED:
                return self._send({"accepted": False, "reason": "already_signed"}, cost=cost)
            filled = sum(1 for v in SIGNED.values() if v == req_id)
            if filled >= REQS.get(req_id, {}).get("headcount", 0):
                return self._send({"accepted": False, "reason": "requisition_full"}, cost=cost)
            SIGNED[cid] = req_id
            return self._send({"accepted": True}, cost=cost)
        if self.path == "/reason":
            return self._send({"completion": "ok", "tokens": 50}, cost=1)
        return self._send({"error": "unknown"}, 404)

    def do_DELETE(self):
        if self.path.startswith("/offer/"):
            cid = self.path.split("/offer/")[1]
            SIGNED.pop(cid, None)
            return self._send({"ok": True}, cost=5)
        return self._send({"error": "unknown"}, 404)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("localhost", 8123), H)
    print("mock arena on http://localhost:8123, phases:", PHASE_TIMES, flush=True)
    srv.serve_forever()
