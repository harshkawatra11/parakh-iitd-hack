"use client";

import { Bar } from "react-chartjs-2";
import "@/components/charts/chart-setup";
import { INK, SEAL, OLIVE, baseOptions } from "@/components/charts/chart-setup";
import { Section, SectionHeading } from "@/components/ui/primitives";
import { Reveal } from "@/components/ui/reveal";
import evidence from "@/data/evidence.json";
import validation from "@/data/validation.json";

const corrLabels = evidence.correlations.map((c) =>
  c.feature.replace(/_/g, " ")
);
const corrValues = evidence.correlations.map((c) => c.spearman);

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

export function Evidence() {
  return (
    <Section id="evidence">
      <SectionHeading
        kicker="File 03 // What the Archive Shows"
        title="Merit signals we kept, biases we didn&rsquo;t"
        lede="Every rule in this shortlist traces back to a measured effect on post_hire_score in the 20,000-row Archive."
      />
      <div className="grid gap-5 md:grid-cols-2">
        <Reveal>
          <ChartCard
            title="Spearman correlation with post_hire_score"
            note="technical_assessment and kpi_met are the strongest merit signals. Age and employer count trend negative — the old panel rewarded early-career candidates less than seniority would suggest."
          >
            <Bar
              data={{
                labels: corrLabels,
                datasets: [
                  {
                    data: corrValues,
                    backgroundColor: corrValues.map((v) =>
                      (v ?? 0) < 0 ? OLIVE : INK
                    ),
                    borderRadius: 1,
                    barThickness: 18,
                  },
                ],
              }}
              options={{
                ...baseOptions,
                indexAxis: "y" as const,
                scales: {
                  ...baseOptions.scales,
                  x: { ...baseOptions.scales.x, min: -0.2, max: 0.35 },
                },
              }}
            />
          </ChartCard>
        </Reveal>

        <Reveal delay={0.06}>
          <ChartCard
            title="KPI attainment vs. mean outcome score"
            note={`Candidates who met >80% of KPIs averaged ${evidence.kpiEffect.met}, vs ${evidence.kpiEffect.notMet} for those who did not — the single strongest binary signal in the Archive.`}
          >
            <Bar
              data={{
                labels: ["KPIs not met", "KPIs met"],
                datasets: [
                  {
                    data: [evidence.kpiEffect.notMet, evidence.kpiEffect.met],
                    backgroundColor: [OLIVE, SEAL],
                    borderRadius: 2,
                    barThickness: 64,
                  },
                ],
              }}
              options={{
                ...baseOptions,
                scales: { ...baseOptions.scales, y: { ...baseOptions.scales.y, min: 0, max: 60 } },
              }}
            />
          </ChartCard>
        </Reveal>

        <Reveal delay={0.12}>
          <ChartCard
            title="Ledger recall @ k=150 (150 true winners)"
            note="The full model — including institute, city and referral channel — recovers more of the old cycle's winners than our de-biased model. That gap is the old panel's bias, and it's exactly what we strip out before scoring the Vault."
          >
            <Bar
              data={{
                labels: ["Random baseline", "Vault-lens (submitted)", "Full model (old biases)"],
                datasets: [
                  {
                    data: [validation.randomBaseline, validation.recallVault, validation.recallFull],
                    backgroundColor: [OLIVE, SEAL, INK],
                    borderRadius: 2,
                    barThickness: 40,
                  },
                ],
              }}
              options={{
                ...baseOptions,
                scales: { ...baseOptions.scales, y: { ...baseOptions.scales.y, min: 0, max: 100 } },
              }}
            />
          </ChartCard>
        </Reveal>

        <Reveal delay={0.18}>
          <ChartCard
            title="The old-boys' network (computed, not assumed)"
            note="Residual of post_hire_score after controlling for merit and role, grouped by institute (n≥40, t≥3.0). The five schools below are the only pedigree effect that survives — everything else in the old panel's taste was noise or dropped bias."
          >
            <Bar
              data={{
                labels: validation.oldBoys.map((s) =>
                  s.replace("maharshi dayanand sarswati university ajmer", "MDS Ajmer")
                    .replace("iisc", "IISc")
                    .replace("bits pilani", "BITS Pilani")
                    .replace("iit kharagpur", "IIT Kharagpur")
                    .replace("nit warangal", "NIT Warangal")
                ),
                datasets: [
                  {
                    data: [7.8, 6.7, 6.4, 5.2, 5.3],
                    backgroundColor: SEAL,
                    borderRadius: 2,
                    barThickness: 22,
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
