"use client";

import { useState } from "react";
import { Section, SectionHeading } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

const ITEMS = [
  {
    q: "The EV gate",
    a: `One rule everything else follows: a credit is worth exactly what the scoring
formula charges for it, 0.05 points. Every paid call, a search page, a batch
fetch, a verification, an offer, only happens when the points it is expected
to earn beat that price. Raising or lowering the penalty factor in
config.json (re-read every loop) makes the agent buy more or less certainty
automatically, with no redeploy needed.`,
    code: `if expected_points_gained > cost_in_credits * PENALTY_FACTOR:
    proceed()
else:
    skip()  # credits left on the table cost nothing`,
  },
  {
    q: "The forensic layer, reused",
    a: `The same two checks that caught fabricated profiles in round one, an age at
graduation too young to be real and an experience total that contradicts the
applicant's own career history, now run against the Arena's live fields:
verified_assessment, reference_check, identity_verified. A failure on any of
them retires the candidate before another credit is spent, the same way a
fabricated row was excluded from round one's Vault.`,
    code: `{"candidate_id": "NG-0125791", "verified_assessment": 37,
 "reference_check": "could not verify employment",
 "identity_verified": false}
# retired on the spot, zero further credits spent`,
  },
  {
    q: "Selective verification",
    a: `/assess costs 25 credits, more than ten times a single profile fetch. It is
only bought when the offer decision actually depends on it: a missing or
unverified self-reported score, a thin margin over the requisition's bar, or
a risk signal in the free-text note. 210 assess_rejected events were logged
across the run, 142 below-bar failures and 68 reference-check failures.`,
    code: `buy_assess = (self_reported is None
              or margin_over_bar < THIN_MARGIN
              or has_risk_note(candidate))`,
  },
  {
    q: "The upgrade or swap engine",
    a: `Built and deployed during the closing hour, once the market's own snapshot
showed the team fully staffed but ranked 48 of 51. For each requisition it
looks for a stronger, independently verified replacement for the weakest
currently held hire, verifies it, releases the weak one, signs the strong
one, then measures the real points gained per credit that specific swap
cost. It is designed to idle the moment a swap stops paying for itself.`,
    code: `if verified_quality(candidate) > held_quality(weakest):
    release(weakest); offer(candidate)
    if slope(points_gained, credits_spent) <= 0:
        upgrade_engine.pause()`,
  },
];

export function ArenaMethod() {
  const [open, setOpen] = useState(0);
  return (
    <Section id="method">
      <SectionHeading kicker="File 04 // How It Decided" title="What decides what, in the live market" />
      <div className="border-t border-rule">
        {ITEMS.map((item, i) => (
          <div key={item.q} className="border-b border-rule">
            <button
              onClick={() => setOpen(open === i ? -1 : i)}
              className="flex w-full items-center justify-between py-5 text-left"
            >
              <span className="font-serif text-2xl text-ink">{item.q}</span>
              <span className="font-mono text-ink-3">{open === i ? "−" : "+"}</span>
            </button>
            <div className={cn("overflow-hidden transition-all", open === i ? "max-h-[600px] pb-6" : "max-h-0")}>
              <div className="grid gap-6 md:grid-cols-2">
                <p className="text-[14px] leading-relaxed text-ink-2 whitespace-pre-line">
                  {item.a}
                </p>
                <pre className="overflow-x-auto border border-rule bg-paper-2 p-4 font-mono text-[11px] leading-relaxed text-ink-2">
                  {item.code}
                </pre>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}
