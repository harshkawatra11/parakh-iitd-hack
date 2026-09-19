"use client";

import { useState } from "react";
import { Section, SectionHeading } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

const ITEMS = [
  {
    q: "Parsers",
    a: `technical_assessment appears as 47, 49/100, 0.45, "43.0 %", "absent". We map the
fraction form (≤1.0) by ×100 and keep a "did not sit" flag rather than imputing zero.
current_ctc appears as "13.9 LPA", "₹13,90,000", 1390000, "13.90L", "INR 13.9 lakh",
"$22,369", "7.53 Cr" — normalised to INR lakh p.a., USD converted at 83/INR.`,
    code: `def p_ctc(v):
    s = v.strip().replace(",", "")
    is_usd = "$" in s
    ...
    if "cr" in low: x *= 100.0
    elif "lpa" in low or "lakh" in low: pass
    else: x /= 1e5
    if is_usd: x *= USD_TO_INR
    return x`,
  },
  {
    q: "Forensics",
    a: `A profile fails if age at graduation < 18, experience exceeds an adult life,
experience contradicts the career-path history by more than a year, or leaves more
than 10 years unaccounted for. On the Archive: 561 flagged, mean outcome 5.49, zero in
the true top 5%. Duplicate people are resolved via union-find over phone, e-mail and
name+graduation-year.`,
    code: `def fabricated_mask(F):
    m = ((F.f_age_at_grad < 18) |
         (F.f_exp > (F.f_age - 20)) |
         (F.f_exp_vs_ysg > 1.5) |
         (F.f_exp_vs_cp > 1.0) |
         (F.f_exp_vs_cp < -8.0) |
         (F.f_gap_years < -4.0) |
         (F.f_gap_years > 10.0))
    return m.fillna(False)`,
  },
  {
    q: "Model",
    a: `LightGBM regressor + top-5% classifier, bagged over 3 seeds, blended by
rank-averaging. Trained on the de-fabricated Archive with every feature the debrief
calls deprecated removed. Validated by scoring dev.csv and checking recall against
dev_winners.csv.`,
    code: `def fit_blend(feats, seeds=(42, 202, 777)):
    regs = [LGBMRegressor(random_state=s, **REG_P).fit(Xtr[feats], ytr) for s in seeds]
    clfs = [LGBMClassifier(random_state=s, **CLF_P).fit(Xtr[feats], ybin) for s in seeds]
    return lambda F: 0.5*rank(mean(reg.predict(F))) + 0.5*rank(mean(clf.predict_proba(F)))`,
  },
  {
    q: "Vault bonuses",
    a: `Public code contributions get a log-ramp bonus (12→48 contributions). New-college
candidates in the top decile of their role's assessment get +0.70z. The five-school
old-boys' network — computed via residual regression, not hardcoded — gets +0.25z.`,
    code: `ramp = (log1p(pcc) - log1p(12)) / (log1p(48) - log1p(12))
b_pcc = clip(ramp, 0, 1) * 1.00`,
  },
];

export function Method() {
  const [open, setOpen] = useState(0);
  return (
    <Section id="method">
      <SectionHeading kicker="File 06 // Method" title="How the pipeline actually works" />
      <div className="border-t border-rule">
        {ITEMS.map((item, i) => (
          <div key={item.q} className="border-b border-rule">
            <button
              onClick={() => setOpen(open === i ? -1 : i)}
              className="flex w-full items-center justify-between py-5 text-left"
            >
              <span className="font-serif text-2xl text-ink">{item.q}</span>
              <span className="font-mono text-ink-3">{open === i ? "−" : "+"}</span>
            </button>
            <div className={cn("overflow-hidden transition-all", open === i ? "max-h-[600px] pb-6" : "max-h-0")}>
              <div className="grid gap-6 md:grid-cols-2">
                <p className="text-[14px] leading-relaxed text-ink-2 whitespace-pre-line">
                  {item.a}
                </p>
                <pre className="overflow-x-auto border border-rule bg-paper-2 p-4 font-mono text-[11px] leading-relaxed text-ink-2">
                  {item.code}
                </pre>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}
