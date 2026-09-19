"use client";

import { useMemo, useState } from "react";
import { Section, SectionHeading, Badge } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";
import shortlist from "@/data/shortlist.json";

type Row = (typeof shortlist)[number];

const PAGE_SIZE = 50;

export function Shortlist() {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [active, setActive] = useState<Row | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return shortlist;
    return shortlist.filter(
      (r) =>
        r.candidate_id.toLowerCase().includes(q) ||
        (r.name ?? "").toLowerCase().includes(q) ||
        (r.role ?? "").toLowerCase().includes(q) ||
        (r.institute ?? "").toLowerCase().includes(q)
    );
  }, [query]);

  const pageRows = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  return (
    <Section id="shortlist">
      <SectionHeading
        kicker="File 04 // The Shortlist"
        title="500 names, ranked, and shown working"
        lede="Every row opens into a dossier: the score decomposition, the raw values as recruiters typed them, and the checks each profile passed."
      />

      <div className="mb-4 flex items-center justify-between gap-4">
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(0);
          }}
          placeholder="Filter by ID, name, role, institute…"
          className="w-full max-w-sm border border-rule bg-transparent px-3 py-2 font-mono text-[13px] text-ink placeholder:text-ink-3 focus:border-seal focus:outline-none"
        />
        <span className="font-mono text-[11px] text-ink-3 whitespace-nowrap">
          {filtered.length} / 500
        </span>
      </div>

      <div className="border border-rule">
        <div className="grid grid-cols-[48px_100px_1fr_1fr_1fr_80px] gap-3 border-b border-rule bg-paper-2 px-4 py-2 font-mono text-[10px] uppercase tracking-wide text-ink-3">
          <span>Rank</span>
          <span>ID</span>
          <span>Name</span>
          <span>Role</span>
          <span>Institute</span>
          <span className="text-right">Score</span>
        </div>
        {pageRows.map((r) => (
          <button
            key={r.candidate_id}
            onClick={() => setActive(r)}
            className="grid w-full grid-cols-[48px_100px_1fr_1fr_1fr_80px] gap-3 border-b border-rule px-4 py-2.5 text-left font-mono text-[12px] last:border-b-0 hover:bg-paper-2"
          >
            <span className="text-ink-3 font-tnum">{r.rank}</span>
            <span className="text-ink">{r.candidate_id}</span>
            <span className="truncate text-ink-2">{r.name}</span>
            <span className="truncate text-ink-2">{r.role}</span>
            <span className="truncate text-ink-3">{r.institute}</span>
            <span className="text-right text-ink font-tnum">{r.score?.toFixed(2)}</span>
          </button>
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
          page {page + 1} / {pageCount}
        </span>
        <button
          disabled={page >= pageCount - 1}
          onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
          className="disabled:opacity-30 hover:text-ink"
        >
          next →
        </button>
      </div>

      {active && <Dossier row={active} onClose={() => setActive(null)} />}
    </Section>
  );
}

function Dossier({ row, onClose }: { row: Row; onClose: () => void }) {
  const bonuses = [
    { label: "Base merit (z)", value: (row.score ?? 0) - (row.bonus_pcc ?? 0) - (row.bonus_newcol ?? 0) - (row.bonus_oldboys ?? 0) },
    { label: "Public contributions bonus", value: row.bonus_pcc ?? 0 },
    { label: "New-college bonus", value: row.bonus_newcol ?? 0 },
    { label: "Old-boys' network bonus", value: row.bonus_oldboys ?? 0 },
  ];
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-ink/30" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="h-full w-full max-w-md overflow-y-auto border-l border-rule bg-paper p-6"
      >
        <div className="mb-6 flex items-start justify-between">
          <div>
            <div className="font-mono text-[11px] text-seal">RANK {row.rank}</div>
            <h3 className="font-serif text-2xl">{row.name}</h3>
            <p className="font-mono text-[12px] text-ink-3">{row.candidate_id}</p>
          </div>
          <button onClick={onClose} className="font-mono text-[11px] text-ink-3 hover:text-ink">
            close ✕
          </button>
        </div>

        <div className="mb-6 flex flex-wrap gap-2">
          <Badge tone="ink">{row.role}</Badge>
          <Badge tone="ink">{row.title}</Badge>
          {row.newCollege && <Badge tone="verdigris">New college</Badge>}
          {row.oldBoys && <Badge tone="ochre">Old-boys' network</Badge>}
        </div>

        <h4 className="mb-3 font-mono text-[11px] uppercase tracking-wide text-ink-2">
          Score decomposition
        </h4>
        <div className="mb-6 space-y-2">
          {bonuses.map((b) => (
            <div key={b.label} className="flex items-center gap-3">
              <span className="w-40 flex-shrink-0 font-mono text-[11px] text-ink-3">{b.label}</span>
              <div className="relative h-4 flex-1 bg-paper-2">
                <div
                  className={cn("absolute inset-y-0 left-0 bg-ink", b.value < 0 && "bg-seal")}
                  style={{ width: `${Math.min(100, Math.abs(b.value) * 40)}%` }}
                />
              </div>
              <span className="w-14 flex-shrink-0 text-right font-mono text-[11px] font-tnum text-ink">
                {b.value.toFixed(2)}
              </span>
            </div>
          ))}
        </div>

        <h4 className="mb-3 font-mono text-[11px] uppercase tracking-wide text-ink-2">
          Raw → parsed
        </h4>
        <table className="w-full font-mono text-[11px]">
          <tbody>
            <Row2 k="technical_assessment" raw={row.tech_raw} parsed={row.tech} />
            <Row2 k="aptitude_score" raw={undefined} parsed={row.apt} />
            <Row2 k="last_rating" raw={undefined} parsed={row.rating} />
            <Row2 k="kpi_met" raw={row.kpi} parsed={undefined} />
            <Row2 k="total_experience" raw={row.exp_raw} parsed={row.exp} />
            <Row2 k="notice_period" raw={row.notice_raw} parsed={undefined} />
            <Row2 k="current_ctc" raw={row.ctc_raw} parsed={undefined} />
            <Row2 k="expected_ctc" raw={row.ectc_raw} parsed={undefined} />
            <Row2 k="public_code_contributions" raw={undefined} parsed={row.pcc} />
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Row2({ k, raw, parsed }: { k: string; raw?: string | null; parsed?: number | null }) {
  return (
    <tr className="border-b border-rule">
      <td className="py-1.5 pr-2 text-ink-3">{k}</td>
      <td className="py-1.5 pr-2 text-ink-2">{raw ?? "—"}</td>
      <td className="py-1.5 text-right text-ink">{parsed ?? "—"}</td>
    </tr>
  );
}
