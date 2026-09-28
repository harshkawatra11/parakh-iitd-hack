# Parakh Arena — Strategy Note

**Team:** IdeaForge · Harsh Kawatra · Delhi Technological University (DTU)

## One idea everything else follows

A credit is worth `PENALTY_FACTOR` points, because that is exactly what the
scoring formula charges for it. So every paid action, a search page, a
profile, a batch, an assessment, an offer, only happens when the points it
is expected to earn beat that price:

```
expected_points_gained > cost_in_credits × PENALTY_FACTOR
```

Nothing else in the agent is a fixed number. Raising or lowering
`PENALTY_FACTOR` in `config.json` (re-read every loop, no redeploy needed
mid-run, though a redeploy is also safe, see below) makes the agent buy more
or less certainty, search wider or narrower, and sign more eagerly or more
conservatively, automatically.

## What it buys, and when

**Recon (offers locked, the cheapest hour to learn the pool).** For each
open requisition: page through `/search` on the role, rank the returned
summaries locally by skill overlap (free, since ranking a summary costs
nothing once it's already been paid for by the search call), keep the best
few dozen, then fetch their full profiles in one `/candidates/batch` call
per fifty (60 credits for fifty profiles beats fifty calls at 2 credits
each only when more than thirty are wanted at once, which they usually
are). Every profile is checked for internal contradictions before anything
else: an age that makes the claimed experience impossible, a career-path
history that doesn't add up to the stated total, more years of experience
than years since graduation allows. These are the same checks, carried
over, that caught fabricated profiles in the preliminary round with zero
false positives against a cycle whose real winners were already known.
Profiles that fail them, or that are already claimed, are dropped before a
single credit is spent trying to rank them further.

**Selective verification.** `/assess` costs 25 credits, more than ten times
a profile. It's only worth buying when the offer decision actually depends
on it: a missing or unverified self-reported score, a thin margin over the
requisition's bar, or a risk signal in the free-text note. A per-requisition
cap keeps this from spiralling: even where the raw expected-value math would
justify assessing everyone, the agent caps itself, because the real cost of
recon isn't just credits, it's the hour of clock it has to finish inside.

**The opening wave (11:30 sharp).** By the time offers unlock, every
requisition already has a ranked, verified-where-it-mattered shortlist.
The agent fires its best available offer into every open slot within
seconds of the phase flipping, because the brief is explicit that the best
names go first in a live market.

**Handling a rejected offer.** Every reason the API can return is handled
explicitly rather than just logged and ignored: `already_signed` and
`same_person_already_signed` retire that candidate id for good,
`requisition_full` stops the agent from wasting further offers on a
role that's done, and `role_mismatch` retires just that pairing. A repeat
of an offer already held is safe by the client's own design.

**Closing hour.** Offer and other costs are re-measured live rather than
assumed: the agent tracks the actual credit delta around every paid call,
so a documented cost change (offers doubling in the closing hour) is picked
up automatically from the numbers, not from a second hardcoded table that
could drift out of sync with reality.

**Stopping.** When nothing left in a requisition's queue clears its
expected-value bar, the agent stops spending on it and falls back to free
`/ledger` polling until the arena closes. Credits left on the table cost
nothing; a bad signing costs the slot as well as the credits.

## What we tuned once the penalty factor was announced

`PENALTY_FACTOR` sets `config.json`, which the agent re-reads every polling
loop. A low value widens recon (more search pages, a larger shortlist, more
assessments bought) because information is cheap relative to the points on
offer; a high value narrows it to only the most obviously worthwhile
candidates. The closing reserve and market-poll frequency are set as small
multiples of the same number, so one edit is enough. If a redeploy is
needed to change it, in-flight state (who we've already signed, who's
already been ruled out) is checkpointed to disk and reloaded on restart,
so the redeploy re-tunes the agent's future decisions without re-spending
on decisions it already made.

## What we would do with another two hours

Widen recon to run requisitions in parallel rather than one after another,
which would let us afford a larger shortlist per role inside the same
one-hour window. Add a live re-ranking pass during the market phase that
reads `/market` price pressure and pulls forward offers for requisitions
where rival agencies are visibly filling fast, rather than working strictly
in the order requisitions were listed. Use `/reason` more deliberately: it
is currently reserved for candidates whose recruiter note doesn't match any
of the keyword patterns already known to carry signal from the preliminary
round's data; with more budget headroom it could also summarise market
conditions across all open requisitions once per poll, and could substitute
for the keyword table entirely if it earns its keep credit for credit.

## Edge cases handled

An empty search page stops that requisition's paging rather than retrying
forever. A crash anywhere in the main loop is caught, logged with its
traceback, and the loop continues rather than exiting, since a third crash
ends the run entirely. Running out of credits is treated as a terminal but
graceful state: the agent stops trying to spend and idles on free calls
until the arena closes, rather than raising past the point where nothing
useful can happen. The rate limit is handled inside `arena_client.py`,
which was provided in the starter kit and used unmodified: it backs off and
retries a `429 rate_limited` response automatically. A wrong-phase error
(an offer attempted during recon, for instance) is caught and treated as a
signal to re-check the current phase, not as a fatal error.

## AI assistants declared

Anthropic Claude (Claude Code) was used to draft and refactor this agent's
code, to design and run the local mock-arena tests it was validated
against before deployment, and to draft this note. Every rule, threshold
and piece of reasoning above was checked against the actual starter kit,
the actual API reference, and a local test harness built to the same
documented contract, not assumed from memory.
