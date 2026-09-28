"""
Parakh Arena agent - Team IdeaForge (Innov8 4.0 Grand Finale, "The Battle Arena").

Runs on the team laptop against the live arena:
    ARENA_URL=https://innov8-battle-arena.onrender.com  ARENA_KEY=<slip key>  python agent.py

Core rule: a credit is worth PENALTY_FACTOR points (score = points - credits x PF).
Every paid call and every offer happens only when the points it is expected
to earn beat its price. Unspent credits cost nothing.

Each loop (every LOOP_SECONDS):
    /ledger (free)        phase, credits, points -> recalibrate points-per-hire
    /requisitions (free)  server-truth remaining slots per requisition
    for each requisition with open slots:
        queue empty -> restock: next search pages, rank summaries by skill match,
                       fetch the best profiles (batch when >= 30), forensics,
                       hard bar filters, queue sorted by expected points
        pop best -> refresh if stale (60 s in closing) -> assess -> offer if EV > 0
        -> handle every rejection reason
    /market every MARKET_EVERY_SECONDS (logged)

Safety: every exception is caught and logged, never fatal; state is
checkpointed after every signing so a restart never double-offers; a
heartbeat file stops two copies of the agent from running at once.
"""
import json
import os
import sys
import time
import traceback

from arena_client import Arena, Exhausted, WrongPhase
import lib

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_PATH = os.environ.get("CHECKPOINT_PATH", os.path.join(HERE, "checkpoint.json"))
LOG_PATH = os.environ.get("LOG_PATH", os.path.join(HERE, "arena_log.jsonl"))
CONFIG_PATH = os.environ.get("CONFIG_PATH", os.path.join(HERE, "config.json"))
HEARTBEAT_PATH = os.environ.get("HEARTBEAT_PATH", os.path.join(HERE, "agent.heartbeat"))

DEFAULTS = {
    "PENALTY_FACTOR": 0.05,
    "POINTS_PER_HIRE": 10.0,
    "LOOP_SECONDS": 10.0,
    "MARKET_EVERY_SECONDS": 300.0,
    "HEARTBEAT_LOG_SECONDS": 120.0,
    "PAGES_PER_RESTOCK": 5.0,
    "MAX_PAGES_PER_REQ": 120.0,
    "BATCH_TOP_PER_RESTOCK": 50.0,
    "BATCH_MIN_IDS": 30.0,
    "DRY_LIMIT": 4.0,
    "DRY_RESET_SECONDS": 900.0,
    "ASSESS_SKIP_MARGIN": 15.0,
    "ASSESS_ALWAYS": 1.0,
    "PROFILE_STALE_SECONDS": 180.0,
    "CLOSING_STALE_SECONDS": 60.0,
    "MIN_CREDITS_FLOOR": 200.0,
    "SPEND_CAP": 30000.0,
    "UPGRADE_ENABLED": 0.0,
    "UPGRADE_MAX_OLD_QUALITY": 0.55,
    "UPGRADE_MIN_NEW_QUALITY": 0.70,
    "UPGRADE_MIN_DELTA": 0.25,
    "UPGRADE_MIN_SELF_MARGIN": 12.0,
    "UPGRADE_MAX_SWAPS": 116.0,
    "UPGRADE_ASSESS_PER_PASS": 6.0,
    "UPGRADE_PAGES_PER_RESTOCK": 20.0,
    "UPGRADE_MIN_SLOPE": 8.0,
}

LIST_KEYS = ("results", "candidates", "profiles", "items", "data", "requisitions", "hits")


# ---------------------------------------------------------------------------
# Config and logging
# ---------------------------------------------------------------------------
def load_config():
    """config.json overrides DEFAULTS; environment variables override both. Re-read every loop."""
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    for k in DEFAULTS:
        if k in os.environ:
            try:
                cfg[k] = float(os.environ[k])
            except ValueError:
                pass
    for k in DEFAULTS:
        try:
            cfg[k] = float(cfg[k])
        except (TypeError, ValueError):
            cfg[k] = DEFAULTS[k]
    return cfg


