"use client";

import { motion } from "framer-motion";
import { Container, Kicker, Stat } from "@/components/ui/primitives";
import validation from "@/data/validation.json";

export function Masthead() {
  const recallPct = Math.round((validation.recallVault / validation.totalWinners) * 100);
  return (
    <div className="relative overflow-hidden border-b border-rule py-20 md:py-32">
      <Container>
        <Kicker className="mb-6">[ Classified · Preliminary Round ]</Kicker>
        <h1 className="font-serif text-[3.2rem] leading-[1.02] tracking-[-0.01em] text-ink md:text-[5.5rem]">
          Five hundred names,
          <br />
          <span className="italic">defensible</span> one by one.
        </h1>
        <p className="mt-6 max-w-xl text-[15px] leading-relaxed text-ink-2">
          Parakh (परख — discernment) is our shortlist and audit trail for Innov8 4.0&rsquo;s
          &ldquo;Corporate Heist&rdquo; case: 10,000 applicant profiles, a hiring panel that
          quietly changed its standards, and 500 names we are prepared to defend to
          Eightfold.ai engineers in person.
        </p>

        <motion.div
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          style={{ transformOrigin: "left" }}
          className="mt-10 h-px w-full max-w-2xl bg-seal"
        />

        <div className="mt-10 grid grid-cols-2 gap-y-8 gap-x-6 md:grid-cols-4">
          <Stat value="10,000" label="Vault profiles" />
          <Stat value="736" label="Profiles rejected" />
          <Stat value="9,754" label="Real people" />
          <Stat value={`${recallPct}%`} label="Ledger recall @150" />
        </div>
      </Container>
    </div>
  );
}
