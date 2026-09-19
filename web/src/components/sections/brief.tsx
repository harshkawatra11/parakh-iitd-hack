"use client";

import { useState } from "react";
import { Section, SectionHeading, Rule } from "@/components/ui/primitives";
import { Reveal } from "@/components/ui/reveal";
import { cn } from "@/lib/utils";

const LINES = [
  {
    t: "00:03",
    line: "Don't assume this cycle works like the old ones. Things changed after the reorg.",
    action: "Every rule below treats the Vault as its own regime, not an extension of the Archive.",
  },
  {
    t: "00:11",
    line: "They finally started logging public code contributions this year... someone with a sustained record, dozens of merged contributions or more, gets fast-tracked.",
    action: "public_code_contributions is test-only. Log-ramp bonus from 12 → saturates at 48 contributions.",
  },
  {
    t: "00:42",
    line: "Résumés where the titles climb faster than the years behind them... now go straight to the bin.",
    action: "Learned per-level tenure floor from the Archive → 149 title-inflated profiles excluded.",
  },
  {
    t: "01:05",
    line: "Anyone who can't join inside two months is dead to them this cycle.",
    action: "notice_period > 60 days excluded — a value with zero precedent in train or dev.",
  },
  {
    t: "01:21",
    line: "Their best people this cycle came from colleges they had never hired from before... They love those.",
    action: "New-institute candidates in the top decile of their role's assessment get a +0.70z boost.",
  },
  {
    t: "01:39",
    line: "Forget the old committee's pet preferences... The old panel quietly inflated all of it. The new panel ignores every one of those.",
    action: "Institute, city, referral channel, employer brand, degree and CV-gap features dropped from the Vault model.",
  },
  {
    t: "01:53",
    line: "The only old habit that survived the reorg is the old-boys' network: a handful of colleges... still get a leg up.",
    action: "Residual regression (merit + role) isolates 5 schools at t≥3.0 → +0.25z, computed not hardcoded.",
  },
  {
    t: "02:07",
    line: "The data is filthy... Some profiles are straight-up fabricated... the same person sometimes shows up twice.",
    action: "393 fabricated profiles excluded (0% ever in the true top 5%); 246 duplicate rows collapsed to 9,754 people.",
  },
];

export function Brief() {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <Section id="brief">
      <SectionHeading
        kicker="File 01 // The Insider's Debrief"
        title="What the voice note said, and what we did about it"
        lede="Recovered, unedited, one speaker. Hover — or tap — any line to see the rule it became."
      />
      <div className="border-t border-rule">
        {LINES.map((l, i) => (
          <Reveal key={l.t} delay={i * 0.03}>
            <button
              onClick={() => setOpen(open === i ? null : i)}
              className="group block w-full border-b border-rule py-5 text-left"
            >
              <div className="grid grid-cols-[64px_1fr] gap-4 md:grid-cols-[80px_1fr_1fr]">
                <span className="font-mono text-[12px] text-seal pt-0.5">{l.t}</span>
                <p className="font-serif text-[19px] italic leading-snug text-ink md:pr-8">
                  &ldquo;{l.line}&rdquo;
                </p>
                <div
                  className={cn(
                    "hidden md:block font-mono text-[12px] leading-relaxed text-ink-3 transition-opacity",
                    "opacity-0 group-hover:opacity-100",
                    open === i && "opacity-100"
                  )}
                >
                  → {l.action}
                </div>
              </div>
              <div
                className={cn(
                  "md:hidden overflow-hidden font-mono text-[12px] leading-relaxed text-ink-3 transition-all",
                  open === i ? "mt-3 max-h-24" : "max-h-0"
                )}
              >
                → {l.action}
              </div>
            </button>
          </Reveal>
        ))}
      </div>
      <Rule className="mt-0" />
    </Section>
  );
}