def log(event, **kw):
    """One JSON line per decision, to stdout and arena_log.jsonl. ASCII-only, so the Windows console never chokes."""
    rec = {"t": time.strftime("%H:%M:%S"), "event": event}
    rec.update(kw)
    line = json.dumps(rec, default=str)
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Response-shape helpers (the exact JSON shapes were not published)
# ---------------------------------------------------------------------------
def extract_list(resp):
    """A list of dict records from any of the common response shapes."""
    if isinstance(resp, list):
        return [x for x in resp if isinstance(x, dict)]
    if isinstance(resp, dict):
        for k in LIST_KEYS:
            v = resp.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
            if isinstance(v, dict) and v and all(isinstance(x, dict) for x in v.values()):
                return list(v.values())
        if resp and all(isinstance(x, dict) for x in resp.values()):
            return list(resp.values())
    return []


def unwrap_profile(p):
    """{'candidate': {...}, 'claimed': true} -> the inner profile with top-level extras merged in."""
    if not isinstance(p, dict):
        return {}
    for k in ("candidate", "profile", "data"):
        inner = p.get(k)
        if isinstance(inner, dict) and inner:
            merged = dict(inner)
            for top_key, top_val in p.items():
                if top_key != k and top_key not in merged:
                    merged[top_key] = top_val
            return merged
    return p


def extract_verified(a):
    """Verified assessment score (0-100) from a /assess response, or None."""
    if not isinstance(a, dict):
        return None
    for key in ("verified_assessment", "verified_score", "assessment", "score",
                "technical_assessment", "assessment_score"):
        v = lib.field(a, key)
        if isinstance(v, dict):
            v = lib.field(v, "score", "value", "verified", "verified_score")
        s = lib.p_pct_score(v)
        if s is not None:
            return s
    return None


# ---------------------------------------------------------------------------
# Measured costs and persistent state
# ---------------------------------------------------------------------------
class Costs:
    """Credit price per endpoint, measured from X-Credits-Remaining around every paid call."""
    DEFAULT = {"search": 1, "candidate": 2, "batch": 60, "assess": 25, "offer": 10,
               "release": 5, "market": 2}

    def __init__(self):
        self.observed = dict(self.DEFAULT)

    def spend(self, arena, endpoint, fn, *args, **kwargs):
        before = arena.credits_remaining
        result = fn(*args, **kwargs)
        after = arena.credits_remaining
        if before is not None and after is not None and before >= after:
            self.observed[endpoint] = before - after
        return result

    def get(self, endpoint):
        return self.observed.get(endpoint, self.DEFAULT.get(endpoint, 1))


