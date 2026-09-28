import { TopBar } from "@/components/topbar";
import { Masthead } from "@/components/sections/masthead";
import { Brief } from "@/components/sections/brief";
import { Funnel } from "@/components/sections/funnel";
import { Evidence } from "@/components/sections/evidence";
import { Shortlist } from "@/components/sections/shortlist";
import { Ledger } from "@/components/sections/ledger";
import { Validation } from "@/components/sections/validation";
import { Method } from "@/components/sections/method";
import { Colophon } from "@/components/sections/colophon";

export default function Home() {
  return (
    <>
      <TopBar />
      <main className="flex-1">
        <Masthead />
        <Brief />
        <Funnel />
        <Evidence />
        <Shortlist />
        <Ledger />
        <Validation />
        <Method />
        <div className="border-b border-rule py-8">
          <div className="mx-auto w-full max-w-6xl px-4 md:px-8">
            <a
              href="/arena"
              className="font-mono text-[11px] uppercase tracking-wide text-ink-3 hover:text-seal"
            >
              Round 2 · The Battle Arena, live console →
            </a>
          </div>
        </div>
      </main>
      <Colophon />
    </>
  );
}
