"use client";

import { Section, SectionHeading } from "@/components/ui/primitives";
import { Reveal, RevealGroup, revealItem } from "@/components/ui/reveal";
import { motion } from "framer-motion";
import funnel from "@/data/funnel.json";

const COLORS = ["var(--ink-3)", "var(--olive)", "var(--ochre)", "var(--ink-3)", "var(--ink-2)", "var(--seal)"];

export function Funnel() {
  const max = funnel[0].count;
  return (
    <Section id="funnel">
      <SectionHeading
        kicker="File 02 // The Exclusion Funnel"
        title="Ten thousand profiles. Five hundred names."
        lede="Every removal is a rule, not a hunch — each stage below is a hard, auditable check applied to the Vault."
      />
      <RevealGroup className="space-y-5" stagger={0.06}>
        {funnel.map((stage, i) => {
          const pct = (stage.count / max) * 100;
          return (
            <motion.div key={stage.stage} variants={revealItem} className="group">
              <div className="mb-1.5 flex items-baseline justify-between font-mono text-[12px]">
                <span className="text-ink-2">{stage.stage}</span>
                <span className="text-ink-3">{stage.note}</span>
              </div>
              <div className="relative h-8 w-full bg-paper-2">
                <motion.div
                  initial={{ width: 0 }}
                  whileInView={{ width: `${pct}%` }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] }}
                  className="absolute inset-y-0 left-0"
                  style={{ backgroundColor: COLORS[i] }}
                />
                <span className="absolute inset-y-0 right-2 flex items-center font-mono text-[12px] font-medium text-ink font-tnum">
                  {stage.count.toLocaleString()}
                </span>
              </div>
            </motion.div>
          );
        })}
      </RevealGroup>
      <Reveal delay={0.3} className="mt-8 border-t border-rule pt-6">
        <p className="max-w-2xl font-mono text-[12px] leading-relaxed text-ink-3">
          On the Ledger cycle (dev.csv), the same fabrication rule flagged 87 of 2,999
          profiles — and <span className="text-ink font-medium">zero</span> of the 150
          confirmed winners were among them.
        </p>
      </Reveal>
    </Section>
  );
}