class State:
    """Everything that must survive a crash or restart."""

    def __init__(self):
        self.signed = {}        # candidate_id -> req_id
        self.signed_at = {}     # candidate_id -> epoch seconds
        self.dead = set()       # candidate ids never to spend on again
        self.person_keys = set()
        self.next_page = {}     # req_id -> next search page
        self.dry_restocks = {}  # req_id -> consecutive restocks with nothing eligible
        self.held_quality = {}  # candidate_id -> quality of a current hire (drives upgrades)

    def save(self):
        data = {"signed": self.signed, "signed_at": self.signed_at, "dead": sorted(self.dead),
                "person_keys": sorted(self.person_keys), "next_page": self.next_page,
                "dry_restocks": self.dry_restocks, "held_quality": self.held_quality}
        tmp = CHECKPOINT_PATH + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, CHECKPOINT_PATH)
        except OSError as e:
            log("checkpoint_save_failed", error=str(e))

    def load(self):
        try:
            with open(CHECKPOINT_PATH, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            log("checkpoint_absent")
            return
        self.signed = dict(d.get("signed", {}))
        self.signed_at = {k: float(v) for k, v in d.get("signed_at", {}).items()}
        self.dead = set(d.get("dead", []))
        self.person_keys = set(d.get("person_keys", []))
        self.next_page = {k: int(v) for k, v in d.get("next_page", {}).items()}
        self.dry_restocks = {k: int(v) for k, v in d.get("dry_restocks", {}).items()}
        self.held_quality = {k: float(v) for k, v in d.get("held_quality", {}).items()}
        log("checkpoint_loaded", signed=len(self.signed), dead=len(self.dead), next_page=self.next_page)


# ---------------------------------------------------------------------------
# The agent
# ---------------------------------------------------------------------------
class Agent:
    def __init__(self):
        self.cfg = load_config()
        self.arena = Arena()
        self.costs = Costs()
        self.state = State()
        self.state.load()
        self.queues = {}        # req_id -> list of candidate entries, best first
        self.backlog = {}       # req_id -> summaries found but not yet profiled
        self.seen = set()       # summary ids already queued for profiling this run
        self.first_seen = set()
        self.points_per_hire = self.cfg["POINTS_PER_HIRE"]
        self.assess_always = self.cfg["ASSESS_ALWAYS"] >= 1
        self.last_points_as_of = None
        self.last_phase = None
        self.phase = "unknown"
        self.last_market_at = 0.0
        self.last_heartbeat_log = 0.0
        self.last_heartbeat_write = 0.0
        self.last_dry_reset = time.time()
        self.budget_total = None
        self.exhausted = False
        self.stats = {"signed": 0, "rejected": 0, "assessed": 0, "assess_rejected": 0,
                      "restocks": 0, "refresh_rejected": 0, "upgrades": 0, "upgrade_offer_rejected": 0}
        self.swaps = 0
        self.swap_log = []          # (epoch, quality gained) per completed upgrade
        self.upgrade_off = False    # set when the measured points slope says upgrades don't pay
        self.prev_points = None
        self.prev_points_asof = None
        self.backfill_held_quality()

    def backfill_held_quality(self):
        """Quality of each current hire, recovered from signed/upgraded log lines when the checkpoint predates it."""
        if all(c in self.state.held_quality for c in self.state.signed):
            return
        try:
            with open(LOG_PATH, encoding="utf-8") as f:
                for line in f:
                    if '"event": "signed"' not in line and '"event": "upgraded"' not in line:
                        continue
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    cid, q = r.get("cid"), r.get("quality")
                    if cid in self.state.signed and q is not None:
                        self.state.held_quality[cid] = float(q)
        except OSError:
            pass
        log("held_quality_backfilled", known=len(self.state.held_quality), signed=len(self.state.signed))

    # ---- small utilities --------------------------------------------------
    @property
    def pf(self):
        return self.cfg["PENALTY_FACTOR"]

    def dump_once(self, name, obj):
        """Log the first real response of each endpoint once, so field names can be checked from the log."""
        if name not in self.first_seen:
            self.first_seen.add(name)
            log("first_response", endpoint=name, sample=json.dumps(obj, default=str)[:2500])

    def touch_heartbeat(self, force=False):
        now = time.time()
        if not force and now - self.last_heartbeat_write < 5:
            return
        self.last_heartbeat_write = now
        try:
            with open(HEARTBEAT_PATH, "w", encoding="utf-8") as f:
                f.write(str(now))
        except OSError:
            pass

    def call(self, endpoint, fn, *args, **kwargs):
        """Every paid call goes through here: cost measured, first response logged, errors contained."""
        self.touch_heartbeat()
        try:
            result = self.costs.spend(self.arena, endpoint, fn, *args, **kwargs)
        except (Exhausted, WrongPhase):
            raise
        except Exception as e:
            log("call_failed", endpoint=endpoint, error=str(e)[:300])
            return None
        self.dump_once(endpoint, result)
        return result

    def can_spend(self, cost):
        cr = self.arena.credits_remaining
        if cr is None:
            return True
        if cr - cost < self.cfg["MIN_CREDITS_FLOOR"]:
            return False
        if self.budget_total is not None and (self.budget_total - cr) + cost > self.cfg["SPEND_CAP"]:
            return False
        return True

    def est_points(self, e):
        return self.points_per_hire * (0.5 + 0.5 * e["quality"])

    # ---- building queues ---------------------------------------------------
    def evaluate(self, cid, prof, bar, reasons=None):
        """Profile -> queue entry, or None (and the id retired) if it fails any hard check."""
        q, reason, conf, detail = lib.fit_score(prof, bar)
        if q is None:
            self.state.dead.add(cid)
            if reasons is not None:
                key = reason.split(":")[0].split(" ")[0]
                reasons[key] = reasons.get(key, 0) + 1
            return None
        keys = lib.person_key_candidates(prof)
        if any(k in self.state.person_keys for k in keys):
            self.state.dead.add(cid)
            if reasons is not None:
                reasons["duplicate_person"] = reasons.get("duplicate_person", 0) + 1
            return None
        return {"cid": cid, "profile": prof, "fetched_at": time.time(), "quality": q,
                "conf": conf, "detail": detail, "verified": False, "keys": keys}

    def fetch_profiles(self, ids):
        """Full profiles for ids: one batch call per 50 when at least BATCH_MIN_IDS are wanted, else singles."""
        profiles = {}
        ids = [str(i) for i in ids if i]
        if len(ids) >= int(self.cfg["BATCH_MIN_IDS"]):
            for i in range(0, len(ids), 50):
                chunk = ids[i:i + 50]
                if not self.can_spend(self.costs.get("batch")):
                    break
                items = extract_list(self.call("batch", self.arena.batch, chunk))
                for n, p in enumerate(items):
                    p = unwrap_profile(p)
                    cid = lib.field(p, "candidate_id", "id")
                    if cid is None and len(items) == len(chunk):
                        cid = chunk[n]
                    if cid is not None:
                        profiles[str(cid)] = p
        else:
            for cid in ids:
                if not self.can_spend(self.costs.get("candidate")):
                    break
                p = self.call("candidate", self.arena.candidate, cid)
                if isinstance(p, dict):
                    p = unwrap_profile(p)
                    profiles[str(lib.field(p, "candidate_id", "id") or cid)] = p
        return profiles

    def restock(self, bar, pages=None):
        """Refill one requisition's queue from its backlog or the next search pages. Returns entries added."""
        rid = bar["req_id"]
        pages_n = int(pages if pages is not None else self.cfg["PAGES_PER_RESTOCK"])
        max_pages = int(self.cfg["MAX_PAGES_PER_REQ"])
        want = int(self.cfg["BATCH_TOP_PER_RESTOCK"])
        backlog = self.backlog.setdefault(rid, [])
        self.stats["restocks"] += 1

        if len(backlog) < want:
            start = int(self.state.next_page.get(rid, 0))
            end = min(start + pages_n, max_pages)
            for page in range(start, end):
                if not self.can_spend(self.costs.get("search")):
                    break
                resp = self.call("search", self.arena.search, q="", role=bar["role"] or None,
                                 page=page, size=100)
                self.state.next_page[rid] = page + 1
                if resp is None:
                    break
                results = extract_list(resp)
                if not results:
                    self.state.next_page[rid] = max_pages
                    log("search_exhausted", req=rid, page=page)
                    break
                for s in results:
                    cid = lib.field(s, "candidate_id", "id")
                    if cid is None:
                        continue
                    cid = str(cid)
                    if cid in self.seen or cid in self.state.dead or cid in self.state.signed:
                        continue
                    self.seen.add(cid)
                    if lib.truthy(lib.field(s, "claimed", "is_claimed")):
                        self.state.dead.add(cid)
                        continue
                    backlog.append(s)
            backlog.sort(key=lambda s: lib.skill_overlap(lib.field(s, "skills"), bar["skills"]), reverse=True)

        if not backlog:
            self.state.dry_restocks[rid] = self.state.dry_restocks.get(rid, 0) + 1
            log("restock", req=rid, pages_to=self.state.next_page.get(rid), summaries=0,
                profiled=0, eligible=0, dry=self.state.dry_restocks[rid])
            self.state.save()
            return 0

        pick = [str(lib.field(s, "candidate_id", "id")) for s in backlog[:want]]
        del backlog[:want]
        profiles = self.fetch_profiles(pick)
        reasons = {}
        queue = self.queues.setdefault(rid, [])
        added = 0
        for cid, prof in profiles.items():
            e = self.evaluate(cid, prof, bar, reasons)
            if e:
                queue.append(e)
                added += 1
        queue.sort(key=lambda e: e["conf"] * self.est_points(e), reverse=True)
        self.state.dry_restocks[rid] = 0 if added else self.state.dry_restocks.get(rid, 0) + 1
        log("restock", req=rid, pages_to=self.state.next_page.get(rid), picked=len(pick),
            profiled=len(profiles), eligible=added, queue=len(queue), backlog=len(backlog),
            rejects=reasons, dry=self.state.dry_restocks[rid])
        self.state.save()
        return added

    # ---- verifying and signing ---------------------------------------------
    def refresh(self, e, bar):
        """Re-read a queued profile before offering (claimed status may have changed)."""
        if not self.can_spend(self.costs.get("candidate")):
            return e
        p = self.call("candidate", self.arena.candidate, e["cid"])
        if not isinstance(p, dict):
            return None
        p = unwrap_profile(p)
        verified = e["detail"].get("assessment") if e["detail"].get("src") == "verified" else None
        q, reason, conf, detail = lib.fit_score(p, bar, verified_assessment=verified)
        if q is None:
            self.state.dead.add(e["cid"])
            self.stats["refresh_rejected"] += 1
            log("refresh_rejected", cid=e["cid"], req=bar["req_id"], reason=reason)
            return None
        e.update(profile=p, fetched_at=time.time(), quality=q, detail=detail,
                 conf=max(conf, e["conf"]) if e["verified"] else conf)
        return e

    def should_assess(self, e):
        if self.assess_always:
            return True
        d = e["detail"]
        if d.get("src") == "none" or d.get("sentiment", 0) < 0:
            return True
        mp = d.get("margin_pts")
        if mp is not None and mp >= self.cfg["ASSESS_SKIP_MARGIN"]:
            return False
        return (1.0 - e["conf"]) * self.est_points(e) > self.costs.get("assess") * self.pf

    def assess(self, e, bar):
        """Buy the verified assessment + reference check. None = candidate ruled out."""
        if not self.can_spend(self.costs.get("assess")):
            return e
        a = self.call("assess", self.arena.assess, e["cid"])
        if not isinstance(a, dict):
            return e                     # assessment unavailable: fall back to unverified numbers
        self.stats["assessed"] += 1
        if lib.reference_check_bad(a):
            self.state.dead.add(e["cid"])
            self.stats["assess_rejected"] += 1
            log("assess_rejected", cid=e["cid"], req=bar["req_id"], why="reference_check",
                sample=json.dumps(a, default=str)[:300])
            return None
        verified = extract_verified(a)
        q, reason, conf, detail = lib.fit_score(e["profile"], bar, verified_assessment=verified)
        if q is None:
            self.state.dead.add(e["cid"])
            self.stats["assess_rejected"] += 1
            log("assess_rejected", cid=e["cid"], req=bar["req_id"], why=reason)
            return None
        if verified is None:
            conf = max(conf, 0.85)       # reference check passed even without a score
        e.update(quality=q, conf=conf, detail=detail, verified=True)
        return e

    def work_req(self, bar):
        """Fill one requisition's open slots, restocking its queue as it drains."""
        rid = bar["req_id"]
        remaining = int(bar["remaining"])
        queue = self.queues.setdefault(rid, [])
        while remaining > 0 and not self.exhausted:
            if not queue:
                if self.state.dry_restocks.get(rid, 0) >= int(self.cfg["DRY_LIMIT"]):
                    return
                if (int(self.state.next_page.get(rid, 0)) >= int(self.cfg["MAX_PAGES_PER_REQ"])
                        and not self.backlog.get(rid)):
                    return
                self.restock(bar)
                continue
            e = queue.pop(0)
            cid = e["cid"]
            if cid in self.state.signed or cid in self.state.dead:
                continue
            if any(k in self.state.person_keys for k in e["keys"]):
                self.state.dead.add(cid)
                continue
            stale = (self.cfg["CLOSING_STALE_SECONDS"] if self.phase == "closing"
                     else self.cfg["PROFILE_STALE_SECONDS"])
            if time.time() - e["fetched_at"] > stale:
                e = self.refresh(e, bar)
                if e is None:
                    continue
            if not e["verified"] and self.should_assess(e):
                e = self.assess(e, bar)
                if e is None:
                    continue
            offer_cost = self.costs.get("offer")
            ev = e["conf"] * self.est_points(e) - offer_cost * self.pf
            if ev <= 0:
                log("skip_low_ev", cid=cid, req=rid, ev=round(ev, 3))
                continue
            if not self.can_spend(offer_cost):
                log("budget_stop", req=rid, credits_remaining=self.arena.credits_remaining)
                queue.insert(0, e)
                return
            resp = self.call("offer", self.arena.offer, cid, rid)
            if not isinstance(resp, dict):
                self.state.dead.add(cid)
                self.state.save()
                continue
            if resp.get("accepted"):
                self.state.signed[cid] = rid
                self.state.signed_at[cid] = time.time()
                self.state.person_keys.update(e["keys"])
                self.state.held_quality[cid] = e["quality"]
                remaining -= 1
                self.stats["signed"] += 1
                log("signed", cid=cid, req=rid, quality=round(e["quality"], 3), conf=e["conf"],
                    est_points=round(self.est_points(e), 2), ev=round(ev, 2), verified=e["verified"],
                    already_yours=bool(resp.get("already_yours")), detail=e["detail"],
                    credits_remaining=self.arena.credits_remaining)
                self.state.save()
            else:
                reason = str(resp.get("reason") or resp.get("error") or "unknown")
                self.stats["rejected"] += 1
                self.state.dead.add(cid)
                log("offer_rejected", cid=cid, req=rid, reason=reason)
                self.state.save()
                if reason == "requisition_full":
                    return

    # ---- closing-hour upgrades ----------------------------------------------
    def upgrade_worthy(self, e):
        """Worth paying to assess as an upgrade: already verified, or a self-reported margin with room to spare."""
        if e["verified"]:
            return True
        d = e["detail"]
        mp = d.get("margin_pts")
        return mp is not None and mp >= self.cfg["UPGRADE_MIN_SELF_MARGIN"] and d.get("sentiment", 0) >= 0

    def upgrade_req(self, bar):
        """Swap this requisition's weakest hire for a clearly stronger, verified candidate.

        Order: find and verify the replacement first, release the weak hire only once
        the replacement is proven, then offer. If the offer is refused after the
        release, the slot is empty and the normal fill pass refills it next loop.
        """
        rid = bar["req_id"]
        cfg = self.cfg
        assessed = 0
        restocks = 0
        queue = self.queues.setdefault(rid, [])
        while (not self.upgrade_off and self.swaps < int(cfg["UPGRADE_MAX_SWAPS"])
               and assessed < int(cfg["UPGRADE_ASSESS_PER_PASS"])):
            held = [(self.state.held_quality.get(c, 0.0), c) for c, r in self.state.signed.items() if r == rid]
            if not held:
                return
            q_old, old_cid = min(held)
            if q_old > cfg["UPGRADE_MAX_OLD_QUALITY"]:
                return
            need = max(cfg["UPGRADE_MIN_NEW_QUALITY"], q_old + cfg["UPGRADE_MIN_DELTA"])
            cands = [e for e in queue
                     if e["cid"] not in self.state.dead and e["cid"] not in self.state.signed
                     and e["quality"] >= need and self.upgrade_worthy(e)]
            if not cands:
                if restocks >= 2 or self.state.dry_restocks.get(rid, 0) >= int(cfg["DRY_LIMIT"]):
                    return
                if int(self.state.next_page.get(rid, 0)) >= int(cfg["MAX_PAGES_PER_REQ"]) and not self.backlog.get(rid):
                    return
                restocks += 1
                self.restock(bar, pages=int(cfg["UPGRADE_PAGES_PER_RESTOCK"]))
                continue
            e = max(cands, key=lambda x: x["quality"])
            queue.remove(e)
            stale = cfg["CLOSING_STALE_SECONDS"] if self.phase == "closing" else cfg["PROFILE_STALE_SECONDS"]
            if time.time() - e["fetched_at"] > stale:
                e = self.refresh(e, bar)
                if e is None:
                    continue
            if not e["verified"]:
                assessed += 1
                e = self.assess(e, bar)
                if e is None:
                    continue
            if e["quality"] < q_old + cfg["UPGRADE_MIN_DELTA"]:
                queue.append(e)          # verified, just not strong enough to replace this hire
                continue
            if not self.can_spend(self.costs.get("release") + self.costs.get("offer")):
                queue.append(e)
                return
            rel = self.call("release", self.arena.release, old_cid)
            if not isinstance(rel, dict) or rel.get("error") or rel.get("released") is False:
                log("release_failed", cid=old_cid, req=rid, resp=json.dumps(rel, default=str)[:200])
                queue.append(e)
                return
            self.state.signed.pop(old_cid, None)
            self.state.signed_at.pop(old_cid, None)
            self.state.held_quality.pop(old_cid, None)
            self.state.dead.add(old_cid)
            self.state.save()
            resp = self.call("offer", self.arena.offer, e["cid"], rid)
            if isinstance(resp, dict) and resp.get("accepted"):
                cid = e["cid"]
                self.state.signed[cid] = rid
                self.state.signed_at[cid] = time.time()
                self.state.held_quality[cid] = e["quality"]
                self.state.person_keys.update(e["keys"])
                self.swaps += 1
                self.stats["upgrades"] += 1
                self.swap_log.append((time.time(), e["quality"] - q_old))
                log("upgraded", cid=cid, quality=round(e["quality"], 3), old_cid=old_cid,
                    old_quality=round(q_old, 3), req=rid, swaps=self.swaps, detail=e["detail"],
                    credits_remaining=self.arena.credits_remaining)
            else:
                self.state.dead.add(e["cid"])
                self.stats["upgrade_offer_rejected"] += 1
                reason = resp.get("reason") if isinstance(resp, dict) else resp
                log("upgrade_offer_rejected", cid=e["cid"], req=rid, reason=str(reason))
            self.state.save()

    # ---- periodic tasks ----------------------------------------------------
    def calibrate(self, led):
        """Learn points-per-hire from /ledger each time points_as_of moves (15-minute refresh)."""
        asof = led.get("points_as_of")
        if asof is None or asof == self.last_points_as_of:
            return
        first = self.last_points_as_of is None
        self.last_points_as_of = asof
        try:
            asof_f = float(asof)
        except (TypeError, ValueError):
            return
        pts = lib.first_number(led.get("points"), 0.0) or 0.0
        if self.prev_points is not None and self.swap_log:
            dq = sum(d for t, d in self.swap_log if self.prev_points_asof + 5 < t <= asof_f - 5)
            if dq >= 1.0:
                slope = (pts - self.prev_points) / dq
                log("upgrade_slope", delta_points=round(pts - self.prev_points, 2),
                    delta_quality=round(dq, 3), slope=round(slope, 2))
                if slope < self.cfg["UPGRADE_MIN_SLOPE"]:
                    self.upgrade_off = True
                    log("upgrade_stopped", why="measured points slope below UPGRADE_MIN_SLOPE",
                        slope=round(slope, 2))
        self.prev_points, self.prev_points_asof = pts, asof_f
        if first:
            return
        counted = sum(1 for t in self.state.signed_at.values() if t <= asof_f - 5)
        if counted >= 3 and pts > 0:
            live = max(1.0, min(200.0, pts / counted))
            log("points_calibrated", points=pts, counted_hires=counted,
                points_per_hire=round(live, 2), was=round(self.points_per_hire, 2))
            self.points_per_hire = live
            if live < 3.0 and self.assess_always:
                self.assess_always = False
                log("assess_policy", assess_always=False, why="a hire is worth less than 3 points")
        elif counted >= 5 and pts <= 0 and not self.assess_always:
            self.assess_always = True
            log("zero_points_alert", counted_hires=counted, action="assess every candidate from now on")

    def maybe_market(self):
        if time.time() - self.last_market_at < self.cfg["MARKET_EVERY_SECONDS"]:
            return
        if not self.can_spend(self.costs.get("market")):
            return
        self.last_market_at = time.time()
        m = self.call("market", self.arena.market)
        if m is not None:
            log("market", sample=json.dumps(m, default=str)[:1500])

    def heartbeat_log(self, led):
        if time.time() - self.last_heartbeat_log < self.cfg["HEARTBEAT_LOG_SECONDS"]:
            return
        self.last_heartbeat_log = time.time()
        log("heartbeat", phase=self.phase, credits_remaining=self.arena.credits_remaining,
            ledger_signed=led.get("signed"), points=led.get("points"), score=led.get("score"),
            points_per_hire=round(self.points_per_hire, 2), assess_always=self.assess_always,
            swaps=self.swaps, upgrade_off=self.upgrade_off,
            observed_costs=self.costs.observed, stats=self.stats,
            queues={k: len(v) for k, v in self.queues.items()}, next_page=self.state.next_page)

    # ---- main loop ---------------------------------------------------------
    def run(self):
        log("start", url=self.arena.base, penalty_factor=self.pf, points_per_hire=self.points_per_hire,
            assess_always=self.assess_always, restored_signed=len(self.state.signed),
            restored_dead=len(self.state.dead))
        while True:
            try:
                self.touch_heartbeat(force=True)
                self.cfg = load_config()
                led = self.arena.ledger()
                self.dump_once("ledger", led)
                if self.budget_total is None:
                    used = lib.first_number(led.get("credits_used"), 0.0) or 0.0
                    rem = lib.first_number(led.get("credits_remaining"))
                    if rem is not None:
                        self.budget_total = used + rem
                self.phase = str(led.get("phase", "unknown"))
                if self.phase != self.last_phase:
                    log("phase_change", phase=self.phase, credits_remaining=self.arena.credits_remaining,
                        score=led.get("score"), points=led.get("points"))
                    self.last_phase = self.phase
                if self.phase == "closed":
                    log("final", ledger=led, stats=self.stats)
                    break
                self.calibrate(led)
                if time.time() - self.last_dry_reset > self.cfg["DRY_RESET_SECONDS"]:
                    self.state.dry_restocks = {}
                    self.last_dry_reset = time.time()
                    log("dry_reset")
                if self.phase in ("market", "closing") and not self.exhausted:
                    reqs = extract_list(self.arena.requisitions())
                    self.dump_once("requisitions", reqs)
                    bars = [lib.requisition_bar(r, self.points_per_hire) for r in reqs]
                    bars = [b for b in bars if b["req_id"] and b["remaining"] > 0]
                    bars.sort(key=lambda b: b["remaining"], reverse=True)
                    for bar in bars:
                        self.work_req(bar)
                    if self.cfg["UPGRADE_ENABLED"] >= 1 and not self.upgrade_off:
                        for r in reqs:
                            full = lib.requisition_bar(r, self.points_per_hire)
                            if full["req_id"] and full["remaining"] == 0:
                                self.upgrade_req(full)
                    self.maybe_market()
                self.heartbeat_log(led)
                time.sleep(self.cfg["LOOP_SECONDS"])
            except Exhausted:
                self.exhausted = True
                log("credits_exhausted")
                time.sleep(30)
            except WrongPhase as e:
                log("wrong_phase", error=str(e)[:200])
                time.sleep(3)
            except KeyboardInterrupt:
                log("stopped_by_keyboard")
                break
            except Exception:
                log("crash_caught", trace=traceback.format_exc()[-2000:])
                time.sleep(5)
        self.state.save()


def main():
    if not os.environ.get("ARENA_KEY"):
        print("ARENA_KEY is not set. Set it in this terminal, then run again.", flush=True)
        sys.exit(1)
    if os.environ.get("FORCE_START") != "1":
        try:
            with open(HEARTBEAT_PATH, encoding="utf-8") as f:
                age = time.time() - float(f.read().strip())
            if age < 60:
                print(f"Another agent wrote a heartbeat {age:.0f}s ago ({HEARTBEAT_PATH}). "
                      "If no other agent is running, wait 60 s or set FORCE_START=1.", flush=True)
                sys.exit(2)
        except (OSError, ValueError):
            pass
    Agent().run()


if __name__ == "__main__":
    main()
