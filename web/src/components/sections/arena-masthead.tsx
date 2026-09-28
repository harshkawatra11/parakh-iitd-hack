"use client";

import { motion } from "framer-motion";
import { Container, Kicker, Stat } from "@/components/ui/primitives";
import arena from "@/data/arena_events.json";

export function ArenaMasthead() {
  const filled = arena.requisitions_summary.total_filled;
  const headcount = arena.requisitions_summary.total_headcount;
  const swaps = arena.counts.upgraded_events;
  const creditsUsed = arena.ledger.credits_used;
  const budget = creditsUsed + arena.ledger.credits_remaining;
  const lastRank = arena.market_samples[arena.market_samples.length - 1];

  return (
    <div className="relative overflow-hidden border-b border-rule py-20 md:py-32">
      <Container>
        <Kicker className="mb-6">[ Live · Round 2 · The Battle Arena ]</Kicker>
        <h1 className="font-serif text-[3.2rem] leading-[1.02] tracking-[-0.01em] text-ink md:text-[5.5rem]">
          Fifty one recruiters,
          <br />
          <span className="italic">one shared</span> pool.
        </h1>
        <p className="mt-6 max-w-xl text-[15px] leading-relaxed text-ink-2">
          Innov8 4.0&rsquo;s live finale: a six-hour real-time market, 116 open seats across
          ten requisitions, a 50,000-credit budget, and a scoring formula that charges
          0.05 points for every credit spent. This console reads the agent&rsquo;s own
          decision log, frozen at 15:59 IST.
        </p>

        <motion.div
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          style={{ transformOrigin: "left" }}
          className="mt-10 h-px w-full max-w-2xl bg-verdigris"
        />

        <div className="mt-10 grid grid-cols-2 gap-y-8 gap-x-6 md:grid-cols-4">
          <Stat value={`${filled} / ${headcount}`} label="Requisitions filled" />
          <Stat value={swaps} label="Verified upgrade swaps" />
          <Stat
            value={`${creditsUsed.toLocaleString()} / ${budget.toLocaleString()}`}
            label="Credits used / budget"
          />
          <Stat
            value={lastRank ? `${lastRank.your_rank} / 51` : "N/A"}
            label="Arena rank, latest snapshot"
          />
        </div>
      </Container>
    </div>
  );
}
