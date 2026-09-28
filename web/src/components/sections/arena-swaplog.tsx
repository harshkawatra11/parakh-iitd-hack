"use client";

import { useMemo, useState } from "react";
import { Section, SectionHeading, Badge } from "@/components/ui/primitives";
import arena from "@/data/arena_events.json";

const PAGE_SIZE = 15;

export function ArenaSwapLog() {
  const [page, setPage] = useState(0);
  const upgrades = useMemo(() => arena.upgrades, []);
  const pageRows = upgrades.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const pageCount = Math.max(1, Math.ceil(upgrades.length / PAGE_SIZE));

  return (
    <Section id="swap-log">
      <SectionHeading
        kicker="File 03 // The Swap Log"
        title="70 upgrades, three minutes and forty seven seconds"
        lede="Every row is a real closing-hour swap: a weaker held hire released, a stronger verified candidate signed in its place, read straight from the agent's decision log."
      />

      <div className="border border-rule">
        <div className="grid grid-cols-[70px_1fr_1fr_90px_90px] gap-3 border-b border-rule bg-paper-2 px-4 py-2 font-mono text-[10px] uppercase tracking-wide text-ink-3">
          <span>Time</span>
          <span>Requisition</span>
          <span>Released &rarr; signed</span>
          <span>Quality</span>
          <span>Swap #</span>
        </div>
        {pageRows.map((u) => (
          <div
            key={`${u.cid}-${u.t}`}
            className="grid grid-cols-[70px_1fr_1fr_90px_90px] gap-3 border-b border-rule px-4 py-2.5 font-mono text-[12px] last:border-b-0"
          >
            <span className="text-ink-3">{u.t}</span>
            <span>
              <Badge tone="verdigris">{u.req}</Badge>
            </span>
            <span className="truncate text-ink-2">
              <span className="text-ink-3">{u.old_cid}</span> &rarr; <span className="text-ink">{u.cid}</span>
            </span>
            <span className="text-ink-3">
              {u.old_quality?.toFixed(3)} &rarr; <span className="text-ink font-medium">{u.quality?.toFixed(3)}</span>
            </span>
            <span className="text-ink-3">#{u.swaps}</span>
          </div>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between font-mono text-[11px] text-ink-3">
        <button
          disabled={page === 0}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          className="disabled:opacity-30 hover:text-ink"
        >
          &larr; prev
        </button>
        <span>
          {upgrades.length} swaps &middot; page {page + 1} / {pageCount}
        </span>
        <button
          disabled={page >= pageCount - 1}
          onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
          className="disabled:opacity-30 hover:text-ink"
        >
          next &rarr;
        </button>
      </div>
    </Section>
  );
}
