"use client";

import { Bar } from "react-chartjs-2";
import "@/components/charts/chart-setup";
import { INK, SEAL, OLIVE, VERDIGRIS, baseOptions } from "@/components/charts/chart-setup";
import { Section, SectionHeading } from "@/components/ui/primitives";
import { Reveal } from "@/components/ui/reveal";
import arena from "@/data/arena_events.json";

function ChartCard({
  title,
  note,
  children,
}: {
  title: string;
  note: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-rule p-5 md:p-6">
      <h3 className="font-mono text-[11px] uppercase tracking-wide text-ink-2">
        {title}
      </h3>
      <div className="mt-4 h-56">{children}</div>
      <p className="mt-4 border-t border-rule pt-3 font-mono text-[11px] leading-relaxed text-ink-3">
        {note}
      </p>
    </div>
  );
}

export function ArenaCharts() {
  const budget = arena.ledger.credits_used + arena.ledger.credits_remaining;
  const firstRank = arena.market_samples[0];
  const lastRank = arena.market_samples[arena.market_samples.length - 1];

  return (
    <Section id="market">
      <SectionHeading
        kicker="File 02 // The Market, In Numbers"
        title="What 1,262 paid calls actually bought"
        lede="Every figure below is read off the agent's own ledger and market snapshots, not estimated after the fact."
      />
      <div className="grid gap-5 md:grid-cols-2">
        <Reveal>
          <ChartCard
            title="Credits: spent vs remaining"
            note={`31,003 of a 50,000 credit budget spent by the freeze, ${arena.ledger.calls.toLocaleString()} API calls made across the six-hour window.`}
          >
            <Bar
              data={{
                labels: ["Credits used", "Credits remaining"],
                datasets: [
                  {
                    data: [arena.ledger.credits_used, arena.ledger.credits_remaining],
                    backgroundColor: [SEAL, OLIVE],
                    borderRadius: 2,
                    barThickness: 64,
                  },
                ],
              }}
              options={{
                ...baseOptions,
                scales: { ...baseOptions.scales, y: { ...baseOptions.scales.y, min: 0, max: budget } },
              }}
            />
          </ChartCard>
        </Reveal>

        <Reveal delay={0.06}>
          <ChartCard
            title="Signed, upgraded, crashed"
            note="116 requisition seats filled, 70 of them later swapped for a stronger verified hire, one crash caught and survived without exiting the loop."
          >
            <Bar
              data={{
                labels: ["Signed (held)", "Upgrade swaps", "Crashes caught"],
                datasets: [
                  {
                    data: [
                      arena.requisitions_summary.total_filled,
                      arena.counts.upgraded_events,
                      arena.counts.crash_caught_events,
                    ],
                    backgroundColor: [VERDIGRIS, SEAL, INK],
                    borderRadius: 2,
                    barThickness: 48,
                  },
                ],
              }}
              options={baseOptions}
            />
          </ChartCard>
        </Reveal>

        <Reveal delay={0.12}>
          <ChartCard
            title="Arena rank, of 51 teams"
            note={`Rank ${firstRank?.your_rank ?? "?"} of 51 right after the opening wave (${firstRank?.t}), rank ${lastRank?.your_rank ?? "?"} of 51 mid upgrade sprint (${lastRank?.t}). Lower is better.`}
          >
            <Bar
              data={{
                labels: [`Opening wave, ${firstRank?.t}`, `Upgrade sprint, ${lastRank?.t}`],
                datasets: [
                  {
                    data: [firstRank?.your_rank ?? 0, lastRank?.your_rank ?? 0],
                    backgroundColor: [OLIVE, VERDIGRIS],
                    borderRadius: 2,
                    barThickness: 64,
                  },
                ],
              }}
              options={{
                ...baseOptions,
                scales: { ...baseOptions.scales, y: { ...baseOptions.scales.y, min: 0, max: 51, reverse: true } },
              }}
            />
          </ChartCard>
        </Reveal>

        <Reveal delay={0.18}>
          <ChartCard
            title="Why a candidate never became a hire"
            note="Summed across every restock cycle. Below-bar assessments were the largest single reason, but 2,111 candidates were lost simply because another team reached them first."
          >
            <Bar
              data={{
                labels: ["Below bar", "Already claimed", "Notice period", "CTC ceiling"],
                datasets: [
                  {
                    data: [
                      arena.restock_reject_totals.below_bar,
                      arena.restock_reject_totals.claimed,
                      arena.restock_reject_totals.notice,
                      arena.restock_reject_totals.ctc,
                    ],
                    backgroundColor: SEAL,
                    borderRadius: 2,
                    barThickness: 34,
                  },
                ],
              }}
              options={{ ...baseOptions, indexAxis: "y" as const }}
            />
          </ChartCard>
        </Reveal>
      </div>
    </Section>
  );
}
