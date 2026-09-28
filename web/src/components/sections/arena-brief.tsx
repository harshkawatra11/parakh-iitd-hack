"use client";

import { Section, SectionHeading } from "@/components/ui/primitives";
import { Reveal } from "@/components/ui/reveal";

export function ArenaBrief() {
  return (
    <Section id="brief">
      <SectionHeading
        kicker="File 01 // Six Hours, No Human In The Loop"
        title="Filled and mediocre beats empty. It does not beat filled and strong."
        lede="The story of one autonomous agent against a live, adversarial market it could not pause or replay."
      />
      <div className="space-y-6 max-w-3xl">
        <Reveal>
          <p className="text-[15px] leading-relaxed text-ink-2">
            The agent launched at 15:15:05 IST and had offers in every one of the 116 open
            seats within three minutes, because the recon that decides who to offer had
            already run in parallel across all ten requisitions before the market even
            opened. Three minutes later the arena&rsquo;s own market snapshot placed the
            team at rank 48 of 51, fully staffed and near the bottom of the board at the
            same time, because the scoring formula does not care how fast a seat filled,
            only how strong the hire in it is.
          </p>
        </Reveal>
        <Reveal delay={0.06}>
          <p className="text-[15px] leading-relaxed text-ink-2">
            The closing hour became a second problem. At 15:38:25 the arena moved to its
            closing phase. At 15:41:04 the agent hit a transient network failure calling
            requisitions, caught it, logged it, and kept running rather than exiting, the
            same crash-survives-the-loop design carried over from round one. At 15:53:50
            the team redeployed with an upgrade engine live: find a stronger, independently
            verified replacement for the weakest currently held hire, verify it, release
            the weak one, sign the strong one, and check whether the swap is still paying
            for itself before doing another. It ran 70 such swaps in three minutes and
            forty seven seconds.
          </p>
        </Reveal>
        <Reveal delay={0.12}>
          <p className="text-[15px] leading-relaxed text-ink-2">
            By the time this data was frozen at 15:59 IST, the arena&rsquo;s market endpoint
            had the team at rank 18 of 51, up thirty places on the same 116 filled seats.
            The full account, including where the agent&rsquo;s own local score readout and
            the arena&rsquo;s real scoring cadence visibly disagreed during the sprint, is in
            the arena README linked below.
          </p>
        </Reveal>
      </div>
    </Section>
  );
}
