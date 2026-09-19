"use client";

import { useMemo, useState } from "react";
import { Section, SectionHeading, Badge } from "@/components/ui/primitives";
import exclusions from "@/data/exclusions.json";

const REASON_LABEL: Record<string, { label: string; tone: "seal" | "ochre" | "olive" }> = {
  fabricated: { label: "Fabricated", tone: "seal" },
  inflated: { label: "Title inflated", tone: "ochre" },
  late: { label: "Cannot join in time", tone: "olive" },
};

const PAGE_SIZE = 40;

export function Ledger() {
  const [filter, setFilter] = useState<string>("all");
  const [page, setPage] = useState(0);

  const filtered = useMemo(
    () => (filter === "all" ? exclusions : exclusions.filter((e) => e.reason === filter)),
    [filter]
  );
  const pageRows = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  return (
    <Section id="ledger">
      <SectionHeading
        kicker="File 05 // The Exclusions Ledger"
        title="736 profiles removed. None of them by guess."
        lede="On the Ledger cycle, this exact rule set removed 87 profiles — and zero of the 150 confirmed winners were among them."
      />

      <div className="mb-4 flex flex-wrap gap-2">
        {["all", "fabricated", "inflated", "late"].map((f) => (
          <button
            key={f}
            onClick={() => {
              setFilter(f);
              setPage(0);
            }}
            className={`border px-3 py-1.5 font-mono text-[11px] uppercase tracking-wide transition-colors ${
              filter === f
                ? "border-ink bg-ink text-paper"
                : "border-rule text-ink-3 hover:border-ink-3"
            }`}
          >
            {f === "all" ? "All" : REASON_LABEL[f]?.label}
          </button>
        ))}
      </div>

      <div className="border border-rule">
        <div className="grid grid-cols-[100px_1fr_140px_1fr] gap-3 border-b border-rule bg-paper-2 px-4 py-2 font-mono text-[10px] uppercase tracking-wide text-ink-3">
          <span>ID</span>
          <span>Name / role</span>
          <span>Reason</span>
          <span>Detail</span>
        </div>
        {pageRows.map((e) => (
          <div
            key={e.candidate_id}
            className="grid grid-cols-[100px_1fr_140px_1fr] gap-3 border-b border-rule px-4 py-2.5 font-mono text-[12px] last:border-b-0"
          >
            <span className="text-ink">{e.candidate_id}</span>
            <span className="truncate text-ink-2">
              {e.name} <span className="text-ink-3">· {e.role}</span>
            </span>
            <span>
              <Badge tone={REASON_LABEL[e.reason]?.tone ?? "olive"}>
                {REASON_LABEL[e.reason]?.label ?? e.reason}
              </Badge>
            </span>
            <span className="truncate text-ink-3">{e.detail}</span>
          </div>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between font-mono text-[11px] text-ink-3">
        <button
          disabled={page === 0}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          className="disabled:opacity-30 hover:text-ink"
        >
          ← prev
        </button>
        <span>
          {filtered.length} rows · page {page + 1} / {pageCount}
        </span>
        <button
          disabled={page >= pageCount - 1}
          onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
          className="disabled:opacity-30 hover:text-ink"
        >
          next →
        </button>
      </div>
    </Section>
  );
}
