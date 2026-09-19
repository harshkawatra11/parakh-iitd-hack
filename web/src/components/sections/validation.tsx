"use client";

import { Section, SectionHeading, Stat } from "@/components/ui/primitives";
import { Reveal } from "@/components/ui/reveal";
import validation from "@/data/validation.json";

export function Validation() {
  return (
    <Section id="validation">
      <SectionHeading
        kicker="File 07 // Ledger Validation"
        title="We checked our work against a cycle we already know the answer to"
        lede="dev.csv is a past cycle's applicant pool; dev_winners.csv is who actually made the top 5%. We ran the full pipeline against it before ever touching the Vault."
      />
      <Reveal>
        <div className="grid grid-cols-2 gap-y-8 gap-x-6 border-t border-rule pt-8 md:grid-cols-4">
          <Stat value={validation.randomBaseline} label="Random baseline @150" />
          <Stat value={validation.recallVault} label="Submitted model @150" />
          <Stat value={validation.recallFull} label="Full (biased) model @150" />
          <Stat value="0 / 150" label="Winners ever flagged fake" />
        </div>
      </Reveal>
      <Reveal delay={0.1} className="mt-8 max-w-2xl border-t border-rule pt-6">
        <p className="text-[14px] leading-relaxed text-ink-2">
          The full model scores higher on this old cycle precisely because it still
          uses the old panel&rsquo;s biases. We submit the lower, de-biased number on
          purpose — recall on a cycle that no longer applies is the wrong thing to
          optimise for.
        </p>
      </Reveal>
    </Section>
  );
}
